"""Safe persisted player problem reports and Admin triage for issue #349."""

# Import base64 decoding so browser-provided image payloads never reach storage unvalidated.
import base64
# Import in-memory byte streams for metadata-stripping image normalization.
from io import BytesIO
# Import regular expressions for bounded idempotency keys and route context.
import re

# Import Pillow's decoder and encoder for server-side image verification and metadata removal.
from PIL import Image, UnidentifiedImageError

# Import application version for a server-authored diagnostic field.
from casino.config import APP_VERSION
# Import stable public errors for invalid report input and missing report references.
from casino.errors import NotFoundError, ValidationError
# Import UTC timestamps and random identifiers through existing core boundaries.
from casino.core.clock import utc_now
# Import the shared identifier generator.
from casino.core.ids import new_id
# Import the configured JSON or MySQL document provider.
from casino.core.storage import get_storage_provider

# Name the compact report index document stored by either supported provider.
INDEX_DOCUMENT = "feedback_report_index"
# Enumerate user-selectable report categories.
ALLOWED_CATEGORIES = frozenset({"bug", "visual", "accessibility", "performance", "content", "other"})
# Enumerate the repository's governed priority taxonomy; P4 is intentionally absent.
ALLOWED_PRIORITIES = frozenset({"P1", "P2", "P3"})
# Enumerate internal workflow states that preserve rather than delete report history.
ALLOWED_STATUSES = frozenset({"new", "triaged", "linked", "resolved", "duplicate", "rejected"})
# Permit only low-cardinality application locales in diagnostic context.
ALLOWED_LOCALES = frozenset({"en-US", "ru-RU"})
# Permit only browser families produced by the privacy-reducing client classifier.
ALLOWED_BROWSER_FAMILIES = frozenset({"Chrome", "Edge", "Firefox", "Safari", "Other"})
# Permit only operating-system families produced by the privacy-reducing client classifier.
ALLOWED_OS_FAMILIES = frozenset({"Android", "iOS", "Linux", "macOS", "Windows", "Other"})
# Bound one client-compressed image before the server performs any decode work.
MAX_SOURCE_IMAGE_BYTES = 210_000
# Bound the sum of decoded source payloads inside one report.
MAX_TOTAL_SOURCE_BYTES = 650_000
# Limit report attachments to a small, reviewable set.
MAX_ATTACHMENTS = 3
# Reject decompression bombs before Pillow allocates an unreasonable image surface.
MAX_IMAGE_PIXELS = 12_000_000
# Bound normalized evidence dimensions while retaining readable desktop screenshots.
MAX_IMAGE_DIMENSION = 1_920
# Bound retained reports in the list index without deleting canonical detail documents.
MAX_INDEX_REPORTS = 2_000
# Validate browser-generated idempotency keys without accepting arbitrary document-like values.
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,100}$")
# Validate a route-only browser context without query strings, fragments, or absolute origins.
ROUTE_PATTERN = re.compile(r"^/[A-Za-z0-9_./-]{0,180}$")
# Validate optional manually linked GitHub issue URLs against the owned repository.
GITHUB_ISSUE_PATTERN = re.compile(r"^https://github\.com/andreivorobiev/virtual-casino-simulator/issues/[1-9][0-9]*$")


# Build a fresh index so default evaluation never shares mutable state.
def _empty_index() -> dict:
    # Return independent lists and maps for safe provider mutation.
    return {"reports": [], "idempotency": {}}


# Return one canonical report document key from a server-authored identifier.
def _report_key(report_id: str) -> str:
    # Prefix the identifier so report details cannot collide with another document family.
    return f"feedback_report_{report_id}"


