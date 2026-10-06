"""Tests for vscode/build_vsix.py. Run: python3 -m unittest discover -s tests/python

Builds the .vsix into a temporary directory and checks what the Marketplace and Open VSX
need: an icon, the repository links, and README/CHANGELOG without relative links (the
Marketplace shows them outside the repository, where relative paths are dead).
"""
import importlib.util
import json
import os
import re
import tempfile
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPEC = importlib.util.spec_from_file_location("build_vsix", os.path.join(ROOT, "vscode", "build_vsix.py"))
build_vsix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_vsix)

REPO = "https://github.com/simon-says-labs/session-guard"


class BuildVsixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.path = build_vsix.build(cls._tmp.name)
        cls.zip = zipfile.ZipFile(cls.path)
        cls.manifest = cls.zip.read("extension.vsixmanifest").decode("utf-8")
        cls.package = json.loads(cls.zip.read("extension/package.json"))

    @classmethod
    def tearDownClass(cls):
        cls.zip.close()
        cls._tmp.cleanup()

    def test_icon_is_packaged_and_declared(self):
        icon = "extension/" + self.package["icon"]
        self.assertIn(icon, self.zip.namelist())
        self.assertTrue(self.zip.read(icon).startswith(b"\x89PNG"), "icon must be a PNG, not an SVG")
        self.assertIn("<Icon>%s</Icon>" % icon, self.manifest)
        self.assertIn('Type="Microsoft.VisualStudio.Services.Icons.Default" Path="%s"' % icon, self.manifest)
        self.assertIn('Extension=".png"', self.zip.read("[Content_Types].xml").decode("utf-8"))

    def test_links_for_the_marketplace_page(self):
        for prop in ("Links.Source", "Links.GitHub", "Links.Support", "Links.Learn", "GitHubFlavoredMarkdown"):
            self.assertIn("Microsoft.VisualStudio.Services.%s" % prop, self.manifest)

    def test_readme_and_changelog_have_no_relative_links(self):
        for name in ("extension/README.md", "extension/CHANGELOG.md"):
            text = self.zip.read(name).decode("utf-8")
            targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'(?:src|href)="([^"]+)"', text)
            relative = [t for t in targets if not re.match(r"^(https?://|mailto:|#)", t)]
            self.assertEqual(relative, [], name)

    def test_readme_images_point_to_raw_files_in_the_repository(self):
        text = self.zip.read("extension/README.md").decode("utf-8")
        self.assertIn("](%s/raw/HEAD/docs/screenshot.png)" % REPO, text)
        self.assertIn('href="%s/blob/HEAD/docs/README.fr.md"' % REPO, text)
        self.assertIn('href="#english"', text, "anchors on the same page stay as they are")

    def test_readme_in_the_repository_is_unchanged(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            self.assertIn("](docs/screenshot.png)", f.read())


class RewriteTest(unittest.TestCase):
    def test_rewrite_rules(self):
        text = ('![a](docs/x.png) [b](CONTRIBUTING.md) [c](https://example.org) [d](#top) '
                '<img src="docs/y.png"> <a href="docs/z.md">z</a> [e](mailto:a@b.c)')
        out = build_vsix.absolute_links(text, REPO)
        self.assertEqual(out, (
            "![a](%(r)s/raw/HEAD/docs/x.png) [b](%(r)s/blob/HEAD/CONTRIBUTING.md) [c](https://example.org) "
            '[d](#top) <img src="%(r)s/raw/HEAD/docs/y.png"> <a href="%(r)s/blob/HEAD/docs/z.md">z</a> '
            "[e](mailto:a@b.c)") % {"r": REPO})


if __name__ == "__main__":
    unittest.main()
