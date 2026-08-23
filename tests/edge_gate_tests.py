# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused listener-free edge preparation and observation evidence for TEST-050."""

# Import copies so policy mutations cannot affect shared fixtures.
import copy
# Import JSON support for isolated declarative policy mutations.
import json
# Import filesystem copying for complete inert template fixtures.
import shutil
# Import disposable directories for tests that never touch repository assets.
import tempfile
# Import portable paths for the isolated edge packet.
from pathlib import Path
# Import the repository's dependency-free unit-test framework.
import unittest
# Import mocks that prove validation and cookie refusal do not use the network.
from unittest import mock

# Import only the repository-side edge gate contract under test.
from scripts import edge_gate

# Resolve the checkout root independently of the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Mirror the exact stable #203 response security headers in mocked edge evidence.
GREEN_HEADERS = {"Content-Security-Policy": "default-src 'self'", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY", "Strict-Transport-Security": "max-age=31536000"}


# Validate fail-closed static policy and sanitized read-only observation behavior.
class EdgeGateTests(unittest.TestCase):
    # Create one complete isolated policy and template tree for each test.
    def setUp(self):
        # Allocate a disposable root that unittest cleanup always removes.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-edge-test-")
        # Register cleanup immediately so assertion failures cannot retain the fixture.
        self.addCleanup(self.temporary.cleanup)
        # Resolve the temporary repository-shaped root.
        self.root = Path(self.temporary.name)
        # Copy only inert deploy assets required by the validator.
        shutil.copytree(ROOT / "deploy", self.root / "deploy")
        # Retain the isolated canonical policy path for concise test mutations.
        self.policy_path = self.root / "deploy" / "edge" / "restricted-preview.json"

    # Read a fresh isolated policy mapping.
    def read_policy(self):
        # Decode the test-local policy without touching the checkout copy.
        return json.loads(self.policy_path.read_text(encoding="utf-8"))

    # Persist one deliberately mutated policy mapping into the isolated fixture.
    def write_policy(self, policy):
        # Write canonical readable JSON only inside the disposable test root.
        self.policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

    # Return deterministic successful endpoint evidence for the three exact probes.
    def green_fetcher(self, url, monitor_header, timeout, maximum_body_bytes):
        # Assert the monitor retains its reviewed timeout and body bounds.
        self.assertEqual((timeout, maximum_body_bytes), (5, 65536))
        # Return the anonymous minimal liveness record without requiring a cookie.
        if url.endswith("/healthz"):
            # Prove the secret is not sent to anonymous liveness.
            self.assertIsNone(monitor_header)
            # Return the real production success envelope around the exact OPS-001 liveness value.
            return 200, copy.deepcopy(GREEN_HEADERS), {"ok": True, "data": {"status": "live"}}
        # Require the synthetic bearer credential for both authenticated operational probes.
        self.assertEqual(monitor_header, ("Authorization", "Bearer synthetic-monitor-value"))
        # Return sanitized MySQL readiness for the authenticated readiness path.
        if url.endswith("/readyz"):
            # Include only allowlisted state plus one permitted extra telemetry field.
            return 200, copy.deepcopy(GREEN_HEADERS), {"ok": True, "data": {"ready": True, "storage_provider": "mysql", "components": {}}}
        # Require the only remaining route to be authenticated Admin Operations.
        self.assertTrue(url.endswith("/api/v2/admin/operations"))
        # Return one sanitized Admin readiness record.
        return 200, copy.deepcopy(GREEN_HEADERS), {"ok": True, "data": {"ready": True, "components": {}}}

    # Prove the complete repository policy passes without opening a listener or client connection.
    def test_static_validation_is_network_and_process_free(self):
        # Make any attempted HTTP client call fail the test immediately.
        with mock.patch("scripts.edge_gate.urllib.request.urlopen", side_effect=AssertionError("network attempted")):
            # Make any attempted certificate socket fail the test immediately.
            with mock.patch("scripts.edge_gate.socket.create_connection", side_effect=AssertionError("socket attempted")):
                # Validate only repository text and mappings.
                policy = edge_gate.validate_policy(self.policy_path, self.root)
        # Confirm the validated packet remains explicitly unactivated.
        self.assertEqual(policy["stage"], "repository-preparation-only")

    # Prove the separate PostgreSQL preview is bound to its provider, hostname, and protected port.
    def test_postgres_preview_profile_is_statically_bound(self):
        # Select the repository-owned OCI preview policy copied into the disposable fixture.
        postgres_policy_path = self.root / "deploy" / "edge" / "postgres-preview.json"
        # Validate only inert repository content without opening a socket or process.
        policy = edge_gate.validate_policy(postgres_policy_path, self.root)
        # Require the exact profile, same-origin host, and native PostgreSQL readiness contract.
        self.assertEqual(policy["deployment_profile"], "oci-postgres-preview")
        self.assertEqual(policy["canonical_origin"], "https://preview.tiltseven.com")
        self.assertEqual(policy["monitoring"]["probes"][1]["expected_json"]["storage_provider"], "postgres")
        self.assertEqual(policy["ingress"]["protected_tcp_ports"], [5432, 8765, 8877])

    # Prove profile-owned values cannot be mixed across the two deployments.
    def test_cross_profile_origin_and_provider_are_rejected(self):
        # Load the isolated MySQL policy and substitute the PostgreSQL profile identifier only.
        policy = self.read_policy()
        policy["deployment_profile"] = "oci-postgres-preview"
        # Persist the inconsistent profile/origin combination in the disposable tree.
        self.write_policy(policy)
        # Reject the cross-profile origin before any live observation can occur.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^origin_policy$"):
            # Validate only the deliberately inconsistent static policy.
            edge_gate.validate_policy(self.policy_path, self.root)

    # Prove public signup or OAuth relaxation fails closed.
    def test_access_weakening_is_rejected(self):
        # Load one isolated policy mutation target.
        policy = self.read_policy()
        # Deliberately enable the held public signup path.
        policy["access"]["public_signup_enabled"] = True
        # Persist only the disposable unsafe fixture.
        self.write_policy(policy)
        # Require one fixed category rather than accepting the weakened boundary.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^access_policy$"):
            # Validate the deliberately unsafe isolated packet.
            edge_gate.validate_policy(self.policy_path, self.root)

    # Prove any non-loopback or port-altered upstream fails closed.
    def test_non_loopback_upstream_is_rejected(self):
        # Load one isolated policy mutation target.
        policy = self.read_policy()
        # Deliberately broaden the upstream bind address.
        policy["upstream"]["host"] = "0.0.0.0"
        # Persist only the disposable unsafe fixture.
        self.write_policy(policy)
        # Require one fixed category rather than accepting public application exposure.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^upstream_policy$"):
            # Validate the deliberately unsafe isolated packet.
            edge_gate.validate_policy(self.policy_path, self.root)

    # Prove appended client forwarding chains cannot replace the reviewed edge-owned identity.
    def test_appended_forwarding_chain_is_rejected(self):
        # Resolve the disposable nginx source.
        nginx_path = self.root / "deploy" / "nginx" / "casino.conf.template"
        # Read the isolated inert template for one security-significant mutation.
        nginx = nginx_path.read_text(encoding="utf-8")
        # Replace the edge-owned source address with the unsafe appended chain helper.
        nginx = nginx.replace("$remote_addr;", "$proxy_add_x_forwarded_for;")
        # Persist only the unsafe disposable template.
        nginx_path.write_text(nginx, encoding="utf-8")
        # Require the template-content category without leaking the changed value.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^template_content$"):
            # Validate the deliberately unsafe isolated packet.
            edge_gate.validate_policy(self.policy_path, self.root)

    # Prove template declarations cannot escape the immutable repository copy.
    def test_template_traversal_is_rejected(self):
        # Load one isolated policy mutation target.
        policy = self.read_policy()
        # Redirect one required source outside the repository-shaped root.
        policy["templates"]["nginx"] = "../outside.conf"
        # Persist only the disposable unsafe fixture.
        self.write_policy(policy)
        # Require a fixed path category without reporting the resolved host path.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^template_path$"):
            # Validate the deliberately unsafe isolated packet.
            edge_gate.validate_policy(self.policy_path, self.root)

    # Prove the monitor refuses missing credential material before any network call.
    def test_observe_requires_credential_before_network(self):
        # Validate the isolated packet using only static reads.
        policy = edge_gate.validate_policy(self.policy_path, self.root)
        # Make any attempted fetch fail the test before returning evidence.
        fetcher = mock.Mock(side_effect=AssertionError("network attempted"))
        # Require the fixed missing-credential category.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^credential_missing$"):
            # Attempt observation without inherited secret material.
            edge_gate.observe(policy, None, fetcher=fetcher, certificate_checker=mock.Mock())
        # Prove refusal happened before the first endpoint request.
        fetcher.assert_not_called()

    # Prove the preferred bearer variable wins over the legacy cookie fallback.
    def test_monitor_header_prefers_authorization(self):
        # Supply both possible root-managed credentials in one synthetic environment.
        header = edge_gate._monitor_header_from_environment({edge_gate.AUTHORIZATION_ENV: "Bearer synthetic-monitor-value", edge_gate.COOKIE_ENV: "casino_session=legacy"})
        # Require the bearer header to be selected for authenticated probes.
        self.assertEqual(header, ("Authorization", "Bearer synthetic-monitor-value"))

    # Prove old monitor-cookie environments remain compatible during rollout.
    def test_monitor_header_accepts_legacy_cookie_fallback(self):
        # Supply only the historical cookie variable used by existing hosts.
        header = edge_gate._monitor_header_from_environment({edge_gate.COOKIE_ENV: "casino_session=synthetic-monitor-value"})
        # Require the fallback to retain the exact cookie header shape.
        self.assertEqual(header, ("Cookie", "casino_session=synthetic-monitor-value"))

    # Prove only the exact standard success envelope can reach probe-field comparison.
    def test_success_envelope_fails_closed(self):
        # Require the canonical two-field success envelope to unwrap its object data.
        self.assertEqual(edge_gate.validated_success_data({"ok": True, "data": {"status": "live"}}), {"status": "live"})
        # Enumerate unwrapped, error, false-success, non-object, and ambiguous top-level shapes.
        malformed = (
            # Reject the original defect's unwrapped probe body.
            {"status": "live"},
            # Reject a standard error envelope.
            {"ok": False, "error": {"code": "UNAVAILABLE"}},
            # Reject a false result even when a data object is also present.
            {"ok": False, "data": {"status": "live"}},
            # Reject truthy non-boolean success values.
            {"ok": 1, "data": {"status": "live"}},
            # Reject a non-object data payload.
            {"ok": True, "data": ["live"]},
            # Reject additional top-level fields that could create ambiguous semantics.
            {"ok": True, "data": {"status": "live"}, "meta": {}},
        )
        # Check every malformed case under the same fixed secret-safe failure category.
        for payload in malformed:
            # Require fail-closed rejection without reflecting the supplied body.
            with self.assertRaisesRegex(edge_gate.EdgeGateError, "^endpoint_body$"):
                # Validate only the current in-memory malformed fixture.
                edge_gate.validated_success_data(payload)

    # Prove the HTTPS client refuses every redirect before authenticated headers can be copied.
    def test_redirects_are_disabled(self):
        # Construct only the standard-library redirect policy without opening a connection.
        handler = edge_gate._NoRedirect()
        # Require no follow-up request for a representative HTTPS redirect.
        redirected = handler.redirect_request(None, None, 302, "redirect", {}, "https://other.example.invalid/b")
        # Prove the handler returns no request object that could carry the monitor credential.
        self.assertIsNone(redirected)

    # Prove green observation emits only the fixed sanitized evidence schema.
    def test_observe_green_output_is_sanitized(self):
        # Validate the isolated packet before the mocked read-only observation.
        policy = edge_gate.validate_policy(self.policy_path, self.root)
        # Use one deterministic epoch and certificate lifetime for stable assertions.
        evidence = edge_gate.observe(
            # Supply only the reviewed policy mapping.
            policy,
            # Supply a synthetic bearer that never leaves the test process.
            ("Authorization", "Bearer synthetic-monitor-value"),
            # Replace network access with deterministic in-memory endpoint evidence.
            fetcher=self.green_fetcher,
            # Return a healthy whole-day certificate lifetime without a socket.
            certificate_checker=lambda host, timeout, now: 45,
            # Freeze the sanitized observation time.
            now_epoch=1784160000,
        )
        # Require the complete fixed top-level evidence key set.
        self.assertEqual(set(evidence), {"schema", "status", "observed_at", "certificate_days_remaining", "checks"})
        # Require all and only the three policy-owned probe names.
        self.assertEqual(evidence["checks"], {"liveness": True, "readiness": True, "admin_operations": True})
        # Serialize once to prove no origin, route, body, header, or cookie value is retained.
        serialized = json.dumps(evidence, sort_keys=True)
        # Reject the canonical host and synthetic secret from sanitized evidence.
        self.assertNotIn("casino.tiltseven.com", serialized)
        # Reject monitor header names and values from sanitized evidence.
        self.assertNotIn("Authorization", serialized)
        # Reject endpoint paths and response telemetry from sanitized evidence.
        self.assertNotIn("readyz", serialized)
        # Reject response header names from sanitized evidence.
        self.assertNotIn("Strict-Transport-Security", serialized)

    # Prove a near-expiry verified certificate fails closed after otherwise green probes.
    def test_certificate_age_fails_closed(self):
        # Validate the isolated packet before the mocked read-only observation.
        policy = edge_gate.validate_policy(self.policy_path, self.root)
        # Require the fixed certificate category when remaining life is below policy.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^certificate_age$"):
            # Run deterministic successful endpoint checks with one stale certificate result.
            edge_gate.observe(
                # Supply only the reviewed policy mapping.
                policy,
                # Supply a synthetic bearer that never leaves the test process.
                ("Authorization", "Bearer synthetic-monitor-value"),
                # Replace endpoint network access with green in-memory evidence.
                fetcher=self.green_fetcher,
                # Return one day less than the fourteen-day requirement.
                certificate_checker=lambda host, timeout, now: 13,
                # Freeze the clock for deterministic output suppression.
                now_epoch=1784160000,
            )

    # Prove unexpected readiness values fail closed without including response content.
    def test_readiness_mismatch_fails_closed(self):
        # Validate the isolated packet before the mocked read-only observation.
        policy = edge_gate.validate_policy(self.policy_path, self.root)

        # Return a deliberately degraded readiness value from an otherwise valid response.
        def degraded_fetcher(url, cookie, timeout, maximum_body_bytes):
            # Reuse green evidence for every route except authenticated readiness.
            if not url.endswith("/readyz"):
                # Delegate to the deterministic green fixture.
                return self.green_fetcher(url, cookie, timeout, maximum_body_bytes)
            # Return a valid success envelope with a fixed degraded value that the gate must reject.
            return 200, copy.deepcopy(GREEN_HEADERS), {"ok": True, "data": {"ready": False, "storage_provider": "mysql"}}

        # Require the fixed body category without emitting the response.
        with self.assertRaisesRegex(edge_gate.EdgeGateError, "^endpoint_body$"):
            # Run deterministic probes with the one unsafe readiness result.
            edge_gate.observe(
                # Supply only the reviewed policy mapping.
                policy,
                # Supply a synthetic bearer that never leaves the test process.
                ("Authorization", "Bearer synthetic-monitor-value"),
                # Use the one deliberately degraded response fixture.
                fetcher=degraded_fetcher,
                # Avoid a socket because readiness must fail first.
                certificate_checker=lambda host, timeout, now: 45,
                # Freeze the clock for deterministic failure behavior.
                now_epoch=1784160000,
            )


# Run focused evidence directly when a developer invokes this module.
if __name__ == "__main__":
    # Delegate reporting and process status to unittest.
    unittest.main()
