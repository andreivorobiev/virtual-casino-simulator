#!/usr/bin/env bash
# Pull, verify, activate, and observe immutable Casino releases from the production host. (#732)

set -Eeuo pipefail

readonly REPOSITORY="${CASINO_RELEASE_REPOSITORY:-andreivorobiev/virtual-casino-simulator}"
readonly API_ROOT="${CASINO_GITHUB_API_ROOT:-https://api.github.com}"
readonly INSTALL_ROOT="${CASINO_INSTALL_ROOT:-/opt/casino}"
readonly CURRENT_LINK="${CASINO_CURRENT_LINK:-${INSTALL_ROOT}/current}"
readonly RELEASES_ROOT="${CASINO_RELEASES_ROOT:-${INSTALL_ROOT}/releases}"
readonly RELEASE_ENV="${CASINO_RELEASE_ENV:-/etc/casino/release.env}"
readonly MONITOR_ENV="${CASINO_EDGE_MONITOR_ENV:-/etc/casino/edge-monitor.env}"
readonly POLLER_STATE_ROOT="${CASINO_RELEASE_POLLER_STATE_ROOT:-/var/lib/casino/release-poller}"
readonly ALARM_FILE="${CASINO_RELEASE_POLLER_ALARM_FILE:-${POLLER_STATE_ROOT}/alarm}"
readonly STABLE_POLLER="${CASINO_RELEASE_POLLER_STABLE_PATH:-/usr/local/libexec/casino-release-poller}"
readonly PYTHON="${CASINO_PYTHON:-/opt/casino/venv/bin/python}"
readonly POLL_INTERVAL_SECONDS="${CASINO_RELEASE_POLL_INTERVAL_SECONDS:-300}"
readonly LAG_INTERVAL_MULTIPLIER="${CASINO_RELEASE_LAG_INTERVAL_MULTIPLIER:-3}"
readonly LOCK_FILE="${CASINO_RELEASE_POLLER_LOCK_FILE:-/run/lock/casino-release-poller.lock}"
readonly ASSET_ARCHIVE="virtual_casino_simulator_package.zip"
readonly ASSET_MANIFEST="release-manifest.json"

log() {
  logger -t casino-release-poller -- "$1" 2>/dev/null || printf '%s\n' "$1" >&2
}

fail() {
  log "release_poller=FAIL reason=$1"
  return 1
}

write_alarm() {
  local reason="$1"
  install -d -m 0750 "${POLLER_STATE_ROOT}"
  printf 'status=alarm\nreason=%s\n' "${reason}" > "${ALARM_FILE}.tmp"
  chmod 0640 "${ALARM_FILE}.tmp"
  mv -f "${ALARM_FILE}.tmp" "${ALARM_FILE}"
  log "release_poller=ALARM reason=${reason}"
}

clear_alarm() {
  rm -f "${ALARM_FILE}"
}

clear_transient_lag_alarm() {
  if test -f "${ALARM_FILE}" && grep -Eq '^reason=(release_delivery_lag|release_query_failed)$' "${ALARM_FILE}"; then
    rm -f "${ALARM_FILE}"
  fi
}

cleanup_owned_work_root() {
  local owned_work_root="$1"
  local relative_root="${owned_work_root#"${RELEASES_ROOT}/"}"
  if test "${relative_root}" = "${owned_work_root}" || [[ ! "${relative_root}" =~ ^\.poller\.[A-Za-z0-9]{8}$ ]]; then
    fail "poll_cleanup_root_invalid"
    return 1
  fi
  test -d "${owned_work_root}" && test ! -L "${owned_work_root}" || { fail "poll_cleanup_root_unsafe"; return 1; }
  rm -rf -- "${owned_work_root}"
}

cleanup_deployment() {
  local status="$1"
  local owned_work_root="$2"
  local cleanup_status=0
  trap - EXIT
  cleanup_owned_work_root "${owned_work_root}" || cleanup_status=$?
  if test "${status}" -ne 0; then
    write_alarm "poll_failed"
  elif test "${cleanup_status}" -ne 0; then
    write_alarm "poll_cleanup_failed"
  fi
  if test "${cleanup_status}" -ne 0; then
    return "${cleanup_status}"
  fi
  return "${status}"
}

