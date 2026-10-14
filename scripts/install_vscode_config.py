"""Apply the shared lightweight settings and remove blocked Linux extensions."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def read_settings(path):
    if not path.exists():
        return {}
    # VS Code accepts JSON comments and trailing commas; preserve quoted strings.
    tokens = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    content = re.sub(tokens, lambda m: m[0] if m[0].startswith('"') else " ",
                     path.read_text())
    content = re.sub(r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])',
                     lambda m: "" if m[0].startswith(",") else m[0], content)
    settings = json.loads(content) if content.strip() else {}
    if not isinstance(settings, dict):
        raise ValueError(f"Expected a settings object in {path}")
    return settings


def merge_settings(path, managed):
    settings = read_settings(path)
    for key, value in managed.items():
        existing = settings.get(key, {})
        settings[key] = {**(existing if isinstance(existing, dict) else {}), **value}
        if key == "extensions.allowed" and isinstance(existing, dict) and "*" in existing:
            settings[key]["*"] = existing["*"]
    content = json.dumps(settings, indent=2) + "\n"
    if path.exists() and path.read_text() == content:
        print(f"  VS Code settings unchanged: {path}", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
        temporary = Path(out.name)
        try:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
            if path.exists():
                shutil.copymode(path, temporary)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"  Installed VS Code settings: {path}", flush=True)


def remove_blocked(cli, blocked):
    installed = subprocess.check_output(
        [str(cli), "--list-extensions"], text=True, timeout=60
    ).splitlines()
    for extension in installed:
        if extension.lower() in blocked:
            # Uninstalling Python can also remove its dependent extensions.
            current = subprocess.check_output(
                [str(cli), "--list-extensions"], text=True, timeout=60
            ).lower().splitlines()
            if extension.lower() not in current:
                continue
            subprocess.run([str(cli), "--uninstall-extension", extension],
                           check=True, timeout=60)


def install_html_watch(cli, source):
    package = json.loads((source / "package.json").read_text())
    identifier = f"{package['publisher']}.{package['name']}"
    with tempfile.TemporaryDirectory(prefix="octo-html-watch-") as directory:
        archive = Path(directory) / f"{identifier}.vsix"
        with ZipFile(archive, "w") as bundle:
            bundle.writestr("extension.vsixmanifest", f'''<?xml version="1.0"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{identifier}" Version="{package['version']}" Publisher="{package['publisher']}"/>
    <DisplayName>{package['displayName']}</DisplayName>
    <Description xml:space="preserve">{package['description']}</Description>
    <Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="{package['engines']['vscode']}"/></Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
  <Dependencies/>
  <Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>''')
            bundle.writestr("[Content_Types].xml", '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="js" ContentType="application/javascript"/>
  <Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>''')
            for name in ["package.json", "extension.js"]:
                bundle.write(source / name, f"extension/{name}")
        subprocess.run([str(cli), "--install-extension", str(archive), "--force"],
                       check=True, timeout=60)


def main():
    if not sys.platform.startswith("linux"):
        print("  Skipped Linux VS Code configuration")
        return
    managed = json.loads(Path(sys.argv[1]).read_text())
    html_watch = Path(sys.argv[1]).resolve().parent / "html-preview-watch"
    home = Path.home()
    merge_settings(Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
                   / "Code/User/settings.json", managed)
    server = Path(os.environ.get("VSCODE_AGENT_FOLDER", home / ".vscode-server"))
    merge_settings(server / "data/Machine/settings.json", managed)
    # The server CLI reads its User settings; the running server reads Machine.
    merge_settings(server / "data/User/settings.json", managed)
    blocked = {key.lower() for key, value in managed["extensions.allowed"].items()
               if value is False}
    desktop_cli = shutil.which("code")
    if desktop_cli:
        remove_blocked(desktop_cli, blocked)
        install_html_watch(desktop_cli, html_watch)
    # Use the newest installed official server, including the older bin layout.
    candidates = []
    for cli in [*server.glob("cli/servers/Stable-*/server/bin/code-server"),
                *server.glob("bin/*/bin/code-server")]:
        product = json.loads((cli.parent.parent / "product.json").read_text())
        version = tuple(int(part) for part in product["version"].split("-", 1)[0].split("."))
        candidates.append((version, str(cli)))
    if candidates:
        remove_blocked(max(candidates)[1], blocked)
        install_html_watch(max(candidates)[1], html_watch)
    elif (server / "extensions/extensions.json").exists():
        raise RuntimeError("Remote extensions exist but no official server CLI was found")
    else:
        print("  No VS Code server installed; remote settings prepared")


if __name__ == "__main__":
    main()
