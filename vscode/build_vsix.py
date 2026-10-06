#!/usr/bin/env python3
"""Packages the VS Code extension as a .vsix without npm or vsce.

Usage:   python3 vscode/build_vsix.py
Output:  dist/session-guard-<version>.vsix
Install: code --install-extension dist/session-guard-<version>.vsix

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LANGUAGES = ["de", "fr", "it", "es"]
FILES = (["package.json", "package.nls.json", "extension.js", "logic.js"]
         + ["package.nls.%s.json" % l for l in LANGUAGES] + ["l10n/bundle.l10n.%s.json" % l for l in LANGUAGES])
FROM_ROOT = {"README.md": "README.md", "LICENSE": "LICENSE.txt", "CHANGELOG.md": "CHANGELOG.md", "docs/icon.png": "icon.png"}
# Shown on the Marketplace page, outside the repository: relative links there are dead.
MARKDOWN = {"README.md", "CHANGELOG.md"}

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension=".json" ContentType="application/json"/>
<Default Extension=".js" ContentType="application/javascript"/>
<Default Extension=".md" ContentType="text/markdown"/>
<Default Extension=".txt" ContentType="text/plain"/>
<Default Extension=".png" ContentType="image/png"/>
<Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""


def manifest(pkg, nls):
    resolve = lambda value: nls.get(value.strip("%"), value) if value.startswith("%") else value
    return """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}" />
    <DisplayName>{display}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
    <Tags>{tags}</Tags>
    <Categories>{categories}</Categories>
    <License>extension/LICENSE.txt</License>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{engine}" />
      <Property Id="Microsoft.VisualStudio.Services.Links.Source" Value="{repo}" />
      <Property Id="Microsoft.VisualStudio.Services.Links.GitHub" Value="{repo}" />
      <Property Id="Microsoft.VisualStudio.Services.Links.Support" Value="{bugs}" />
      <Property Id="Microsoft.VisualStudio.Services.Links.Learn" Value="{homepage}" />
      <Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
    </Properties>
    <Icon>extension/{icon}</Icon>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Changelog" Path="extension/CHANGELOG.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE.txt" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/{icon}" Addressable="true" />
  </Assets>
</PackageManifest>
""".format(name=escape(pkg["name"]), version=escape(pkg["version"]), publisher=escape(pkg["publisher"]),
           display=escape(resolve(pkg["displayName"])), description=escape(resolve(pkg["description"])),
           tags=escape(",".join(pkg.get("keywords", []))), categories=escape(",".join(pkg.get("categories", []))),
           engine=escape(pkg["engines"]["vscode"]), repo=escape(pkg["repository"]["url"]),
           bugs=escape(pkg["bugs"]["url"]), homepage=escape(pkg["homepage"]), icon=escape(pkg["icon"]))


def absolute_links(text, repo):
    """Points relative Markdown and HTML links at the repository, like vsce does:
    images at raw/HEAD, everything else at blob/HEAD. Anchors, mailto and full URLs stay."""
    def target(link, image):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#)", link, re.I):
            return link
        return "%s/%s/HEAD/%s" % (repo, "raw" if image else "blob", link.lstrip("./"))
    text = re.sub(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)",
                  lambda m: "%s[%s](%s)" % (m.group(1), m.group(2), target(m.group(3), bool(m.group(1)))), text)
    return re.sub(r'(<(img|a)\b[^>]*?\b(?:src|href)=")([^"]+)"',
                  lambda m: '%s%s"' % (m.group(1), target(m.group(3), m.group(2) == "img")), text)


def build(out_dir):
    with open(os.path.join(HERE, "package.json"), encoding="utf-8") as f:
        pkg = json.load(f)
    with open(os.path.join(HERE, "package.nls.json"), encoding="utf-8") as f:
        nls = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "%s-%s.vsix" % (pkg["name"], pkg["version"]))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("extension.vsixmanifest", manifest(pkg, nls))
        for name in FILES:
            z.write(os.path.join(HERE, name), "extension/" + name)
        for source, name in FROM_ROOT.items():
            if name in MARKDOWN:
                with open(os.path.join(ROOT, source), encoding="utf-8") as f:
                    z.writestr("extension/" + name, absolute_links(f.read(), pkg["repository"]["url"]))
            else:
                z.write(os.path.join(ROOT, source), "extension/" + name)
    return target


def main():
    print(build(os.path.join(ROOT, "dist")))


if __name__ == "__main__":
    sys.exit(main())
