"""Listener-free TiltSeven repository-scaffold acceptance. (MARKETING-001..003, TEST-107)"""

# Import the standard HTML parser for dependency-free structure inspection.
from html.parser import HTMLParser
# Import JSON parsing for module, requirement, and visual-matrix assertions.
import json
# Import regular expressions for static policy and accidental-live-detail checks.
import re
# Import the standard unittest framework used by focused repository suites.
import unittest
# Import portable paths so every checked artifact is rooted in this checkout.
from pathlib import Path
# Import URL parsing so local assets and the one reviewed Casino destination stay distinct.
from urllib.parse import urlparse

# Resolve the repository root independently from the caller's working directory.
ROOT = Path(__file__).resolve().parents[1]
# Name the repository-only site root once for all artifact checks.
SITE_ROOT = ROOT / "site" / "tiltseven"
# Pin the separate governed Casino destination without activating it.
CASINO_DESTINATION = "https://casino.tiltseven.com/"
# Define the exact locale documents required by the visual matrix.
LOCALE_DOCUMENTS = {"en-US": SITE_ROOT / "index.html", "ru-RU": SITE_ROOT / "ru" / "index.html"}
# Define safety phrases that must remain human-readable in each checked locale.
SAFETY_PHRASES = {
    "en-US": ("play tokens", "no cash value", "No deposits.", "No withdrawals."),
    "ru-RU": ("игровыми жетонами", "Без денежной ценности", "Без пополнений.", "Без вывода."),
}


# Collect the semantic and resource facts needed by the static policy tests.
class MarketingHtmlParser(HTMLParser):
    # Initialize one empty fact inventory before parsing a locale document.
    def __init__(self) -> None:
        # Initialize the standard parser with character references decoded.
        super().__init__(convert_charrefs=True)
        # Record every start tag and normalized attribute mapping.
        self.tags = []
        # Record text by the currently open tag for accessible-name checks.
        self.text = []

    # Capture each opening tag and its attributes in document order.
    def handle_starttag(self, tag, attrs) -> None:
        # Store a dictionary so exact attribute checks stay readable.
        self.tags.append((tag, dict(attrs)))

    # Capture non-empty decoded text without relying on a browser.
    def handle_data(self, data) -> None:
        # Normalize whitespace so prose checks are stable across formatting changes.
        value = " ".join(data.split())
        # Preserve only meaningful visible text.
        if value:
            # Append the normalized text fragment to the document inventory.
            self.text.append(value)


# Parse one checked locale document into a reusable fact inventory.
def parse_document(path: Path) -> MarketingHtmlParser:
    # Create a fresh parser so locale facts never leak into each other.
    parser = MarketingHtmlParser()
    # Parse exact UTF-8 source bytes through the standard decoder.
    parser.feed(path.read_text(encoding="utf-8"))
    # Return the completed inventory.
    return parser