# Normalize one bounded text field and produce field-specific validation details.
def _text(value, field: str, minimum: int, maximum: int) -> str:
    # Collapse surrounding whitespace while preserving intentional line breaks inside descriptions.
    normalized = str(value or "").strip()
    # Reject absent or overly long content with stable machine-readable field context.
    if len(normalized) < minimum or len(normalized) > maximum:
        # Avoid echoing the supplied text in the public error.
        raise ValidationError(f"{field} must be between {minimum} and {maximum} characters", {"field": field})
    # Return the validated user-authored prose.
    return normalized


# Decode, validate, resize, and re-encode one screenshot without retaining metadata.
def _normalize_attachment(item: dict, position: int) -> dict:
    # Require object input so scalars cannot bypass named-field validation.
    if not isinstance(item, dict):
        # Identify only the invalid attachment position.
        raise ValidationError("Each screenshot must be an image object", {"attachment": position})
    # Read the data URL or bare base64 content without retaining a caller-authored file path.
    encoded = str(item.get("data") or "")
    # Remove one allowlisted data-URL prefix before strict base64 decoding.
    if encoded.startswith("data:"):
        # Split on the first comma and reject a malformed header.
        parts = encoded.split(",", 1)
        # Require an image data URL with base64 transfer encoding.
        if len(parts) != 2 or ";base64" not in parts[0] or not parts[0].startswith("data:image/"):
            # Return a stable field diagnostic.
            raise ValidationError("Screenshot data URL is invalid", {"attachment": position})
        # Retain only the encoded bytes after the header.
        encoded = parts[1]
    # Decode strict base64 so ignored punctuation cannot conceal a larger payload.
    try:
        # Convert the browser payload into bounded source bytes.
        raw = base64.b64decode(encoded, validate=True)
    # Collapse malformed encoding into a stable validation result.
    except (ValueError, base64.binascii.Error) as exc:
        # Chain the internal decoder error without exposing it publicly.
        raise ValidationError("Screenshot encoding is invalid", {"attachment": position}) from exc
    # Reject empty and oversized sources before image parsing.
    if not raw or len(raw) > MAX_SOURCE_IMAGE_BYTES:
        # Publish only the reviewed per-image bound.
        raise ValidationError("Screenshot exceeds the 210 KB upload limit", {"attachment": position})
    # Start protected image parsing so malformed input becomes a validation envelope.
    try:
        # Open the source through Pillow so format claims are not trusted.
        with Image.open(BytesIO(raw)) as source:
            # Reject oversized declared dimensions before forcing pixel allocation.
            if source.width * source.height > MAX_IMAGE_PIXELS:
                # Keep the diagnostic independent of source dimensions.
                raise ValidationError("Screenshot dimensions exceed the safe upload limit", {"attachment": position})
            # Force complete decode while the guarded source stream remains open.
            source.load()
            # Reject formats outside the feature's explicit allowlist.
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                # Keep the rejection independent of the untrusted claimed media type.
                raise ValidationError("Screenshot must be PNG, JPEG, or WebP", {"attachment": position})
            # Convert to RGB so EXIF, ICC, text chunks, alpha metadata, and animation frames are discarded.
            normalized = source.convert("RGB")
            # Resize only when needed while retaining the original aspect ratio.
            normalized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            # Allocate a clean output buffer containing no caller-supplied metadata.
            output = BytesIO()
            # Encode a compact, universally previewable JPEG with deterministic quality settings.
            normalized.save(output, format="JPEG", quality=76, optimize=True, progressive=True)
            # Read the normalized evidence bytes after encoding completes.
            sanitized = output.getvalue()
            # Return storage-ready evidence with server-authored dimensions and name.
            return {"attachment_id": new_id("evidence"), "name": f"screenshot-{position}.jpg", "media_type": "image/jpeg", "width": normalized.width, "height": normalized.height, "bytes": len(sanitized), "data": base64.b64encode(sanitized).decode("ascii")}
    # Convert decoder errors and decompression warnings into the same safe diagnostic.
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        # Avoid returning decoder-specific details that could expose library internals.
        raise ValidationError("Screenshot could not be safely decoded", {"attachment": position}) from exc


