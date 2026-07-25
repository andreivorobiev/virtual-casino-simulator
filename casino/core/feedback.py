"""Privacy-safe, provider-neutral problem reports and manual Admin triage for issue #349."""

# Decode browser image payloads only inside the reviewed normalization boundary.
import base64
# Hash normalized images and key durable identity proofs.
import hashlib
# Compare and create HMAC-only reporter and action identities.
import hmac
# Hold decoded image bytes without writing caller input to disk.
from io import BytesIO
# Serialize semantic action payloads deterministically.
import json
# Validate bounded action identifiers and safe relative routes.
import re
# Parse canonical UTC timestamps for rate and retention windows.
from datetime import datetime, timezone

# Decode and re-encode allowlisted image formats without caller metadata.
from PIL import Image, UnidentifiedImageError

# Reuse the public-startup-hardened digest key and bounded feedback policy.
from casino import config
# Bind safe diagnostic context to the canonical packaged application release.
from casino.config import APP_VERSION
# Return stable envelopes for conflicts, missing reports, rates, and invalid input.
from casino.errors import ConflictError, NotFoundError, RateLimitError, ValidationError
# Produce canonical UTC lifecycle timestamps.
from casino.core.clock import utc_now
# Allocate opaque server-owned report and attachment identifiers.
from casino.core.ids import new_id
# Use the configured JSON or MySQL document provider.
from casino.core.storage import get_storage_provider

# Store all report metadata, replay proofs, rates, and lifecycle state under one provider transaction key.
STATE_DOCUMENT = "feedback_reports_v2"
# Accept only the current durable schema so malformed state is preserved rather than normalized away.
STATE_SCHEMA_VERSION = 2
# Enumerate the product-owned category taxonomy.
ALLOWED_CATEGORIES = frozenset({"bug", "visual", "gameplay", "account", "idea", "other"})
# Keep player impact separate from repository P1/P2/P3 priority.
ALLOWED_IMPACTS = frozenset({"blocked", "difficult", "minor"})
# Restrict Admin priority to the repository taxonomy.
ALLOWED_PRIORITIES = frozenset({"P1", "P2", "P3"})
# Restrict report lifecycle to reviewed manual-triage states.
ALLOWED_STATUSES = frozenset({"new", "triaged", "linked", "resolved", "duplicate", "rejected"})
# Identify terminal states eligible for bounded privacy cleanup.
TERMINAL_STATUSES = frozenset({"resolved", "duplicate", "rejected"})
# Bound stored locale metadata to acceptance locales.
ALLOWED_LOCALES = frozenset({"en-US", "ru-RU"})
# Bound stored browser metadata to low-cardinality families.
ALLOWED_BROWSER_FAMILIES = frozenset({"Chrome", "Edge", "Firefox", "Safari", "Other"})
# Bound stored operating-system metadata to low-cardinality families.
ALLOWED_OS_FAMILIES = frozenset({"Android", "iOS", "Linux", "macOS", "Windows", "Other"})
# Reject oversized encoded source images before decoder work.
MAX_SOURCE_IMAGE_BYTES = 210_000
# Bound normalized evidence retained by one report.
MAX_TOTAL_IMAGE_BYTES = 650_000
# Limit one report to a reviewable number of screenshots.
MAX_ATTACHMENTS = 3
# Reject image decompression bombs before full pixel allocation.
MAX_IMAGE_PIXELS = 12_000_000
# Bound normalized image dimensions.
MAX_IMAGE_DIMENSION = 1_920
# Require explicit cleanup instead of silently evicting report content.
MAX_REPORTS = 2_000
# Bound per-report audit and Admin replay history.
MAX_HISTORY = 100
# Accept only browser-generated replay keys with no document-key punctuation.
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,100}$")
# Accept only relative route paths without query strings or fragments.
ROUTE_PATTERN = re.compile(r"^/[A-Za-z0-9_./-]{0,180}$")
# Accept manual links only to the owned Casino issue tracker.
GITHUB_ISSUE_PATTERN = re.compile(r"^https://github\.com/andreivorobiev/virtual-casino-simulator/issues/[1-9][0-9]*$")


# Build independent default containers for an absent provider document.
def _empty_state() -> dict:
    # Return the complete current schema without sharing mutable defaults.
    return {"schema_version": STATE_SCHEMA_VERSION, "reports": [], "idempotency": {}, "rate_events": [], "tombstones": []}


# Validate complete durable state without substituting defaults for malformed content.
def _state(raw: object) -> dict:
    # Require an object with the exact current schema and every canonical container.
    if not isinstance(raw, dict) or raw.get("schema_version") != STATE_SCHEMA_VERSION or not isinstance(raw.get("reports"), list) or not isinstance(raw.get("idempotency"), dict) or not isinstance(raw.get("rate_events"), list) or not isinstance(raw.get("tombstones"), list):
        # Abort the provider transaction so recoverable data remains unchanged.
        raise ConflictError("Problem report storage requires recovery")
    # Return the transaction-owned validated document.
    return raw


# Parse one canonical UTC timestamp for bounded policy comparisons.
def _parse_time(value: object) -> datetime:
    # Normalize the accepted trailing-Z form for the standard parser.
    parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    # Attach UTC only for a legacy value missing an explicit offset.
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