require_runtime() {
  [[ "${REPOSITORY}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail "invalid_repository"
  [[ "${API_ROOT}" =~ ^https://[A-Za-z0-9._:/-]+$ ]] || fail "invalid_api_root"
  [[ "${POLL_INTERVAL_SECONDS}" =~ ^[1-9][0-9]*$ ]] || fail "invalid_poll_interval"
  [[ "${LAG_INTERVAL_MULTIPLIER}" =~ ^[1-9][0-9]*$ ]] || fail "invalid_lag_multiplier"
  test -x "${PYTHON}" || fail "python_unavailable"
}

decide_versions() {
  "${PYTHON}" - "$1" "$2" <<'PY'
import re
import sys

pattern = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

def parse(value):
    match = pattern.fullmatch(value)
    if match is None:
        raise SystemExit("invalid version")
    return tuple(int(part) for part in match.groups())

installed = parse(sys.argv[1])
latest = parse(sys.argv[2])
if latest > installed:
    print("deploy")
elif latest == installed:
    print("current")
else:
    print("ahead")
PY
}

parse_release_json() {
  "${PYTHON}" - "$1" <<'PY'
import datetime
import json
import re
import sys
from pathlib import Path

release = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False:
    raise SystemExit("latest release is not a public stable release")
tag = release.get("tag_name")
commit = release.get("target_commitish")
if not isinstance(tag, str) or re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag) is None:
    raise SystemExit("latest release tag is invalid")
if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
    raise SystemExit("latest release commit is invalid")
published = release.get("published_at")
if not isinstance(published, str):
    raise SystemExit("latest release publication time is invalid")
published_epoch = int(datetime.datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp())
assets = release.get("assets")
if not isinstance(assets, list):
    raise SystemExit("latest release assets are invalid")
expected = {"checksums.txt", "release-manifest.json", "virtual_casino_simulator_package.zip"}
asset_urls = {}
for asset in assets:
    if not isinstance(asset, dict) or asset.get("name") not in expected:
        raise SystemExit("latest release asset set is not exact")
    name = asset["name"]
    url = asset.get("browser_download_url")
    if name in asset_urls or not isinstance(url, str) or not url.startswith("https://github.com/"):
        raise SystemExit("latest release asset URL is invalid")
    asset_urls[name] = url
if set(asset_urls) != expected or len(assets) != len(expected):
    raise SystemExit("latest release asset set is not exact")
print("\t".join((tag, commit, str(published_epoch), asset_urls["checksums.txt"], asset_urls["release-manifest.json"], asset_urls["virtual_casino_simulator_package.zip"])))
PY
}

query_release() {
  local raw_json="$1"
  "${PYTHON}" - "${API_ROOT}" "${REPOSITORY}" "${raw_json}" <<'PY'
import json
import os
import sys
import urllib.request
from pathlib import Path

api_root, repository, output_path = sys.argv[1:]
headers = {"Accept": "application/vnd.github+json", "User-Agent": "casino-release-poller/1"}
token = os.environ.get("CASINO_GITHUB_RELEASE_TOKEN", "")
if token:
    headers["Authorization"] = f"Bearer {token}"
request = urllib.request.Request(f"{api_root}/repos/{repository}/releases/latest", headers=headers)
with urllib.request.urlopen(request, timeout=15) as response:
    payload = response.read(262145)
if len(payload) > 262144:
    raise SystemExit("release response exceeds the bounded size")
release = json.loads(payload.decode("utf-8"))
Path(output_path).write_text(json.dumps(release, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
PY
  parse_release_json "${raw_json}"
}

download_release() {
  local raw_json="$1"
  local destination="$2"
  "${PYTHON}" - "${raw_json}" "${destination}" <<'PY'
import json
import os
import sys
import urllib.request
from pathlib import Path

release = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
destination = Path(sys.argv[2])
destination.mkdir(parents=True, exist_ok=True)
headers = {"Accept": "application/octet-stream", "User-Agent": "casino-release-poller/1"}
token = os.environ.get("CASINO_GITHUB_RELEASE_TOKEN", "")
if token:
    headers["Authorization"] = f"Bearer {token}"
expected = {"checksums.txt", "release-manifest.json", "virtual_casino_simulator_package.zip"}
assets = {asset.get("name"): asset.get("browser_download_url") for asset in release.get("assets", []) if isinstance(asset, dict) and asset.get("name") in expected}
if set(assets) != expected or len(release.get("assets", [])) != len(expected):
    raise SystemExit("release asset set changed after inspection")
limits = {"checksums.txt": 4096, "release-manifest.json": 2 * 1024 * 1024, "virtual_casino_simulator_package.zip": 128 * 1024 * 1024}
for name in sorted(expected):
    request = urllib.request.Request(assets[name], headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        declared_length = response.headers.get("Content-Length")
        if declared_length is not None and (not declared_length.isdigit() or int(declared_length) > limits[name]):
            raise SystemExit("release asset exceeds the bounded size")
        target = destination / name
        with target.open("wb") as output:
            received = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > limits[name]:
                    raise SystemExit("release asset exceeds the bounded size")
                output.write(chunk)
PY
}

verify_assets() {
  local asset_root="$1"
  local expected_tag="$2"
  local expected_commit="$3"
  local verifier_root="${CASINO_VERIFY_ROOT:-${CURRENT_LINK}}"
  "${PYTHON}" - "${asset_root}" "${expected_tag}" "${expected_commit}" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
tag = sys.argv[2]
commit = sys.argv[3]
expected_names = {"release-manifest.json", "virtual_casino_simulator_package.zip"}
lines = (root / "checksums.txt").read_text(encoding="utf-8").splitlines()
records = {}
for line in lines:
    match = re.fullmatch(r"([0-9a-f]{64})  (release-manifest\.json|virtual_casino_simulator_package\.zip)", line)
    if match is None or match.group(2) in records:
        raise SystemExit("checksums.txt is not canonical")
    records[match.group(2)] = match.group(1)
if set(records) != expected_names:
    raise SystemExit("checksums.txt does not name the exact release assets")
for name, expected_hash in records.items():
    digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if digest != expected_hash:
        raise SystemExit("release asset checksum mismatch")
manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
source = manifest.get("source") if isinstance(manifest, dict) else None
if not isinstance(source, dict) or source.get("release_tag") != tag or source.get("commit_sha") != commit:
    raise SystemExit("release manifest provenance mismatch")
artifact = manifest.get("artifact")
if not isinstance(artifact, dict) or artifact.get("name") != "virtual_casino_simulator_package.zip" or artifact.get("sha256") != records["virtual_casino_simulator_package.zip"]:
    raise SystemExit("release manifest artifact binding mismatch")
PY
  "${PYTHON}" "${verifier_root}/scripts/package_app.py" --verify-only --archive "${asset_root}/${ASSET_ARCHIVE}" --manifest "${asset_root}/${ASSET_MANIFEST}" --expected-commit "${expected_commit}" --expected-tag "${expected_tag}" --require-rollback
}

installed_version() {
  "${PYTHON}" - "${CURRENT_LINK}/modules/module-manifest.json" <<'PY'
import json
import re
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = manifest.get("application") if isinstance(manifest, dict) else None
if not isinstance(version, str) or re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version) is None:
    raise SystemExit("installed application version is invalid")
print(version)
PY
}

installed_commit() {
  "${PYTHON}" - "${RELEASE_ENV}" <<'PY'
import re
import sys
from pathlib import Path

values = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#"):
        continue
    key, separator, value = line.partition("=")
    if not separator or key in values:
        raise SystemExit("release environment is invalid")
    values[key] = value
commit = values.get("CASINO_BUILD_SHA")
if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
    raise SystemExit("installed commit is invalid")
print(commit)
PY
}

verify_live_identity() {
  local expected_version="$1"
  local expected_commit="$2"
  "${PYTHON}" - "${MONITOR_ENV}" "${expected_version}" "${expected_commit}" <<'PY'
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# Bind only the reviewed monitor settings from the root-managed file.
monitor_path, expected_version, expected_commit = sys.argv[1:]
# Accept the same simple assignment shape as the canonical monitor validator.
assignment_pattern = re.compile(r"^(?:export[ \t]+)?([A-Z][A-Z0-9_]*)=(.*)$")
# Name the only two settings this probe may consume from the monitor file.
allowed_names = {"CASINO_EDGE_MONITOR_AUTHORIZATION", "CASINO_PUBLIC_ORIGIN"}
# Start with no file-owned values so duplicates fail closed.
file_values = {}
# Decode the root-managed file without evaluating shell syntax.
for line in Path(monitor_path).read_text(encoding="utf-8").splitlines():
    # Ignore blank and whole-line comment rows.
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    # Parse only one physical assignment row.
    match = assignment_pattern.fullmatch(line)
    # Reject malformed rows that target either protected setting.
    if match is None and any(line.lstrip().startswith(name) for name in allowed_names):
        raise SystemExit("monitor configuration is invalid")
    # Ignore unrelated settings without interpreting their values.
    if match is None or match.group(1) not in allowed_names:
        continue
    # Reject duplicate protected assignments before selecting a value.
    if match.group(1) in file_values:
        raise SystemExit("monitor configuration is invalid")
    # Retain only an allowlisted value in memory.
    file_values[match.group(1)] = match.group(2)
# Prefer an already supplied service value and otherwise use the reviewed file.
authorization = os.environ.get("CASINO_EDGE_MONITOR_AUTHORIZATION") or file_values.get("CASINO_EDGE_MONITOR_AUTHORIZATION", "")
# Require the canonical strong bearer shape without reflecting its contents.
if re.fullmatch(r"Bearer [\x21-\x7e]{32,512}", authorization) is None:
    raise SystemExit("monitor authorization is unavailable")
# Prefer an already supplied service origin, then an allowlisted file value, then the public default.
origin = os.environ.get("CASINO_PUBLIC_ORIGIN") or file_values.get("CASINO_PUBLIC_ORIGIN") or "https://casino.tiltseven.com"
# Parse the origin structurally before using it for requests.
parsed_origin = urllib.parse.urlsplit(origin)
# Require one HTTPS authority without credentials, query, fragment, or a path prefix.
if parsed_origin.scheme != "https" or not parsed_origin.netloc or parsed_origin.username is not None or parsed_origin.password is not None or parsed_origin.path not in ("", "/") or parsed_origin.query or parsed_origin.fragment:
    raise SystemExit("monitor public origin is invalid")
# Normalize only the optional trailing slash after validation.
origin = origin.rstrip("/")
def request(path, authenticated):
    headers = {"Accept": "application/json", "User-Agent": "casino-release-poller/1"}
    if authenticated:
        headers["Authorization"] = authorization
    with urllib.request.urlopen(urllib.request.Request(origin + path, headers=headers), timeout=10) as response:
        payload = response.read(65537)
    if len(payload) > 65536:
        raise SystemExit("probe response exceeds bounded size")
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, dict) or parsed.get("ok") is not True or not isinstance(parsed.get("data"), dict):
        raise SystemExit("probe response is invalid")
    return parsed["data"]
health = request("/healthz", False)
ready = request("/readyz", True)
if health.get("status") != "live" or ready.get("ready") is not True:
    raise SystemExit("production probes are not green")
build = ready.get("build")
if not isinstance(build, dict) or build.get("app_version") != expected_version or build.get("sha") != expected_commit:
    raise SystemExit("production build identity does not match the release")
PY
}

current_release_root() {
  readlink -f "${CURRENT_LINK}"
}

activate_release() {
  local release_root="$1"
  ln -sfn "${release_root}" "${CURRENT_LINK}.next"
  mv -Tf "${CURRENT_LINK}.next" "${CURRENT_LINK}"
  test "$(readlink -f "${CURRENT_LINK}")" = "${release_root}"
}

validate_monitor_configuration() {
  local candidate_root="$1"
  "${PYTHON}" "${candidate_root}/scripts/validate_monitor_config.py" check --monitor-env "${MONITOR_ENV}" --application-env /etc/casino/casino.env
}

write_release_environment() {
  local candidate_root="$1"
  local manifest_path="$2"
  local destination="$3"
  "${PYTHON}" "${candidate_root}/scripts/write_release_env.py" --manifest "${manifest_path}" --destination "${destination}"
}

compare_release_roots() {
  local candidate_root="$1"
  local release_root="$2"
  "${PYTHON}" - "${candidate_root}" "${release_root}" <<'PY'
import hashlib
import sys
from pathlib import Path

def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise SystemExit("release roots may not contain symbolic links")
        if path.is_file():
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            result[relative + "/"] = None
        else:
            raise SystemExit("release roots contain unsupported entries")
    return result

if inventory(Path(sys.argv[1])) != inventory(Path(sys.argv[2])):
    raise SystemExit("existing release root does not match the verified archive")
PY
}

check_schema_two() {
  local root="$1"
  PYTHONPATH="${root}" "${PYTHON}" "${root}/scripts/mysql_migrate.py" bridge-check-schema2
}

observe_release() {
  local version="$1"
  local commit="$2"
  "${PYTHON}" "${CURRENT_LINK}/scripts/run_edge_monitor.py" --monitor-env "${MONITOR_ENV}" --policy "${CURRENT_LINK}/deploy/edge/restricted-preview.json"
  verify_live_identity "${version}" "${commit}"
}

rollback_release() {
  local prior_release="$1"
  local prior_env="$2"
  local prior_version="$3"
  local prior_commit="$4"
  activate_release "${prior_release}"
  if test -s "${prior_env}"; then
    install -m 0640 -o root -g root "${prior_env}" "${RELEASE_ENV}"
  else
    rm -f "${RELEASE_ENV}"
  fi
  systemctl restart casino
  systemctl reload nginx
  check_schema_two "${prior_release}"
  observe_release "${prior_version}" "${prior_commit}"
}

deploy_latest() {
  local mode="$1"
  require_runtime
  test "$(id -u)" -eq 0 || fail "root_required"
  install -d -m 0755 "${RELEASES_ROOT}"
  install -d -m 0750 "${POLLER_STATE_ROOT}"
  exec 9>"${LOCK_FILE}"
  flock -n 9 || fail "poll_already_running"
  local work_root
  work_root="$(mktemp -d "${RELEASES_ROOT}/.poller.XXXXXXXX")"
  local cleanup_command
  printf -v cleanup_command 'cleanup_deployment "$?" %q' "${work_root}"
  trap "${cleanup_command}" EXIT
  local prior_env="${work_root}/prior-release.env"
  local metadata="${work_root}/release.json"
  local fields
  fields="$(query_release "${metadata}")"
  local latest_tag latest_commit published_epoch checksum_url manifest_url archive_url
  IFS=$'\t' read -r latest_tag latest_commit published_epoch checksum_url manifest_url archive_url <<<"${fields}"
  test -n "${archive_url}" || fail "release_metadata_incomplete"
  local current_version current_commit decision
  current_version="$(installed_version)"
  current_commit="$(installed_commit)"
  decision="$(decide_versions "${current_version}" "${latest_tag}")"
  if test "${decision}" = "current" && test "${current_commit}" != "${latest_commit}"; then
    fail "release_identity_conflict"
  fi
  if test "${decision}" != "deploy"; then
    cleanup_owned_work_root "${work_root}"
    trap - EXIT
    clear_alarm
    log "release_poller=PASS decision=${decision} installed=v${current_version} latest=${latest_tag}"
    return 0
  fi
  download_release "${metadata}" "${work_root}"
  CASINO_VERIFY_ROOT="${CURRENT_LINK}" verify_assets "${work_root}" "${latest_tag}" "${latest_commit}"
  unzip -q "${work_root}/${ASSET_ARCHIVE}" -d "${work_root}/extracted"
  local candidate_root="${work_root}/extracted/virtual_casino_simulator"
  test -d "${candidate_root}" || fail "archive_root_missing"
  CASINO_VERIFY_ROOT="${candidate_root}" verify_assets "${work_root}" "${latest_tag}" "${latest_commit}"
  validate_monitor_configuration "${candidate_root}"
  check_schema_two "${candidate_root}"
  write_release_environment "${candidate_root}" "${work_root}/${ASSET_MANIFEST}" "${work_root}/release.env"
  local release_root="${RELEASES_ROOT}/${latest_commit}"
  if test -e "${release_root}"; then
    test -d "${release_root}" && test ! -L "${release_root}" || fail "release_root_unsafe"
    compare_release_roots "${candidate_root}" "${release_root}"
  else
    mv "${candidate_root}" "${release_root}"
  fi
  local prior_release
  prior_release="$(current_release_root)"
  test -d "${prior_release}" || fail "prior_release_missing"
  if test -f "${RELEASE_ENV}"; then
    cp -p "${RELEASE_ENV}" "${prior_env}"
  else
    : > "${prior_env}"
  fi
  local switched=0
  rollback_on_error() {
    local status=$?
    trap - ERR
    if test "${switched}" -eq 1; then
      rollback_release "${prior_release}" "${prior_env}" "${current_version}" "${current_commit}" || true
    fi
    return "${status}"
  }
  trap rollback_on_error ERR
  install -m 0640 -o root -g root "${work_root}/release.env" "${RELEASE_ENV}"
  activate_release "${release_root}"
  switched=1
  systemctl restart casino
  systemctl reload nginx
  check_schema_two "${release_root}"
  observe_release "${latest_tag#v}" "${latest_commit}"
  if test "${mode}" = "rollback-drill"; then
    rollback_release "${prior_release}" "${prior_env}" "${current_version}" "${current_commit}"
    switched=0
    trap - ERR
    clear_alarm
    cleanup_owned_work_root "${work_root}"
    trap - EXIT
    log "release_poller=PASS decision=rollback_drill candidate=${latest_tag} restored=v${current_version}"
    return 0
  fi
  install -m 0755 "${release_root}/deploy/pull/casino-release-poller.sh" "${STABLE_POLLER}.next"
  mv -f "${STABLE_POLLER}.next" "${STABLE_POLLER}"
  switched=0
  trap - ERR
  clear_alarm
  cleanup_owned_work_root "${work_root}"
  trap - EXIT
  log "release_poller=PASS decision=deployed release=${latest_tag} commit=${latest_commit}"
}

check_lag() {
  require_runtime
  local work_root
  work_root="$(mktemp -d)"
  trap 'rm -rf "${work_root}"' RETURN
  local fields
  fields="$(query_release "${work_root}/release.json")" || { write_alarm "release_query_failed"; return 1; }
  local latest_tag latest_commit published_epoch checksum_url manifest_url archive_url
  IFS=$'\t' read -r latest_tag latest_commit published_epoch checksum_url manifest_url archive_url <<<"${fields}"
  test -n "${archive_url}" || fail "release_metadata_incomplete"
  local current_version current_commit decision maximum_lag age
  current_version="$(installed_version)"
  current_commit="$(installed_commit)"
  decision="$(decide_versions "${current_version}" "${latest_tag}")"
  maximum_lag=$((POLL_INTERVAL_SECONDS * LAG_INTERVAL_MULTIPLIER))
  age=$(($(date +%s) - published_epoch))
  if test "${decision}" = "deploy" && test "${age}" -gt "${maximum_lag}"; then
    write_alarm "release_delivery_lag"
    return 1
  fi
  if test "${decision}" = "current" && test "${current_commit}" != "${latest_commit}"; then
    write_alarm "release_identity_conflict"
    return 1
  fi
  clear_transient_lag_alarm
  log "release_poller=PASS lag_check=${decision} installed=v${current_version} latest=${latest_tag} age_seconds=${age} threshold_seconds=${maximum_lag}"
}

main() {
  case "${1:-}" in
    decide)
      test "$#" -eq 3 || fail "usage_decide"
      decide_versions "$2" "$3"
      ;;
    inspect-release-json)
      test "$#" -eq 2 || fail "usage_inspect_release_json"
      parse_release_json "$2"
      ;;
    verify-assets)
      test "$#" -eq 4 || fail "usage_verify_assets"
      require_runtime
      verify_assets "$2" "$3" "$4"
      ;;
    check-lag)
      test "$#" -eq 1 || fail "usage_check_lag"
      check_lag
      ;;
    poll)
      test "$#" -eq 1 || fail "usage_poll"
      deploy_latest "deploy"
      ;;
    rollback-drill)
      test "$#" -eq 1 || fail "usage_rollback_drill"
      deploy_latest "rollback-drill"
      ;;
    *)
      fail "usage"
      ;;
  esac
}

if test "${BASH_SOURCE[0]}" = "$0"; then
  main "$@"
fi