# Validate the browser's privacy-reduced diagnostic context.
def _context(value) -> dict:
    # Treat omitted context as an empty object rather than caller-controlled defaults.
    supplied = value if isinstance(value, dict) else {}
    # Read a relative route without retaining its query string or fragment.
    route = str(supplied.get("route") or "/").split("?", 1)[0].split("#", 1)[0]
    # Replace an invalid route with the root rather than preserving hostile content.
    route = route if ROUTE_PATTERN.fullmatch(route) else "/"
    # Read an allowlisted locale only.
    locale = str(supplied.get("locale") or "en-US")
    # Fall back to English when a browser supplies an unsupported locale.
    locale = locale if locale in ALLOWED_LOCALES else "en-US"
    # Read bounded numeric viewport values without accepting arbitrary nested data.
    try:
        # Clamp width to the reviewed browser range.
        width = max(240, min(int(supplied.get("viewport_width") or 0), 8_000))
        # Clamp height to the reviewed browser range.
        height = max(240, min(int(supplied.get("viewport_height") or 0), 8_000))
    # Replace malformed dimensions with a neutral zero pair.
    except (TypeError, ValueError):
        # Preserve no caller-authored invalid dimension.
        width, height = 0, 0
    # Read only a low-cardinality client browser family.
    browser = str(supplied.get("browser_family") or "Other")
    # Replace arbitrary browser strings with the privacy-reduced fallback.
    browser = browser if browser in ALLOWED_BROWSER_FAMILIES else "Other"
    # Read only a low-cardinality OS family.
    operating_system = str(supplied.get("os_family") or "Other")
    # Replace arbitrary platform strings with the privacy-reduced fallback.
    operating_system = operating_system if operating_system in ALLOWED_OS_FAMILIES else "Other"
    # Return the strict privacy-reduced context contract.
    return {"route": route, "locale": locale, "viewport_width": width, "viewport_height": height, "browser_family": browser, "os_family": operating_system, "reduced_motion": bool(supplied.get("reduced_motion")), "app_version": APP_VERSION}


# Build the index-safe subset of one canonical report.
def _summary(report: dict) -> dict:
    # Return no attachment content or Admin notes in list responses.
    return {key: report[key] for key in ("report_id", "reference", "category", "priority", "status", "summary", "route", "locale", "reporter_user_id", "attachment_count", "created_at", "updated_at", "github_issue_url")}


