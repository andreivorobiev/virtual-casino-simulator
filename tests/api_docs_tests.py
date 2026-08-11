# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free complete Swagger contract inventory for API-003 and TEST-152."""

# Import portable paths for source-bound inventory checks.
import pathlib
# Import regular expressions for the static Swagger URL inventory.
import re
# Import unittest assertions without opening a listener.
import unittest

# Resolve the exact checkout root from this test module.
ROOT = pathlib.Path(__file__).resolve().parents[1]


# Verify the same-origin Swagger explorer remains complete, read-only, and packaged.
class ApiDocsTests(unittest.TestCase):
    # Require one selector entry for every governed OpenAPI contract and no invented entry.
    def test_swagger_inventory_matches_all_contracts(self):
        # Read the reviewed Swagger initialization source.
        source = (ROOT / "web" / "api-docs.js").read_text(encoding="utf-8")
        # Extract only exact reviewed YAML filenames from the static source inventory.
        documented = sorted(re.findall(r"'([^']+\.yaml)'", source))
        # Enumerate every governed source contract on disk.
        governed = sorted(path.name for path in (ROOT / "contracts" / "openapi").glob("*.yaml"))
        # Require complete one-to-one inventory parity.
        self.assertEqual(documented, governed)
        # Keep the restricted-preview explorer descriptive rather than mutation-capable.
        self.assertIn("supportedSubmitMethods: []", source)
        # Disable the external validator so contract bytes never leave the owned origin.
        self.assertIn("validatorUrl: null", source)
        # Keep Swagger's official multi-contract Topbar preset bound to the selector inventory.
        self.assertIn("presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset]", source)
        # Require the official selector plugin rather than a parallel custom contract picker.
        self.assertIn("plugins: [SwaggerUIBundle.plugins.DownloadUrl]", source)
        # Render the preset's layout so the selector loads the primary contract immediately.
        self.assertIn("layout: 'StandaloneLayout'", source)
        # Bind initial loading to the first reviewed contract rather than an empty Swagger state.
        self.assertIn("'urls.primaryName': contracts[0].name", source)
        # Supply the complete reviewed selector entries to Swagger's multi-definition configuration.
        self.assertIn("urls: contracts", source)
        # Keep the complete 62-contract catalog collapsed until a reader chooses an operation.
        self.assertIn("docExpansion: 'none'", source)
        # Preserve schema visibility without expanding every model across the large catalog.
        self.assertIn("defaultModelsExpandDepth: 1", source)

    # Require pinned same-origin Swagger assets and retained upstream licensing.
    def test_swagger_assets_are_pinned_and_local(self):
        # Resolve the exact vendored distribution directory.
        vendor = ROOT / "web" / "vendor" / "swagger-ui"
        # Require a substantial official bundle rather than a placeholder shim.
        self.assertGreater((vendor / "swagger-ui-bundle.js").stat().st_size, 1_000_000)
        # Require the official standalone preset that owns the multi-contract Topbar selector.
        self.assertGreater((vendor / "swagger-ui-standalone-preset.js").stat().st_size, 100_000)
        # Require the complete official stylesheet used by the same-origin page.
        self.assertGreater((vendor / "swagger-ui.css").stat().st_size, 100_000)
        # Preserve the Apache license beside the copied upstream assets.
        self.assertIn("Apache License", (vendor / "LICENSE").read_text(encoding="utf-8"))
        # Prove the HTML imports no remote executable or stylesheet.
        html = (ROOT / "web" / "api-docs.html").read_text(encoding="utf-8")
        # Prove the preset is loaded before the application initializes the selector.
        self.assertLess(html.index("swagger-ui-standalone-preset.js"), html.index("api-docs.js"))
        # Refuse CDN or protocol-relative resource references under the owned CSP.
        self.assertNotRegex(html, r"(?:https?:)?//(?:unpkg|cdn|jsdelivr)")

    # Require both supported HTTP adapters to expose traversal-safe contract bytes.
    def test_http_adapters_publish_same_origin_contracts(self):
        # Read both server implementations without importing production runtime state.
        app_source = (ROOT / "casino" / "app.py").read_text(encoding="utf-8")
        # Read the production adapter independently so one route cannot drift.
        wsgi_source = (ROOT / "casino" / "wsgi.py").read_text(encoding="utf-8")
        # Require both stable docs aliases and the dedicated immutable contract root.
        for source in (app_source, wsgi_source):
            # Prove the human-facing URL maps to the dedicated Swagger entry file.
            self.assertIn('("/api-docs", "/api-docs/")', source)
            # Prove the contract namespace selects the dedicated OpenAPI directory.
            self.assertIn('path.startswith("/openapi/")', source)
            # Prove YAML receives an explicit Swagger-compatible media type.
            self.assertIn('"application/yaml; charset=utf-8"', source)


# Run the focused suite directly when invoked outside the central API runner.
if __name__ == "__main__":
    # Use standard unittest discovery output for local diagnosis.
    unittest.main()
