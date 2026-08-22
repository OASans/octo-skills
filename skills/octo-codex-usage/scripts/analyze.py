#!/usr/bin/env python3
"""Aggregate unusual shell usage from recent local Codex session records."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

COMMAND_TYPES = {b"CommandExecution", b"command_execution"}
IMPORT_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([^\n;]+))"
)
SAFE_EXECUTABLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.+-]{0,63}$")
HEREDOC_PATTERN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

ORDINARY_EXECUTABLES = set(
    """
    [ apply_patch awk bash basename biome black bun cargo cat cd chmod clang clear
    cksum cmake
    column comm command cmp cp cut date declare deno df diff dirname docker dotnet du
    echo env eslint exit file find flake8 gh git go gradle grep gunzip gzip head id
    install isort java jest
    javac jq kill kubectl ln local ls make mkdir mktemp mv mvn mypy ninja nl node npm
    npx patch pkill pnpm popd prettier printf pushd pwd pyright pylint pytest python
    python3 read readlink realpath return rg rm rmdir ruff rustc sed set sh sha1sum
    sha256sum shellcheck sleep sort source stat strings stylelint swift tail tar tee
    test time timeout touch tr true tsc ulimit uname uniq unlink unzip uv vitest wc
    which whoami
    xargs xcodebuild yarn yes zip zsh
    """.split()
)
SHELL_KEYWORDS = {
    "case",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "fi",
    "for",
    "function",
    "if",
    "in",
    "then",
    "until",
    "while",
}
RUN_WRAPPERS = {"pipenv", "poetry", "uv"}
SUDO_OPTIONS_WITH_VALUES = {
    "-C", "-D", "-R", "-T", "-g", "-h", "-p", "-u",
    "--chdir", "--close-from", "--group", "--host", "--prompt", "--root",
    "--user",
}
TIMEOUT_OPTIONS_WITH_VALUES = {"-k", "-s", "--kill-after", "--signal"}
ENV_OPTIONS_WITH_VALUES = {"-C", "-S", "-u", "--chdir", "--split-string", "--unset"}


@dataclass(frozen=True)
class Candidate:
    kind: str
    label: str


@dataclass
class CandidateStats:
    runs: int = 0
    failures: int = 0
    sessions: set[str] = field(default_factory=set)


@dataclass
class Report:
    files: int = 0
    sessions: set[str] = field(default_factory=set)
    executions: int = 0
    ordinary_executions: int = 0
    malformed_lines: int = 0
    candidates: dict[Candidate, CandidateStats] = field(default_factory=dict)


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def command_text(item: dict[str, object]) -> str | None:
    command = item.get("command")
    if isinstance(command, str):
        return command
    if isinstance(command, list):
        strings = [part for part in command if isinstance(part, str)]
        return strings[-1] if strings else None
    return None


def inline_purpose(language: str, command: str) -> str:
    if not language.startswith("python"):
        return "ad hoc transformation"

    modules: set[str] = set()
    for match in IMPORT_PATTERN.finditer(command):
        if match.group(1):
            modules.add(match.group(1).split(".")[0].lower())
        if match.group(2):
            for name in match.group(2).split(","):
                parts = name.strip().split()
                if parts:
                    modules.add(parts[0].split(".")[0].lower())

    categories = (
        ({"sqlite3"}, "SQLite inspection"),
        ({"json", "orjson"}, "JSON transformation"),
        ({"csv", "pandas", "polars"}, "tabular-data transformation"),
        ({"toml", "tomllib"}, "TOML transformation"),
        ({"yaml"}, "YAML transformation"),
        ({"xml", "lxml"}, "XML transformation"),
        ({"ast"}, "Python source analysis"),
        ({"zipfile", "tarfile"}, "archive processing"),
        ({"pil", "cv2"}, "image processing"),
        ({"subprocess"}, "process orchestration"),
        ({"pathlib", "glob", "shutil"}, "filesystem batch processing"),
        ({"re"}, "regex text processing"),
    )
    for expected_modules, purpose in categories:
        if modules & expected_modules:
            return purpose
    lowered_command = command.lower()
    if "\n" not in command and re.search(r"\bprint\s*\(", lowered_command):
        return "one-line calculation or formatting"
    return "ad hoc computation"


def normalized_language(raw_language: str) -> str:
    lowered = raw_language.lower()
    if lowered.startswith("python"):
        return "Python"
    return lowered.capitalize()


def shell_segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(
        strip_heredoc_bodies(command), posix=True, punctuation_chars=";|&\n"
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in {"\n", ";", ";;", "&", "&&", "|", "||"}:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def discard_options(tokens: list[str], options_with_values: set[str]) -> None:
    while tokens and tokens[0].startswith("-"):
        option = tokens.pop(0)
        if option == "--":
            return
        option_name = option.split("=", 1)[0]
        if "=" not in option and option_name in options_with_values and tokens:
            tokens.pop(0)


def unwrap_command(tokens: list[str]) -> list[str]:
    while tokens:
        wrapper = Path(tokens[0]).name
        if wrapper == "sudo":
            tokens.pop(0)
            discard_options(tokens, SUDO_OPTIONS_WITH_VALUES)
        elif wrapper == "timeout":
            tokens.pop(0)
            discard_options(tokens, TIMEOUT_OPTIONS_WITH_VALUES)
            if tokens:
                tokens.pop(0)
        elif wrapper == "env":
            tokens.pop(0)
            discard_options(tokens, ENV_OPTIONS_WITH_VALUES)
            while tokens and "=" in tokens[0]:
                tokens.pop(0)
        elif wrapper in {"command", "nohup"}:
            tokens.pop(0)
            discard_options(tokens, set())
        else:
            break
    return tokens


def command_tokens(tokens: list[str]) -> list[str]:
    tokens = list(tokens)
    if tokens and (
        tokens[0] in {"case", "for", "function", "if", "until", "while"}
        or tokens[0].endswith("()")
    ):
        return []
    while tokens and (tokens[0] in SHELL_KEYWORDS or "=" in tokens[0]):
        tokens.pop(0)
    tokens = unwrap_command(tokens)
    if tokens and Path(tokens[0]).name in RUN_WRAPPERS:
        try:
            run_index = tokens.index("run")
        except ValueError:
            return tokens
        tokens = tokens[run_index + 1 :]
    return tokens


def inline_language(command: str) -> str | None:
    for segment in shell_segments(command):
        tokens = command_tokens(segment)
        if len(tokens) < 2:
            continue
        executable = Path(tokens[0]).name.lower()
        if re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable):
            modes = tokens[1:4]
            if any(mode == "-" or re.fullmatch(r"-[A-Za-z]*c", mode) for mode in modes):
                return "Python"
        if executable in {"node", "ruby", "perl"} and any(
            mode == "-e" for mode in tokens[1:4]
        ):
            return normalized_language(executable)
        if executable == "php" and any(mode == "-r" for mode in tokens[1:4]):
            return "Php"
    return None


def command_heads(command: str) -> set[str]:
    heads: set[str] = set()
    segments = shell_segments(command)
    declared_functions = {
        tokens[0][:-2]
        for tokens in segments
        if tokens and tokens[0].endswith("()")
    }
    for segment in segments:
        tokens = command_tokens(segment)
        if not tokens:
            continue
        raw_head = tokens[0]
        head = Path(raw_head).name
        if head in declared_functions:
            continue
        if raw_head.startswith(("./", "../")) or "/ai_tools/" in raw_head:
            continue
        if head.endswith((".py", ".sh", ".rb", ".js")):
            continue
        if SAFE_EXECUTABLE_PATTERN.fullmatch(head):
            heads.add(head.lower())
    return heads


def strip_heredoc_bodies(command: str) -> str:
    kept_lines: list[str] = []
    delimiter: str | None = None
    for line in command.splitlines():
        if delimiter is not None:
            if line.lstrip("\t").strip() == delimiter:
                delimiter = None
            continue
        kept_lines.append(line)
        match = HEREDOC_PATTERN.search(line)
        if match:
            delimiter = match.group(2)
    return "\n".join(kept_lines)


def classify_command(command: str, ignored: set[str]) -> set[Candidate]:
    candidates: set[Candidate] = set()
    language = inline_language(command)
    if language:
        purpose = inline_purpose(language.lower(), command)
        candidates.add(Candidate("inline", f"inline {language}: {purpose}"))
        return candidates

    for executable in command_heads(command):
        if executable not in ORDINARY_EXECUTABLES and executable not in ignored:
            candidates.add(
                Candidate("executable", f"unusual executable: {executable}")
            )
    return candidates


def command_failed(item: dict[str, object]) -> bool:
    if str(item.get("status", "")).lower() == "failed":
        return True
    exit_code = item.get("exit_code")
    return isinstance(exit_code, int) and exit_code != 0


def analyze_file(
    path: Path,
    cutoff: datetime,
    ignored: set[str],
    report: Report,
) -> None:
    session = path.stem
    with path.open("rb") as transcript:
        for raw_line in transcript:
            if not any(marker in raw_line for marker in COMMAND_TYPES):
                continue
            try:
                record = json.loads(raw_line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                report.malformed_lines += 1
                continue
            timestamp = parse_timestamp(record.get("timestamp"))
            if timestamp is None or timestamp < cutoff:
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict) or payload.get("type") != "item_completed":
                continue
            item = payload.get("item")
            if not isinstance(item, dict):
                continue
            item_type = re.sub(r"[^a-z]", "", str(item.get("type", "")).lower())
            if item_type != "commandexecution":
                continue
            command = command_text(item)
            if command is None:
                continue

            report.sessions.add(session)
            report.executions += 1
            candidates = classify_command(command, ignored)
            if not candidates:
                report.ordinary_executions += 1
                continue
            failed = command_failed(item)
            for candidate in candidates:
                stats = report.candidates.setdefault(candidate, CandidateStats())
                stats.runs += 1
                stats.sessions.add(session)
                stats.failures += int(failed)


def discover_transcripts(codex_home: Path, cutoff: datetime) -> list[Path]:
    transcripts: list[Path] = []
    for directory_name in ("sessions", "archived_sessions"):
        directory = codex_home / directory_name
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.jsonl"):
            try:
                if path.stat().st_mtime >= cutoff.timestamp():
                    transcripts.append(path)
            except OSError as error:
                raise RuntimeError(f"cannot inspect {path}: {error}") from error
    return sorted(transcripts)


def analyze(
    codex_home: Path,
    days: int,
    ignored: set[str],
    now: datetime | None = None,
) -> Report:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=days)
    paths = discover_transcripts(codex_home, cutoff)
    if not paths:
        raise RuntimeError(f"no recent Codex transcripts found under {codex_home}")

    report = Report(files=len(paths))
    for path in paths:
        try:
            analyze_file(path, cutoff, ignored, report)
        except OSError as error:
            raise RuntimeError(f"cannot read {path}: {error}") from error
    return report


def render_report(report: Report, days: int, min_count: int, limit: int) -> str:
    ranked = [
        (candidate, stats)
        for candidate, stats in report.candidates.items()
        if stats.runs >= min_count
    ]
    ranked.sort(key=lambda entry: (-len(entry[1].sessions), -entry[1].runs, entry[0].label))

    lines = [
        f"Unusual Codex usage — last {days} days",
        (
            f"Scope: {len(report.sessions)} sessions, {report.executions} shell executions; "
            f"{report.ordinary_executions} ordinary executions suppressed."
        ),
    ]
    if report.malformed_lines:
        lines.append(f"Skipped {report.malformed_lines} incomplete session lines.")
    if not ranked:
        lines.append(f"No unusual pattern repeated at least {min_count} times.")
        return "\n".join(lines)

    lines.append("Repeated unusual patterns:")
    for candidate, stats in ranked[:limit]:
        failure_text = f", {stats.failures} failed" if stats.failures else ""
        lines.append(
            f"- {candidate.label} — {stats.runs} runs across "
            f"{len(stats.sessions)} sessions{failure_text}"
        )
    if len(ranked) > limit:
        lines.append(f"- {len(ranked) - limit} more patterns omitted")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    default_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser = argparse.ArgumentParser(
        description="Report repeated unusual commands without exposing transcript text."
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--codex-home", type=Path, default=default_home)
    parser.add_argument("--ignore", action="append", default=[], metavar="EXECUTABLE")
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.days <= 0 or args.min_count <= 0 or args.limit <= 0:
        parser.error("--days, --min-count, and --limit must be positive")
    return args


def main() -> int:
    args = parse_args()
    ignored = {Path(value).name.lower() for value in args.ignore}
    try:
        report = analyze(args.codex_home.expanduser(), args.days, ignored)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 1
    print(render_report(report, args.days, args.min_count, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
