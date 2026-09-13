#!/usr/bin/env python3
"""Render managed defaults while preserving this host's project and hook trust."""

import json
from pathlib import Path
import sys

try:
    import tomllib
except ImportError:
    # Python <3.11 needs tomli; pip also ships it on supported older Pythons.
    try:
        import tomli as tomllib
    except ImportError:
        try:
            from pip._vendor import tomli as tomllib
        except ImportError as error:
            raise SystemExit("Codex config rendering needs Python 3.11+, tomli, or pip with tomli.") from error


def toml_value(value):
    if isinstance(value, (str, bool, int)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    raise ValueError("Unsupported local trust value: " + type(value).__name__)


def render_table(path, table):
    lines = ["[" + ".".join(json.dumps(key, ensure_ascii=False) for key in path) + "]"]
    for key, value in table.items():
        if not isinstance(value, dict):
            lines.append(json.dumps(key, ensure_ascii=False) + " = " + toml_value(value))
    for key, value in table.items():
        if isinstance(value, dict):
            lines.extend(["", *render_table([*path, key], value)])
    return lines


def render_config(managed, installed):
    source = tomllib.loads(managed)
    local = tomllib.loads(installed)
    if "projects" in source or "state" in source.get("hooks", {}):
        raise ValueError("Managed defaults must not contain machine-local trust")
    lines = [managed.rstrip()]
    for path, table in [
        (["projects"], local.get("projects", {})),
        (["hooks", "state"], local.get("hooks", {}).get("state", {})),
    ]:
        if not isinstance(table, dict):
            raise ValueError("Local trust must be a table: " + ".".join(path))
        if table:
            lines.extend(["", *render_table(path, table)])
    rendered = "\n".join(lines) + "\n"
    tomllib.loads(rendered)
    return rendered


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render_codex_config.py MANAGED INSTALLED")
    source, installed = map(Path, sys.argv[1:])
    try:
        print(render_config(source.read_text(), installed.read_text() if installed.exists() else ""), end="")
    except (OSError, ValueError) as error:
        raise SystemExit("Could not render Codex config: " + str(error)) from error


if __name__ == "__main__":
    main()