# Create one idempotent authenticated report and return its public reference.
def submit(user: dict, body: dict) -> dict:
    # Require an object payload so arrays and scalars fail as validation rather than internal errors.
    if not isinstance(body, dict):
        # Return the standard public validation envelope without reflecting the supplied value.
        raise ValidationError("Problem report body must be an object")
    # Reject guest-trial principals until that separate privacy and abuse gate is approved.
    if str(user.get("identity_provider") or "").lower() == "guest":
        # Keep the restriction explicit rather than silently losing a disposable reporter link.
        raise ValidationError("Problem reports currently require a registered account")
    # Require a strong browser-generated idempotency key for retry-safe submission.
    idempotency_key = str(body.get("idempotency_key") or "")
    # Reject absent or malformed keys before any attachment work.
    if not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
        # Identify the field without reflecting its content.
        raise ValidationError("A valid idempotency key is required", {"field": "idempotency_key"})
    # Read the configured provider once for this operation.
    provider = get_storage_provider()
    # Return an existing report before reprocessing evidence on a safe retry.
    existing_id = provider.read_document(INDEX_DOCUMENT, _empty_index).get("idempotency", {}).get(f"{user.get('user_id')}:{idempotency_key}")
    # Branch when the same identity already completed this action.
    if existing_id:
        # Read the canonical report to return its stable reference.
        existing = provider.read_document(_report_key(existing_id), None)
        # Return the prior success when its canonical document remains available.
        if existing:
            # Expose no report contents in the retry response.
            return {"report_id": existing["report_id"], "reference": existing["reference"], "status": existing["status"], "replayed": True}
    # Normalize the category against the stable taxonomy.
    category = str(body.get("category") or "bug").lower()
    # Reject unknown categories instead of creating uncontrolled label values.
    if category not in ALLOWED_CATEGORIES:
        # Return a field-scoped validation error.
        raise ValidationError("Report category is invalid", {"field": "category"})
    # Validate the required player-authored fields.
    summary = _text(body.get("summary"), "summary", 5, 140)
    # Validate the observed behavior description.
    actual = _text(body.get("actual"), "actual", 5, 4_000)
    # Validate the expected behavior description.
    expected = _text(body.get("expected"), "expected", 5, 2_000)
    # Read only a list of attachments.
    attachments_input = body.get("attachments") or []
    # Reject non-list or oversized attachment collections.
    if not isinstance(attachments_input, list) or len(attachments_input) > MAX_ATTACHMENTS:
        # Publish the bounded collection limit.
        raise ValidationError("A report can include up to three screenshots", {"field": "attachments"})
    # Normalize every supplied image independently.
    attachments = [_normalize_attachment(item, index + 1) for index, item in enumerate(attachments_input)]
    # Reject a report whose combined source declarations exceed the request-owned ceiling.
    if sum(int(item.get("bytes") or 0) for item in attachments) > MAX_TOTAL_SOURCE_BYTES:
        # Keep the aggregate error independent of image contents.
        raise ValidationError("Combined screenshots exceed the report upload limit", {"field": "attachments"})
    # Sanitize the browser diagnostic context.
    context = _context(body.get("context"))
    # Allocate the canonical server report identifier.
    report_id = new_id("report")
    # Build a short human reference suitable for confirmation and search.
    reference = f"RPT-{report_id.rsplit('_', 1)[-1][:8].upper()}"
    # Capture one timestamp for both lifecycle fields.
    created_at = utc_now()
    # Build the canonical detail document with a governed default P2 priority.
    report = {"report_id": report_id, "reference": reference, "category": category, "priority": "P2", "status": "new", "summary": summary, "actual": actual, "expected": expected, "route": context["route"], "locale": context["locale"], "context": context, "reporter_user_id": str(user.get("user_id") or ""), "reporter_display_name": str(user.get("display_name") or "")[:120], "attachments": attachments, "attachment_count": len(attachments), "admin_notes": "", "labels": ["P2", "bug" if category in {"bug", "visual", "accessibility", "performance"} else "enhancement"], "github_issue_url": "", "created_at": created_at, "updated_at": created_at}
    # Persist canonical detail before advertising it in the list index.
    provider.write_document(_report_key(report_id), report)
    # Define one atomic index mutation that also enforces idempotency across processes.
    def add_to_index(index: dict) -> dict:
        # Repair a malformed or legacy index shape conservatively.
        current = index if isinstance(index, dict) else _empty_index()
        # Copy report rows so provider-owned input is not mutated unexpectedly.
        reports = list(current.get("reports") or [])
        # Copy idempotency entries so safe retries remain associated with the reporter identity.
        idempotency = dict(current.get("idempotency") or {})
        # Name the per-user action identity.
        action_key = f"{user.get('user_id')}:{idempotency_key}"
        # Preserve the first committed report when concurrent retries race.
        if action_key in idempotency:
            # Return the unmodified index with stable container types.
            return {"reports": reports, "idempotency": idempotency}
        # Append the attachment-free summary for Admin listing.
        reports.append(_summary(report))
        # Retain only the newest bounded set while canonical report documents remain available by reference.
        reports = reports[-MAX_INDEX_REPORTS:]
        # Record the action identity for future safe retries.
        idempotency[action_key] = report_id
        # Remove idempotency entries whose report fell outside the bounded list index.
        retained_ids = {item.get("report_id") for item in reports}
        # Return the normalized compact index.
        return {"reports": reports, "idempotency": {key: value for key, value in idempotency.items() if value in retained_ids}}
    # Atomically publish the report summary and idempotency mapping.
    updated_index = provider.update_document(INDEX_DOCUMENT, add_to_index, _empty_index)
    # Resolve a concurrent retry winner when this detail was not the indexed result.
    winner_id = updated_index.get("idempotency", {}).get(f"{user.get('user_id')}:{idempotency_key}")
    # Load the winner if another process committed first.
    winner = provider.read_document(_report_key(winner_id), report) if winner_id else report
    # Return the identifier-only confirmation contract.
    return {"report_id": winner["report_id"], "reference": winner["reference"], "status": winner["status"], "replayed": winner["report_id"] != report_id}