# Compute one domain-separated HMAC without storing raw source values.
def _digest(domain: str, *values: object) -> str:
    # Join bounded fields with a separator that cannot be confused with ordinary identifiers.
    message = "\x1f".join((domain, *(str(value) for value in values)))
    # Key the proof with the existing public-startup-hardened server digest material.
    return hmac.new(config.MAIL_DIGEST_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


# Build an opaque stable reporter reference from an authenticated canonical user id.
def _reporter_reference(user_id: str) -> str:
    # Expose only a short HMAC reference to Admin filters and audit history.
    return "USR-" + _digest("feedback-reporter", user_id)[:16].upper()


# Bind one semantic payload to a keyed fingerprint.
def _fingerprint(payload: dict) -> str:
    # Serialize equivalent objects into one canonical representation.
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # Key the fingerprint so private prose cannot be dictionary-tested from storage alone.
    return _digest("feedback-payload", canonical)


# Build one private attachment-document key from server-owned identifiers.
def _attachment_key(report_id: str, attachment_id: str) -> str:
    # Bind evidence to its report so a cross-report identifier cannot substitute it.
    return f"feedback_attachment_{report_id}_{attachment_id}"


# Resolve one report from authoritative state by opaque server id.
def _find_report(state: dict, report_id: str) -> dict | None:
    # Return the exact match without exposing adjacent records.
    return next((row for row in state["reports"] if row.get("report_id") == report_id), None)


# Append one bounded privacy-safe lifecycle event.
def _event(report: dict, action: str, actor: str, prior: object = None, current: object = None) -> None:
    # Copy existing events before appending fixed, non-prose values.
    history = list(report.get("history") or [])
    # Record only time, action, opaque actor, and bounded state transition.
    history.append({"at": utc_now(), "action": action, "actor_reference": actor, "prior": prior, "current": current})
    # Retain only the newest bounded events.
    report["history"] = history[-MAX_HISTORY:]


# Normalize and validate one bounded player-authored text field.
def _text(value: object, field: str, minimum: int, maximum: int) -> str:
    # Trim surrounding whitespace while retaining intentional internal line breaks.
    normalized = str(value or "").strip()
    # Reject absent or oversized content without echoing it.
    if len(normalized) < minimum or len(normalized) > maximum:
        # Return a field-scoped validation result.
        raise ValidationError(f"{field} must be between {minimum} and {maximum} characters", {"field": field})
    # Return only the validated text.
    return normalized


# Decode, validate, resize, and re-encode one screenshot without retaining metadata.
def _normalize_attachment(item: object, position: int) -> dict:
    # Require named input so scalars cannot bypass validation.
    if not isinstance(item, dict):
        # Identify only the invalid attachment position.
        raise ValidationError("Each screenshot must be an image object", {"attachment": position})
    # Read a data URL or bare base64 payload without retaining a caller filename.
    encoded = str(item.get("data") or "")
    # Remove one allowlisted data-URL prefix before strict decoding.
    if encoded.startswith("data:"):
        # Split only the first comma so encoded bytes remain intact.
        parts = encoded.split(",", 1)
        # Require an image base64 data URL.
        if len(parts) != 2 or ";base64" not in parts[0] or not parts[0].startswith("data:image/"):
            # Return a stable validation result.
            raise ValidationError("Screenshot data URL is invalid", {"attachment": position})
        # Retain only the encoded bytes.
        encoded = parts[1]
    # Decode strict base64 so ignored punctuation cannot conceal a larger payload.
    try:
        # Convert transport text into source bytes.
        raw = base64.b64decode(encoded, validate=True)
    # Collapse encoding failures into one safe error.
    except (ValueError, base64.binascii.Error) as exc:
        # Preserve the decoder error only as chained internal context.
        raise ValidationError("Screenshot encoding is invalid", {"attachment": position}) from exc
    # Reject empty or oversized sources before image parsing.
    if not raw or len(raw) > MAX_SOURCE_IMAGE_BYTES:
        # Publish only the reviewed bound.
        raise ValidationError("Screenshot exceeds the 210 KB upload limit", {"attachment": position})
    # Decode and sanitize the source image inside one protected boundary.
    try:
        # Open the source without trusting MIME or extension claims.
        with Image.open(BytesIO(raw)) as source:
            # Reject declared surfaces above the reviewed pixel ceiling.
            if source.width * source.height > MAX_IMAGE_PIXELS:
                # Avoid echoing untrusted dimensions.
                raise ValidationError("Screenshot dimensions exceed the safe upload limit", {"attachment": position})
            # Force complete decoding before format acceptance.
            source.load()
            # Accept only static PNG, JPEG, or WebP decoders.
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                # Reject every other format through one stable result.
                raise ValidationError("Screenshot must be PNG, JPEG, or WebP", {"attachment": position})
            # Convert into fresh RGB pixels so EXIF, ICC, text chunks, and animation metadata disappear.
            normalized = source.convert("RGB")
            # Reduce oversized dimensions while preserving aspect ratio.
            normalized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            # Allocate a clean output buffer.
            output = BytesIO()
            # Encode one deterministic metadata-free JPEG derivative.
            normalized.save(output, format="JPEG", quality=76, optimize=True, progressive=True)
            # Capture the sanitized bytes.
            sanitized = output.getvalue()
            # Compute a content-integrity digest for recovery checks.
            sha256 = hashlib.sha256(sanitized).hexdigest()
            # Return server-authored metadata and transport-safe pixels.
            return {"attachment_id": new_id("evidence"), "name": f"screenshot-{position}.jpg", "media_type": "image/jpeg", "width": normalized.width, "height": normalized.height, "bytes": len(sanitized), "sha256": sha256, "data": base64.b64encode(sanitized).decode("ascii")}
    # Convert parser and decompression failures into one stable public result.
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        # Avoid exposing decoder internals.
        raise ValidationError("Screenshot could not be safely decoded", {"attachment": position}) from exc


# Validate the browser's privacy-reduced diagnostic context.
def _context(value: object) -> dict:
    # Treat omitted context as an empty object.
    supplied = value if isinstance(value, dict) else {}
    # Remove query and fragment text before validating a relative route.
    route = str(supplied.get("route") or "/").split("?", 1)[0].split("#", 1)[0]
    # Replace an unsafe route with root.
    route = route if ROUTE_PATTERN.fullmatch(route) else "/"
    # Accept only a governed locale.
    locale = str(supplied.get("locale") or "en-US")
    # Fall back to English for unsupported locale metadata.
    locale = locale if locale in ALLOWED_LOCALES else "en-US"
    # Parse and clamp viewport dimensions.
    try:
        # Bound width to a reviewed browser range.
        width = max(240, min(int(supplied.get("viewport_width") or 0), 8_000))
        # Bound height to a reviewed browser range.
        height = max(240, min(int(supplied.get("viewport_height") or 0), 8_000))
    # Replace malformed dimensions with a neutral pair.
    except (TypeError, ValueError):
        # Store no caller-authored malformed value.
        width, height = 0, 0
    # Accept only a low-cardinality browser family.
    browser = str(supplied.get("browser_family") or "Other")
    # Replace arbitrary browser text with the fallback.
    browser = browser if browser in ALLOWED_BROWSER_FAMILIES else "Other"
    # Accept only a low-cardinality OS family.
    operating_system = str(supplied.get("os_family") or "Other")
    # Replace arbitrary OS text with the fallback.
    operating_system = operating_system if operating_system in ALLOWED_OS_FAMILIES else "Other"
    # Return only reviewed context fields.
    return {"route": route, "locale": locale, "viewport_width": width, "viewport_height": height, "browser_family": browser, "os_family": operating_system, "reduced_motion": bool(supplied.get("reduced_motion")), "app_version": APP_VERSION}


# Return attachment metadata without encoded pixels.
def _descriptor(attachment: dict) -> dict:
    # Keep only server-authored identity, format, geometry, size, and integrity.
    return {key: attachment[key] for key in ("attachment_id", "name", "media_type", "width", "height", "bytes", "sha256")}


# Return the list-safe subset of one committed report.
def _summary(report: dict) -> dict:
    # Exclude private prose, pixels, notes, audit history, fingerprints, and raw identity.
    return {key: report[key] for key in ("report_id", "reference", "category", "impact", "priority", "status", "summary", "route", "locale", "reporter_reference", "attachment_count", "created_at", "updated_at", "github_issue_url")}


# Validate a complete submission before durable mutation.
def _validated_submission(user: dict, body: object) -> tuple[str, str, dict, list[dict]]:
    # Require object input.
    if not isinstance(body, dict):
        # Return the stable body-shape error.
        raise ValidationError("Problem report body must be an object")
    # Reject guest or absent canonical identities.
    user_id = str(user.get("user_id") or "").strip()
    # Enforce authenticated persistent-user scope.
    if not user_id or str(user.get("identity_provider") or "").lower() == "guest":
        # Publish no identity detail.
        raise ValidationError("Problem reports currently require a registered account")
    # Validate the caller replay key.
    action_key = str(body.get("idempotency_key") or "")
    # Reject missing or malformed keys.
    if not IDEMPOTENCY_PATTERN.fullmatch(action_key):
        # Identify only the invalid field.
        raise ValidationError("A valid idempotency key is required", {"field": "idempotency_key"})
    # Validate product category.
    category = str(body.get("category") or "bug").lower()
    # Reject uncontrolled categories.
    if category not in ALLOWED_CATEGORIES:
        # Identify only the invalid field.
        raise ValidationError("Report category is invalid", {"field": "category"})
    # Validate player impact independently from repository priority.
    impact = str(body.get("impact") or "minor").lower()
    # Reject uncontrolled impact values.
    if impact not in ALLOWED_IMPACTS:
        # Identify only the invalid field.
        raise ValidationError("Report impact is invalid", {"field": "impact"})
    # Require a bounded attachment list.
    supplied_attachments = body.get("attachments") or []
    # Reject non-list or excessive evidence.
    if not isinstance(supplied_attachments, list) or len(supplied_attachments) > MAX_ATTACHMENTS:
        # Publish only the reviewed count limit.
        raise ValidationError("A report can include up to three screenshots", {"field": "attachments"})
    # Normalize attachments serially before storage reservation.
    attachments = [_normalize_attachment(item, index + 1) for index, item in enumerate(supplied_attachments)]
    # Reject excessive normalized aggregate size.
    if sum(item["bytes"] for item in attachments) > MAX_TOTAL_IMAGE_BYTES:
        # Publish only the aggregate limit result.
        raise ValidationError("Combined screenshots exceed the report upload limit", {"field": "attachments"})
    # Build validated content and safe context only.
    content = {"category": category, "impact": impact, "summary": _text(body.get("summary"), "summary", 5, 140), "actual": _text(body.get("actual"), "actual", 5, 4_000), "expected": _text(body.get("expected"), "expected", 5, 2_000), "context": _context(body.get("context"))}
    # Return only the opaque reporter reference, transient replay key, safe content, and sanitized evidence.
    return _reporter_reference(user_id), action_key, content, attachments


# Persist winner-owned evidence idempotently during submission recovery.
def _write_attachments(provider, report: dict, attachments: list[dict]) -> None:
    # Read the winner's fixed descriptor inventory.
    descriptors = list(report.get("attachments") or [])
    # Reject changed evidence counts under a reused action identity.
    if len(descriptors) != len(attachments):
        # Keep the report in recoverable preparing state.
        raise ConflictError("Problem report retry payload changed")
    # Match sanitized evidence by stable position and digest.
    for descriptor, attachment in zip(descriptors, attachments):
        # Reject changed pixels under the same replay key.
        if descriptor.get("sha256") != attachment.get("sha256"):
            # Preserve the first winner.
            raise ConflictError("Problem report retry payload changed")
        # Resolve the winner-owned evidence key.
        key = _attachment_key(report["report_id"], descriptor["attachment_id"])
        # Read any prior partial-saga write.
        existing = provider.read_document(key, None)
        # Accept only the exact prior write as idempotent recovery.
        if isinstance(existing, dict) and existing.get("state") == "active" and existing.get("report_id") == report["report_id"] and existing.get("sha256") == descriptor["sha256"]:
            # Continue without rewriting durable evidence.
            continue
        # Preserve malformed or conflicting data unchanged.
        if existing is not None:
            # Stop in the recoverable preparing phase.
            raise ConflictError("Problem report attachment storage requires recovery")
        # Persist only normalized pixels and server-authored metadata.
        provider.write_document(key, {"schema_version": STATE_SCHEMA_VERSION, "state": "active", "report_id": report["report_id"], **descriptor, "data": attachment["data"]})


# Create one recoverable, rate-limited, idempotent authenticated report.
def submit(user: dict, body: dict) -> dict:
    # Validate all input and evidence before durable mutation.
    reporter, action_key, content, attachments = _validated_submission(user, body)
    # Convert the raw browser key into a domain-separated durable proof.
    action_digest = _digest("feedback-submit", reporter, action_key)
    # Bind the action to validated prose, context, and normalized evidence digests.
    semantics = {**content, "attachments": [{"position": index + 1, "sha256": item["sha256"], "bytes": item["bytes"]} for index, item in enumerate(attachments)]}
    # Compute the HMAC-only semantic fingerprint.
    payload_fingerprint = _fingerprint(semantics)
    # Allocate candidate identities before provider locking.
    candidate_id = new_id("report")
    # Build a short player-facing reference.
    reference = f"RPT-{candidate_id.rsplit('_', 1)[-1][:8].upper()}"
    # Capture one timestamp for reservation fields.
    created_at = utc_now()
    # Share the transaction-selected winner with later phases.
    selected: dict = {}
    # Read the provider once for the full operation.
    provider = get_storage_provider()
    # Reserve the winner, replay proof, and durable rate slot atomically.
    def reserve(raw: object) -> dict:
        # Validate the complete state before mutation.
        state = _state(raw)
        # Resolve a prior winner through the HMAC-only action proof.
        prior_id = state["idempotency"].get(action_digest)
        # Handle an exact retry.
        if prior_id:
            # Resolve the prior report inside the same locked document.
            prior = _find_report(state, prior_id)
            # Preserve broken replay state for recovery.
            if prior is None:
                # Abort unchanged.
                raise ConflictError("Problem report storage requires recovery")
            # Reject changed meaning under the same action key.
            if not hmac.compare_digest(str(prior.get("payload_fingerprint", "")), payload_fingerprint):
                # Preserve the first accepted meaning.
                raise ConflictError("Problem report idempotency key was reused with different input")
            # Publish a detached prior winner.
            selected.update(dict(prior))
            # Leave state unchanged.
            return state
        # Parse one current instant for rate pruning.
        now = _parse_time(created_at)
        # Retain only valid events within the configured window.
        retained = [event for event in state["rate_events"] if isinstance(event, dict) and event.get("reporter_reference") and event.get("at") and (now - _parse_time(event["at"])).total_seconds() <= config.FEEDBACK_RATE_WINDOW_SECONDS]
        # Count this reporter's accepted reservations across every process.
        if sum(1 for event in retained if event.get("reporter_reference") == reporter) >= config.FEEDBACK_RATE_LIMIT:
            # Reject without allocating a report or attachment document.
            raise RateLimitError("Problem report rate limit is active")
        # Require explicit retention cleanup before bounded capacity is exhausted.
        if len(state["reports"]) >= MAX_REPORTS:
            # Avoid silent privacy or replay-data eviction.
            raise ConflictError("Problem report retention cleanup is required")
        # Describe evidence without storing pixels in the authoritative state row.
        descriptors = [_descriptor(item) for item in attachments]
        # Build a complete nonpublic preparing report.
        report = {"report_id": candidate_id, "reference": reference, "storage_phase": "preparing", "payload_fingerprint": payload_fingerprint, "category": content["category"], "impact": content["impact"], "priority": "P2", "status": "new", "summary": content["summary"], "actual": content["actual"], "expected": content["expected"], "route": content["context"]["route"], "locale": content["context"]["locale"], "context": content["context"], "reporter_reference": reporter, "attachments": descriptors, "attachment_count": len(descriptors), "admin_notes": "", "labels": ["P2", "bug" if content["category"] in {"bug", "visual", "gameplay", "account"} else "enhancement"], "github_issue_url": "", "created_at": created_at, "updated_at": created_at, "terminal_at": None, "history": [], "admin_actions": {}}
        # Append the hidden reservation before separate evidence writes.
        state["reports"].append(report)
        # Store the HMAC-only winner mapping.
        state["idempotency"][action_digest] = candidate_id
        # Store the durable rate event in the same transaction.
        state["rate_events"] = retained + [{"reporter_reference": reporter, "at": created_at}]
        # Publish a detached winner.
        selected.update(dict(report))
        # Commit the complete state.
        return state
    # Serialize reservations across threads and processes for JSON and MySQL.
    provider.update_document(STATE_DOCUMENT, reserve, _empty_state)
    # Return an exact already-committed replay without touching evidence.
    if selected.get("storage_phase") == "committed":
        # Return only the public receipt.
        return {"report_id": selected["report_id"], "reference": selected["reference"], "status": selected["status"], "replayed": True}
    # Write or recover the winner-owned evidence set.
    _write_attachments(provider, selected, attachments)
    # Share the committed winner with the response.
    committed: dict = {}
    # Publish the report only after every evidence document is durable.
    def finalize(raw: object) -> dict:
        # Validate state inside the provider lock.
        state = _state(raw)
        # Resolve the selected winner.
        report = _find_report(state, selected["report_id"])
        # Require the same semantic reservation.
        if report is None or not hmac.compare_digest(str(report.get("payload_fingerprint", "")), payload_fingerprint):
            # Preserve unexpected state for recovery.
            raise ConflictError("Problem report storage requires recovery")
        # Commit only the preparing phase.
        if report.get("storage_phase") == "preparing":
            # Make the report list/detail visible.
            report["storage_phase"] = "committed"
            # Stamp finalization.
            report["updated_at"] = utc_now()
            # Record the fixed lifecycle event.
            _event(report, "report_committed", reporter, "preparing", "committed")
        # Accept a concurrent exact finalization only.
        elif report.get("storage_phase") != "committed":
            # Preserve deletion or unknown phases.
            raise ConflictError("Problem report storage requires recovery")
        # Publish a detached committed report.
        committed.update(dict(report))
        # Commit the complete state.
        return state
    # Atomically publish visibility.
    provider.update_document(STATE_DOCUMENT, finalize, _empty_state)
    # Return only stable receipt fields.
    return {"report_id": committed["report_id"], "reference": committed["reference"], "status": committed["status"], "replayed": committed["report_id"] != candidate_id}


# Read and validate the authoritative state without mutation.
def _read_state() -> dict:
    # Reject malformed state instead of showing a false empty inbox.
    return _state(get_storage_provider().read_document(STATE_DOCUMENT, _empty_state))


# List compact committed reports with bounded exact filters.
def list_reports(filters: dict | None = None) -> list[dict]:
    # Read only fully committed reports.
    reports = [row for row in _read_state()["reports"] if row.get("storage_phase") == "committed"]
    # Treat absent query input as empty filters.
    supplied = filters if isinstance(filters, dict) else {}
    # Normalize each supported exact filter.
    priority = str(supplied.get("priority") or "").upper()
    # Normalize lifecycle state.
    status = str(supplied.get("status") or "").lower()
    # Normalize product category.
    category = str(supplied.get("category") or "").lower()
    # Normalize reporter-selected impact.
    impact = str(supplied.get("impact") or "").lower()
    # Normalize locale.
    locale = str(supplied.get("locale") or "")
    # Normalize safe route.
    route = str(supplied.get("route") or "")
    # Normalize opaque reporter reference.
    reporter = str(supplied.get("reporter") or "").upper()
    # Reject unsupported priorities.
    if priority and priority not in ALLOWED_PRIORITIES:
        # Identify only the filter family.
        raise ValidationError("Feedback priority filter is invalid")
    # Reject unsupported lifecycle values.
    if status and status not in ALLOWED_STATUSES:
        # Identify only the filter family.
        raise ValidationError("Feedback status filter is invalid")
    # Reject unsupported categories.
    if category and category not in ALLOWED_CATEGORIES:
        # Identify only the filter family.
        raise ValidationError("Feedback category filter is invalid")
    # Reject unsupported impacts.
    if impact and impact not in ALLOWED_IMPACTS:
        # Identify only the filter family.
        raise ValidationError("Feedback impact filter is invalid")
    # Reject unsupported locales.
    if locale and locale not in ALLOWED_LOCALES:
        # Identify only the filter family.
        raise ValidationError("Feedback locale filter is invalid")
    # Reject unsafe route values.
    if route and not ROUTE_PATTERN.fullmatch(route):
        # Identify only the filter family.
        raise ValidationError("Feedback route filter is invalid")
    # Reject raw or malformed reporter filters.
    if reporter and not re.fullmatch(r"USR-[A-F0-9]{16}", reporter):
        # Identify only the filter family.
        raise ValidationError("Feedback reporter filter is invalid")
    # Parse optional date bounds.
    try:
        # Parse the inclusive lower bound when present.
        created_from = _parse_time(supplied["created_from"]) if supplied.get("created_from") else None
        # Parse the inclusive upper bound when present.
        created_to = _parse_time(supplied["created_to"]) if supplied.get("created_to") else None
    # Collapse parser failures into one safe result.
    except (TypeError, ValueError):
        # Avoid echoing caller date text.
        raise ValidationError("Feedback date filter is invalid")
    # Return newest-first safe summaries after every predicate passes.
    return [_summary(row) for row in reversed(reports) if (not priority or row.get("priority") == priority) and (not status or row.get("status") == status) and (not category or row.get("category") == category) and (not impact or row.get("impact") == impact) and (not locale or row.get("locale") == locale) and (not route or row.get("route") == route) and (not reporter or row.get("reporter_reference") == reporter) and (not created_from or _parse_time(row.get("created_at")) >= created_from) and (not created_to or _parse_time(row.get("created_at")) <= created_to)]


# List the authenticated persistent user's own report statuses without exposing retained evidence.
def list_reporter_reports(user: dict) -> list[dict]:
    # Reject missing, guest, or anonymous identities before deriving a reporter reference.
    if not isinstance(user, dict) or not user.get("user_id") or str(user.get("identity_provider") or "").lower() == "guest":
        # Publish the same registered-only policy used by submission.
        raise ValidationError("Problem reports currently require a registered account")
    # Derive the opaque reporter reference exactly as submission does.
    reporter = _reporter_reference(str(user.get("user_id") or ""))
    # Return newest-first summaries scoped to that reporter only.
    return list_reports({"reporter": reporter})


# Read one committed report and its Admin-only normalized evidence.
def detail(report_id: str) -> dict:
    # Resolve authoritative metadata first.
    report = _find_report(_read_state(), report_id)
    # Hide absent and noncommitted phases behind one not-found result.
    if report is None or report.get("storage_phase") != "committed":
        # Return the stable not-found envelope.
        raise NotFoundError("Problem report was not found")
    # Read the provider once for all evidence documents.
    provider = get_storage_provider()
    # Collect validated Admin-only evidence.
    attachments = []
    # Verify every expected attachment document.
    for descriptor in list(report.get("attachments") or []):
        # Load evidence without a substitute default.
        stored = provider.read_document(_attachment_key(report_id, descriptor["attachment_id"]), None)
        # Fail closed for missing, deleted, malformed, or substituted evidence.
        if not isinstance(stored, dict) or stored.get("state") != "active" or stored.get("report_id") != report_id or stored.get("sha256") != descriptor.get("sha256") or not isinstance(stored.get("data"), str):
            # Preserve report and evidence for recovery.
            raise ConflictError("Problem report attachment storage requires recovery")
        # Add normalized pixels to the Admin-only projection.
        attachments.append({**descriptor, "data": stored["data"]})
    # Copy report metadata so callers cannot mutate provider state.
    projection = dict(report)
    # Attach only validated evidence.
    projection["attachments"] = attachments
    # Remove internal semantic and replay proofs from API output.
    projection.pop("payload_fingerprint", None)
    # Remove HMAC-only Admin action map from API output.
    projection.pop("admin_actions", None)
    # Return the Admin-authorized projection.
    return projection


# Apply idempotent triage and manual-link changes in one provider transaction.
def update(report_id: str, body: dict) -> dict:
    # Require structured input.
    if not isinstance(body, dict):
        # Return the stable body-shape error.
        raise ValidationError("Problem report update must be an object")
    # Require a strong Admin action key.
    action_key = str(body.get("idempotency_key") or "")
    # Reject missing or malformed action keys.
    if not IDEMPOTENCY_PATTERN.fullmatch(action_key):
        # Identify only the invalid field.
        raise ValidationError("A valid idempotency key is required", {"field": "idempotency_key"})
    # Collect only validated mutable fields.
    requested: dict = {}
    # Validate optional lifecycle state.
    if "status" in body:
        # Normalize state.
        status = str(body.get("status") or "").lower()
        # Reject unsupported state.
        if status not in ALLOWED_STATUSES:
            # Identify only the invalid field.
            raise ValidationError("Problem report status is invalid", {"field": "status"})
        # Retain the validated state.
        requested["status"] = status
    # Validate optional repository priority.
    if "priority" in body:
        # Normalize priority.
        priority = str(body.get("priority") or "").upper()
        # Reject P4 and arbitrary values.
        if priority not in ALLOWED_PRIORITIES:
            # Identify only the invalid field.
            raise ValidationError("Problem report priority must be P1, P2, or P3", {"field": "priority"})
        # Retain the validated priority.
        requested["priority"] = priority
    # Validate optional internal notes.
    if "admin_notes" in body:
        # Normalize bounded notes.
        notes = str(body.get("admin_notes") or "").strip()
        # Reject oversized notes.
        if len(notes) > 4_000:
            # Identify only the invalid field.
            raise ValidationError("Admin notes must not exceed 4000 characters", {"field": "admin_notes"})
        # Retain validated notes.
        requested["admin_notes"] = notes
    # Validate optional manually recorded issue link.
    if "github_issue_url" in body:
        # Normalize the reviewed URL.
        issue_url = str(body.get("github_issue_url") or "").strip()
        # Reject foreign or non-issue links.
        if issue_url and not GITHUB_ISSUE_PATTERN.fullmatch(issue_url):
            # Identify only the invalid field.
            raise ValidationError("GitHub issue URL must belong to the Casino repository", {"field": "github_issue_url"})
        # Retain the validated manual link.
        requested["github_issue_url"] = issue_url
    # Reject empty mutations.
    if not requested:
        # Avoid consuming a replay key for no state change.
        raise ValidationError("Problem report update has no supported fields")
    # Compute HMAC-only action and semantic proofs.
    action_digest = _digest("feedback-admin-update", report_id, action_key)
    # Bind the action key to one update meaning.
    action_fingerprint = _fingerprint(requested)
    # Share the selected row with the response.
    selected: dict = {}
    # Mutate metadata, audit, manual link, and replay proof atomically.
    def mutate(raw: object) -> dict:
        # Validate authoritative state.
        state = _state(raw)
        # Resolve the committed report.
        report = _find_report(state, report_id)
        # Reject missing or noncommitted reports.
        if report is None or report.get("storage_phase") != "committed":
            # Hide storage phase details.
            raise NotFoundError("Problem report was not found")
        # Copy HMAC-only Admin replay proofs.
        actions = dict(report.get("admin_actions") or {})
        # Resolve a prior action.
        prior = actions.get(action_digest)
        # Reject changed semantics under one key.
        if prior and not hmac.compare_digest(str(prior), action_fingerprint):
            # Preserve the first accepted update.
            raise ConflictError("Problem report update idempotency key was reused with different input")
        # Return exact replays without duplicate audit.
        if prior:
            # Publish a detached current row.
            selected.update(dict(report))
            # Leave state unchanged.
            return state
        # Capture the prior lifecycle.
        prior_status = report.get("status")
        # Apply only validated fields.
        report.update(requested)
        # Move a manually linked active report into linked state.
        if requested.get("github_issue_url") and report.get("status") in {"new", "triaged"}:
            # Record explicit manual linkage only.
            report["status"] = "linked"
        # Stamp terminal entry for retention.
        report["terminal_at"] = utc_now() if report.get("status") in TERMINAL_STATUSES and prior_status not in TERMINAL_STATUSES else report.get("terminal_at")
        # Clear terminal timing when explicitly reopened.
        if report.get("status") not in TERMINAL_STATUSES:
            # Keep active reports out of terminal cleanup.
            report["terminal_at"] = None
        # Rebuild governed labels without caller labels.
        report["labels"] = [report["priority"], "bug" if report["category"] in {"bug", "visual", "gameplay", "account"} else "enhancement"]
        # Refresh lifecycle time.
        report["updated_at"] = utc_now()
        # Record one privacy-safe audit event.
        _event(report, "admin_triage", "ADMIN", prior_status, report.get("status"))
        # Publish the replay proof only with the completed mutation.
        actions[action_digest] = action_fingerprint
        # Bound retained Admin action proofs.
        report["admin_actions"] = dict(list(actions.items())[-MAX_HISTORY:])
        # Publish a detached updated row.
        selected.update(dict(report))
        # Commit the complete state.
        return state
    # Serialize the update across JSON and MySQL processes.
    get_storage_provider().update_document(STATE_DOCUMENT, mutate, _empty_state)
    # Return a fresh evidence-validated Admin projection.
    return detail(selected["report_id"])


# Build a sanitized manual GitHub issue draft without external mutation capability.
def github_draft(report_id: str) -> dict:
    # Load the Admin-authorized report.
    report = detail(report_id)
    # Read safe diagnostic context.
    context = report.get("context") or {}
    # Build a reporter-free issue title.
    title = f"[{report['category'].title()}] {report['summary']}"
    # Build bounded Markdown without notes, identity, or encoded evidence.
    body = "\n".join((f"Internal report: `{report['reference']}`", "", "## What happened", report["actual"], "", "## Expected", report["expected"], "", "## Reproduction context", f"- Route: `{report['route']}`", f"- App version: `{context.get('app_version', APP_VERSION)}`", f"- Locale: `{report['locale']}`", f"- Viewport: `{context.get('viewport_width', 0)} × {context.get('viewport_height', 0)}`", f"- Browser family: `{context.get('browser_family', 'unknown')}`", f"- OS family: `{context.get('os_family', 'unknown')}`", f"- Reduced motion: `{bool(context.get('reduced_motion'))}`", f"- Reporter-selected impact: `{report['impact']}`", f"- Screenshots retained internally: {report['attachment_count']}", "", "Screenshots and reporter identity remain in the Admin inbox. Publication is a separate manual Admin action outside this application."))
    # Return only reviewable text, governed labels, and the disabled external-publication switch.
    return {"title": title[:256], "body": body, "labels": list(report.get("labels") or [report["priority"], "bug"]), "source_report_id": report_id, "publication_mode": "manual_only", "publication_enabled": config.FEEDBACK_GITHUB_PUBLICATION_ENABLED}


# Export one privacy-safe Admin metadata manifest without encoded pixels.
def export_report(report_id: str) -> dict:
    # Load and validate the complete report first.
    report = detail(report_id)
    # Replace evidence payloads with integrity metadata only.
    report["attachments"] = [_descriptor(item) for item in report.get("attachments") or []]
    # State the fixed export policy explicitly.
    report["export_policy"] = "metadata_only_manual_admin_export"
    # Return the bounded Admin export.
    return report


# Complete one explicit or retention-driven deletion saga.
def _delete_internal(report_id: str, action_digest: str, reason: str) -> dict:
    # Share the reserved report with the attachment scrub phase.
    selected: dict = {}
    # Read the provider once for every phase.
    provider = get_storage_provider()
    # Mark report content nonpublic before scrubbing separate evidence.
    def reserve(raw: object) -> dict:
        # Validate authoritative state.
        state = _state(raw)
        # Return an exact completed replay from the tombstone registry.
        tombstone = next((row for row in state["tombstones"] if row.get("report_id") == report_id), None)
        # Handle a completed deletion.
        if tombstone:
            # Reject a different deletion identity.
            if tombstone.get("delete_action_digest") != action_digest:
                # Preserve the completed tombstone.
                raise ConflictError("Problem report deletion already completed")
            # Publish the tombstone.
            selected.update(dict(tombstone))
            # Leave state unchanged.
            return state
        # Resolve a retained report.
        report = _find_report(state, report_id)
        # Reject absent reports.
        if report is None:
            # Hide tombstone inventory.
            raise NotFoundError("Problem report was not found")
        # Require committed content or the exact recovery action.
        if report.get("storage_phase") == "deleting" and report.get("delete_action_digest") != action_digest:
            # Preserve the first deletion owner.
            raise ConflictError("Problem report deletion is already in progress")
        # Reject preparing and unknown phases.
        if report.get("storage_phase") not in {"committed", "deleting"}:
            # Preserve recovery data unchanged.
            raise ConflictError("Problem report storage requires recovery")
        # Hide the report from all reads before evidence mutation.
        report["storage_phase"] = "deleting"
        # Bind retries to the HMAC-only action identity.
        report["delete_action_digest"] = action_digest
        # Store only the fixed deletion reason.
        report["delete_reason"] = reason
        # Refresh lifecycle time.
        report["updated_at"] = utc_now()
        # Publish a detached reserved row.
        selected.update(dict(report))
        # Commit complete state.
        return state
    # Serialize the deletion reservation.
    provider.update_document(STATE_DOCUMENT, reserve, _empty_state)
    # Return exact completed replay.
    if selected.get("deleted_at"):
        # Return only tombstone fields.
        return {"report_id": selected["report_id"], "reference": selected["reference"], "deleted_at": selected["deleted_at"], "replayed": True}
    # Scrub every private evidence document after the report becomes nonpublic.
    for descriptor in list(selected.get("attachments") or []):
        # Replace normalized pixels with a fixed deletion tombstone.
        provider.write_document(_attachment_key(report_id, descriptor["attachment_id"]), {"schema_version": STATE_SCHEMA_VERSION, "state": "deleted", "report_id": report_id, "attachment_id": descriptor["attachment_id"], "deleted_at": utc_now()})
    # Share the completed tombstone with the response.
    completed: dict = {}
    # Remove content and publish the tombstone atomically.
    def finish(raw: object) -> dict:
        # Validate authoritative state.
        state = _state(raw)
        # Resolve the reserved deletion.
        report = _find_report(state, report_id)
        # Require the exact deleting action.
        if report is None or report.get("storage_phase") != "deleting" or report.get("delete_action_digest") != action_digest:
            # Preserve current state for recovery.
            raise ConflictError("Problem report deletion requires recovery")
        # Capture one completion time.
        deleted_at = utc_now()
        # Build minimal nonidentifying tombstone metadata.
        tombstone = {"report_id": report_id, "reference": report["reference"], "deleted_at": deleted_at, "delete_reason": reason, "delete_action_digest": action_digest}
        # Remove all report prose, context, evidence descriptors, notes, identity proof, and history.
        state["reports"] = [row for row in state["reports"] if row.get("report_id") != report_id]
        # Remove submission replay mappings for deleted content.
        state["idempotency"] = {key: value for key, value in state["idempotency"].items() if value != report_id}
        # Preserve rates only for reporters with another retained report.
        retained_reporters = {row.get("reporter_reference") for row in state["reports"]}
        # Remove unneeded opaque reporter references.
        state["rate_events"] = [event for event in state["rate_events"] if event.get("reporter_reference") in retained_reporters]
        # Append a bounded tombstone.
        state["tombstones"] = (list(state["tombstones"]) + [tombstone])[-MAX_REPORTS:]
        # Publish the completed tombstone.
        completed.update(tombstone)
        # Commit complete state.
        return state
    # Commit privacy deletion atomically.
    provider.update_document(STATE_DOCUMENT, finish, _empty_state)
    # Return the minimal deletion receipt.
    return {"report_id": completed["report_id"], "reference": completed["reference"], "deleted_at": completed["deleted_at"], "replayed": False}


# Delete one report after explicit Admin confirmation.
def delete_report(report_id: str, body: dict) -> dict:
    # Require structured input.
    if not isinstance(body, dict):
        # Reject ambiguous deletion calls.
        raise ValidationError("Problem report deletion must be an object")
    # Require a strong action key.
    action_key = str(body.get("idempotency_key") or "")
    # Reject absent or malformed keys.
    if not IDEMPOTENCY_PATTERN.fullmatch(action_key):
        # Identify only the invalid field.
        raise ValidationError("A valid idempotency key is required", {"field": "idempotency_key"})
    # Bind deletion to report and caller action.
    action_digest = _digest("feedback-admin-delete", report_id, action_key)
    # Execute the recoverable deletion saga.
    return _delete_internal(report_id, action_digest, "admin_delete")


# Apply bounded retention and recover interrupted deletions.
def cleanup_retention() -> dict:
    # Parse one current instant for all comparisons.
    now = _parse_time(utc_now())
    # Share bounded stale-rate accounting with the response.
    rate_accounting = {"before": 0, "after": 0}
    # Prune expired opaque rate slots inside the same provider transaction used by submissions.
    def prune_rates(raw: object) -> dict:
        # Preserve malformed state by validating the complete document first.
        state = _state(raw)
        # Count the retained registry before pruning.
        rate_accounting["before"] = len(state["rate_events"])
        # Keep only structurally valid events inside the configured enforcement window.
        state["rate_events"] = [event for event in state["rate_events"] if isinstance(event, dict) and event.get("reporter_reference") and event.get("at") and (now - _parse_time(event["at"])).total_seconds() <= config.FEEDBACK_RATE_WINDOW_SECONDS]
        # Count the durable registry after pruning.
        rate_accounting["after"] = len(state["rate_events"])
        # Commit the complete validated document.
        return state
    # Apply the bounded rate-retention cleanup across JSON and MySQL processes.
    get_storage_provider().update_document(STATE_DOCUMENT, prune_rates, _empty_state)
    # Read one consistent post-prune snapshot for content candidate selection.
    state = _read_state()
    # Collect exact deletion tuples.
    candidates = []
    # Inspect retained reports without mutating the snapshot.
    for report in state["reports"]:
        # Resume an interrupted deletion under its original action identity.
        if report.get("storage_phase") == "deleting":
            # Preserve the original reason and action digest.
            candidates.append((report["report_id"], report.get("delete_action_digest"), report.get("delete_reason") or "retention"))
            # Continue to the next row.
            continue
        # Preserve preparing reports for submit retry or operator recovery.
        if report.get("storage_phase") != "committed":
            # Skip nonpublic recovery state.
            continue
        # Measure maximum content age.
        absolute_age = (now - _parse_time(report.get("created_at"))).total_seconds()
        # Measure terminal age only when present.
        terminal_age = (now - _parse_time(report.get("terminal_at"))).total_seconds() if report.get("terminal_at") else 0
        # Select terminal or absolute-age privacy expiry.
        if (report.get("status") in TERMINAL_STATUSES and terminal_age > config.FEEDBACK_TERMINAL_RETENTION_SECONDS) or absolute_age > config.FEEDBACK_MAX_RETENTION_SECONDS:
            # Create a deterministic server-owned recovery identity.
            candidates.append((report["report_id"], _digest("feedback-retention-delete", report["report_id"]), "retention"))
    # Complete candidates serially so provider locks stay bounded.
    receipts = [_delete_internal(report_id, action_digest, reason) for report_id, action_digest, reason in candidates]
    # Return only counts and configured policy.
    return {"deleted": len(receipts), "rate_events_pruned": rate_accounting["before"] - rate_accounting["after"], "terminal_retention_seconds": config.FEEDBACK_TERMINAL_RETENTION_SECONDS, "maximum_retention_seconds": config.FEEDBACK_MAX_RETENTION_SECONDS}