# Verify the static scaffold stays local, bilingual, safe, accessible, and undeployed.
class MarketingSiteTests(unittest.TestCase):
    # Require one complete semantic document per governed locale.
    def test_locale_documents_have_semantic_landmarks(self) -> None:
        # Inspect English and Russian independently.
        for locale, path in LOCALE_DOCUMENTS.items():
            # Label failures with the affected locale.
            with self.subTest(locale=locale):
                # Read the exact authored document.
                source = path.read_text(encoding="utf-8")
                # Parse semantic tags without launching a listener or browser.
                parsed = parse_document(path)
                # Build a compact tag inventory for cardinality checks.
                names = [tag for tag, _attrs in parsed.tags]
                # Require a declared locale and exactly one header, main, and footer.
                html_rows = [attrs for tag, attrs in parsed.tags if tag == "html"]
                # Verify the document language and landmark cardinality.
                self.assertEqual(([row.get("lang") for row in html_rows], names.count("header"), names.count("main"), names.count("footer")), ([locale.split("-")[0]], 1, 1, 1))
                # Require one stable browser-evidence selector on the main landmark.
                main_rows = [attrs for tag, attrs in parsed.tags if tag == "main"]
                # Verify exact evidence identity and keyboard focusability.
                self.assertEqual((main_rows[0].get("data-testid"), main_rows[0].get("tabindex")), ("marketing-site", "-1"))
                # Require title, description, one H1, navigation, and skip navigation.
                self.assertIn("<title>", source)
                # Require one human-readable meta description.
                self.assertRegex(source, r'<meta name="description" content="[^"]{40,}">')
                # Require one top-level heading and at least one navigation landmark.
                self.assertEqual(names.count("h1"), 1)
                # Require both primary navigation and the keyboard skip link.
                self.assertTrue("nav" in names and 'class="skip-link"' in source and 'href="#main-content"' in source)
                # Reject replacement characters and unresolved template placeholders.
                self.assertNotRegex(source, r"\uFFFD|\{\{[^}]+\}\}")
                # Reject any complete visible text fragment that is only a dotted resource key.
                self.assertFalse(any(re.fullmatch(r"[a-z]+(?:\.[a-z0-9_-]+){2,}", value) for value in parsed.text))

    # Require both locale variants to preserve the fake-money safety boundary.
    def test_safety_copy_and_destination_are_exact(self) -> None:
        # Inspect the complete source for each locale.
        for locale, path in LOCALE_DOCUMENTS.items():
            # Label failures with the affected locale.
            with self.subTest(locale=locale):
                # Read the localized document.
                source = path.read_text(encoding="utf-8")
                # Require every locale-owned safety phrase.
                self.assertTrue(all(phrase in source for phrase in SAFETY_PHRASES[locale]))
                # Require the separate Casino destination and no other absolute hyperlink.
                parsed = parse_document(path)
                # Collect every hyperlink target.
                hrefs = [attrs["href"] for tag, attrs in parsed.tags if tag == "a" and "href" in attrs]
                # Isolate absolute network destinations.
                absolute = {href for href in hrefs if urlparse(href).scheme in {"http", "https"}}
                # Permit only the reviewed canonical Casino origin.
                self.assertEqual(absolute, {CASINO_DESTINATION})
                # Reject payment controls, forms, trackers, and executable content.
                forbidden_tags = {tag for tag, _attrs in parsed.tags} & {"script", "iframe", "form", "input", "button", "video", "audio"}
                # Require a purely static, non-collecting page.
                self.assertEqual(forbidden_tags, set())

    # Require every runtime resource to be local and present in the repository.
    def test_resources_are_local_and_present(self) -> None:
        # Check each locale from its own directory so relative-path resolution is exact.
        for locale, path in LOCALE_DOCUMENTS.items():
            # Label failures with the affected locale.
            with self.subTest(locale=locale):
                # Parse the resource-bearing tags.
                parsed = parse_document(path)
                # Collect stylesheet and image references.
                resources = [attrs.get("href") for tag, attrs in parsed.tags if tag == "link" and attrs.get("rel") in {"icon", "stylesheet"}]
                # Include every image source.
                resources += [attrs.get("src") for tag, attrs in parsed.tags if tag == "img"]
                # Require at least the stylesheet, icon, and visible brand mark.
                self.assertGreaterEqual(len(resources), 3)
                # Validate every resource independently.
                for resource in resources:
                    # Label failures with the exact authored reference.
                    with self.subTest(resource=resource):
                        # Reject network, protocol-relative, data, and root-absolute resources.
                        self.assertFalse(urlparse(resource).scheme or resource.startswith(("//", "/")))
                        # Resolve the local reference and require a real checked file.
                        target = (path.parent / resource).resolve()
                        # Prevent traversal outside the owned static-site module.
                        self.assertTrue(target.is_relative_to(SITE_ROOT.resolve()))
                        # Require every referenced local asset to exist.
                        self.assertTrue(target.is_file())

    # Require the authored CSS to satisfy keyboard, responsive, and reduced-motion policy.
    def test_css_owns_accessibility_and_responsive_rules(self) -> None:
        # Read the one shared stylesheet used by both locale documents.
        css = (SITE_ROOT / "styles.css").read_text(encoding="utf-8")
        # Require visible focus, a keyboard skip link, and the 44-pixel-equivalent control floor.
        self.assertTrue(all(anchor in css for anchor in ("a:focus-visible", ".skip-link:focus", "min-height: 2.75rem", "outline: 3px solid")))
        # Require reduced-motion and both responsive transition points.
        self.assertTrue(all(anchor in css for anchor in ("prefers-reduced-motion: reduce", "@media (max-width: 980px)", "@media (max-width: 640px)")))
        # Keep enough mobile preview height and lower-panel separation for the decorative chip to remain unobscured.
        self.assertRegex(css, r"@media \(max-width: 640px\)[\s\S]*?\.hero-card\s*\{\s*min-height:\s*44rem;\s*\}[\s\S]*?\.felt-panel\s*\{\s*bottom:\s*20%;\s*\}")
        # Reject horizontal page scrolling and remote CSS resources.
        self.assertTrue("overflow-x: hidden" in css and not re.search(r"url\(\s*['\"]?https?://", css, re.IGNORECASE))

    # Require the brand SVG to retain a text alternative without external dependencies.
    def test_brand_mark_is_accessible_and_local(self) -> None:
        # Read the checked vector source.
        svg = (SITE_ROOT / "assets" / "tiltseven-mark.svg").read_text(encoding="utf-8")
        # Require an image role linked to a title and description.
        self.assertTrue('role="img"' in svg and 'aria-labelledby="title desc"' in svg and "<title " in svg and "<desc " in svg)
        # Reject executable or remotely loaded SVG content while permitting the standard SVG namespace.
        self.assertNotRegex(svg, r"<script|xlink:href|(?:href|src)=[\"']https?://")

    # Require the future-publication document to stay explicitly non-operative.
    def test_publication_runbook_is_owner_gated(self) -> None:
        # Read the repository-only planning document.
        runbook = (SITE_ROOT / "deployment.md").read_text(encoding="utf-8")
        # Require the explicit no-authorization and separate-packet boundaries.
        self.assertTrue("No publication is authorized" in runbook and "owner must approve an exact publication" in runbook)
        # Reject copied provider endpoints, IP addresses, credentials, or live completion claims.
        self.assertNotRegex(runbook, r"\b(?:\d{1,3}\.){3}\d{1,3}\b|CNAME|MX\s+\d+|password|secret|terminal green")

    # Require one module owner and exact visual-matrix coverage.
    def test_module_and_visual_ownership_are_complete(self) -> None:
        # Load the canonical aggregate module manifest.
        manifest = json.loads((ROOT / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
        # Load the dedicated site-module descriptor.
        module = json.loads((ROOT / "modules" / "marketing_site.json").read_text(encoding="utf-8"))
        # Require exact aggregate, descriptor, path, and prefix ownership.
        self.assertEqual((manifest["modules"]["marketing_site"], module["module"], module["version"], module["paths"], module["requirements_prefixes"]), ("1.0.2", "marketing_site", "1.0.2", ["site/tiltseven/"], ["MARKETING"]))
        # Load the executable visual inventory.
        matrix = json.loads((ROOT / "tests" / "visual" / "visual_matrix.json").read_text(encoding="utf-8"))
        # Isolate the marketing row.
        rows = [row for row in matrix["surfaces"] if row["id"] == "marketing_site"]
        # Require exactly one complete row.
        self.assertEqual(len(rows), 1)
        # Read the governed row.
        row = rows[0]
        # Require both locale documents, every viewport, and all accepted states.
        self.assertEqual((row["locales"], row["viewports"], set(row["states"])), (["en-US", "ru-RU"], ["desktop_primary", "desktop_compact", "tablet", "mobile"], {"landing", "keyboard_focus", "reduced_motion"}))


# Run the focused suite directly when requested by a developer.
if __name__ == "__main__":
    # Exit through unittest's normal result and status behavior.
    unittest.main()