# List compact reports for the Admin inbox with bounded filters.
def list_reports(filters: dict | None = None) -> list[dict]:
    # Read the canonical attachment-free index.
    reports = list(get_storage_provider().read_document(INDEX_DOCUMENT, _empty_index).get("reports") or [])
    # Read optional exact filters from a safe mapping.
    supplied = filters or {}
    # Apply only allowlisted priority filtering.
    priority = str(supplied.get("priority") or "")
    # Apply only allowlisted lifecycle filtering.
    status = str(supplied.get("status") or "")
    # Apply only allowlisted category filtering.
    category = str(supplied.get("category") or "")
    # Reject unsupported values so typos cannot masquerade as an empty inbox.
    if priority and priority not in ALLOWED_PRIORITIES:
        # Identify the invalid filter category.
        raise ValidationError("Feedback priority filter is invalid")
    # Reject unsupported workflow states.
    if status and status not in ALLOWED_STATUSES:
        # Identify the invalid filter category.
        raise ValidationError("Feedback status filter is invalid")
    # Reject unsupported report categories.
    if category and category not in ALLOWED_CATEGORIES:
        # Identify the invalid filter category.
        raise ValidationError("Feedback category filter is invalid")
    # Filter newest-first without mutating canonical ordering.
    return [item for item in reversed(reports) if (not priority or item.get("priority") == priority) and (not status or item.get("status") == status) and (not category or item.get("category") == category)]


# Read one canonical report for Admin detail.
def detail(report_id: str) -> dict:
    # Load the document by a router-validated server identifier.
    report = get_storage_provider().read_document(_report_key(report_id), None)
    # Reject absent references without exposing storage internals.
    if not report:
        # Return the standard not-found envelope.
        raise NotFoundError("Problem report was not found")
    # Return the canonical internal report.
    return report


