#!/usr/bin/env python3
"""Packages the VS Code extension as a .vsix without npm or vsce.

Usage:   python3 vscode/build_vsix.py
Output:  dist/claude-waechter-<version>.vsix
Install: code --install-extension dist/claude-waechter-<version>.vsix

Copyright (c) 2026 Simon Eckmiller. MIT License.
"""
import json
import os
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = ["package.json", "package.nls.json", "package.nls.de.json", "extension.js", "logic.js",
         "l10n/bundle.l10n.de.json"]
FROM_ROOT = {"README.md": "README.md", "LICENSE": "LICENSE.txt", "CHANGELOG.md": "CHANGELOG.md"}

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension=".json" ContentType="application/json"/>
<Default Extension=".js" ContentType="application/javascript"/>
<Default Extension=".md" ContentType="text/markdown"/>
<Default Extension=".txt" ContentType="text/plain"/>
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
    </Properties>
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
  </Assets>
</PackageManifest>
""".format(name=escape(pkg["name"]), version=escape(pkg["version"]), publisher=escape(pkg["publisher"]),
           display=escape(resolve(pkg["displayName"])), description=escape(resolve(pkg["description"])),
           tags=escape(",".join(pkg.get("keywords", []))), categories=escape(",".join(pkg.get("categories", []))),
           engine=escape(pkg["engines"]["vscode"]), repo=escape(pkg["repository"]["url"]))


def main():
    with open(os.path.join(HERE, "package.json"), encoding="utf-8") as f:
        pkg = json.load(f)
    with open(os.path.join(HERE, "package.nls.json"), encoding="utf-8") as f:
        nls = json.load(f)
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "%s-%s.vsix" % (pkg["name"], pkg["version"]))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("extension.vsixmanifest", manifest(pkg, nls))
        for name in FILES:
            z.write(os.path.join(HERE, name), "extension/" + name)
        for source, name in FROM_ROOT.items():
            z.write(os.path.join(ROOT, source), "extension/" + name)
    print(target)


if __name__ == "__main__":
    sys.exit(main())