# Update triage fields while preserving report history and evidence.
def update(report_id: str, body: dict) -> dict:
    # Require an object payload so malformed JSON shapes cannot become internal attribute errors.
    if not isinstance(body, dict):
        # Return a stable public validation result.
        raise ValidationError("Problem report update must be an object")
    # Read the current canonical detail before validating partial fields.
    current = detail(report_id)
    # Copy the document so storage defaults cannot be mutated by reference.
    updated = dict(current)
    # Validate and apply an optional lifecycle state.
    if "status" in body:
        # Normalize the requested state.
        status = str(body.get("status") or "").lower()
        # Reject unknown states.
        if status not in ALLOWED_STATUSES:
            # Return a field-specific error.
            raise ValidationError("Problem report status is invalid", {"field": "status"})
        # Apply the validated state.
        updated["status"] = status
    # Validate and apply an optional governed priority.
    if "priority" in body:
        # Normalize priority spelling.
        priority = str(body.get("priority") or "").upper()
        # Reject P4 and arbitrary values through the authoritative taxonomy.
        if priority not in ALLOWED_PRIORITIES:
            # Return a field-specific error.
            raise ValidationError("Problem report priority must be P1, P2, or P3", {"field": "priority"})
        # Apply the validated priority.
        updated["priority"] = priority
    # Apply bounded internal notes when present.
    if "admin_notes" in body:
        # Permit an empty note while bounding retained text.
        notes = str(body.get("admin_notes") or "").strip()
        # Reject oversized internal notes.
        if len(notes) > 4_000:
            # Identify the invalid field.
            raise ValidationError("Admin notes must not exceed 4000 characters", {"field": "admin_notes"})
        # Store the validated note.
        updated["admin_notes"] = notes
    # Apply an optional reviewed GitHub issue link.
    if "github_issue_url" in body:
        # Normalize the linked URL.
        issue_url = str(body.get("github_issue_url") or "").strip()
        # Reject foreign repositories and non-issue links.
        if issue_url and not GITHUB_ISSUE_PATTERN.fullmatch(issue_url):
            # Return a field-specific error without reflecting the URL.
            raise ValidationError("GitHub issue URL must belong to the Casino repository", {"field": "github_issue_url"})
        # Store the reviewed link.
        updated["github_issue_url"] = issue_url
        # Move linked reports into the linked state unless an Admin selected a terminal state.
        if issue_url and updated.get("status") in {"new", "triaged"}:
            # Record the explicit linkage lifecycle.
            updated["status"] = "linked"
    # Rebuild labels from governed priority and category rather than accepting arbitrary caller labels.
    updated["labels"] = [updated["priority"], "bug" if updated["category"] in {"bug", "visual", "accessibility", "performance"} else "enhancement"]
    # Update the lifecycle timestamp after every accepted mutation.
    updated["updated_at"] = utc_now()
    # Persist the canonical detail document.
    provider = get_storage_provider()
    # Write the complete report with evidence unchanged.
    provider.write_document(_report_key(report_id), updated)
    # Define an index mutation that replaces only the matching compact summary.
    def replace_summary(index: dict) -> dict:
        # Normalize the index container.
        normalized = index if isinstance(index, dict) else _empty_index()
        # Replace the matching entry without reordering it.
        reports = [_summary(updated) if item.get("report_id") == report_id else item for item in list(normalized.get("reports") or [])]
        # Preserve the idempotency map unchanged.
        return {"reports": reports, "idempotency": dict(normalized.get("idempotency") or {})}
    # Publish the updated summary atomically.
    provider.update_document(INDEX_DOCUMENT, replace_summary, _empty_index)
    # Return the updated canonical detail.
    return updated


# Build a sanitized GitHub issue draft for explicit Admin review and manual publication.
def github_draft(report_id: str) -> dict:
    # Load the canonical internal report.
    report = detail(report_id)
    # Map the safe route and browser diagnostics into a bounded issue body.
    context = report.get("context") or {}
    # Create a concise title without reporter identity.
    title = f"[{report['category'].title()}] {report['summary']}"
    # Build Markdown that excludes Admin notes, reporter identity, and encoded attachments.
    body = "\n".join((f"Internal report: `{report['reference']}`", "", "## What happened", report["actual"], "", "## Expected", report["expected"], "", "## Reproduction context", f"- Route: `{report['route']}`", f"- App version: `{context.get('app_version', APP_VERSION)}`", f"- Locale: `{report['locale']}`", f"- Viewport: `{context.get('viewport_width', 0)} × {context.get('viewport_height', 0)}`", f"- Browser family: `{context.get('browser_family', 'unknown')}`", f"- OS family: `{context.get('os_family', 'unknown')}`", f"- Reduced motion: `{bool(context.get('reduced_motion'))}`", f"- Screenshots retained internally: {report['attachment_count']}", "", "Screenshots and reporter identity remain in the Admin inbox and are not published automatically."))
    # Return only governed labels and reviewable prose; no external mutation occurs here.
    return {"title": title[:256], "body": body, "labels": list(report.get("labels") or [report["priority"], "bug"]), "source_report_id": report_id}
