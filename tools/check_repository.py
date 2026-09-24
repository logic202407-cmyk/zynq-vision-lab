#!/usr/bin/env python3
"""Check repository foundations without claiming simulation or board verification.

Uses only Python's standard library. It does not fetch data, run HDL tools,
inspect credentials outside this repository, or change project files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    'README.md', 'LICENSE', 'THIRD_PARTY.md', 'AGENTS.md', 'CONTRIBUTING.md',
    '.gitignore', '.github/workflows/repository-checks.yml',
    'docs/project_plan.md', 'docs/first_week_tasks.md', 'docs/compliance.md',
    'docs/sources.md', 'docs/reproduction.md', 'docs/safety.md',
    'board/hardware_inventory.md', 'build/toolchain_manifest.md',
    'src/rtl/README.md', 'src/hls/README.md', 'src/ps/README.md',
    'sim/README.md', 'data/test_manifest.md', 'report/status.json',
    'report/submission_checklist.md', 'skill/evidence-gates/SKILL.md',
)
EXCLUDED_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache'}
# Check the public project itself; these explicitly private/generated paths are
# ignored by Git and must not be added with `git add -f`.
EXCLUDED_PREFIXES = ('private/', 'data/raw/', 'board/photos/private/', 'build/generated/')
STATUSES = ('planned', 'implemented', 'simulated', 'implemented_on_device', 'board_verified', 'reproduced')
SECRET_PATTERNS = (
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
)
LINK_PATTERN = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
FORBIDDEN_SUFFIXES = {'.lic', '.pem', '.key', '.bit', '.dcp', '.xsa', '.wdb'}
BINARY_SUFFIXES = {'.png', '.jpg', '.jpeg', '.pdf', '.gif'}


def safe_relative_path(value: object) -> bool:
    """Allow ASCII project-relative paths without traversal or backslashes."""
    if not isinstance(value, str) or not value or not re.fullmatch(r'[A-Za-z0-9._/-]+', value):
        return False
    parts = value.split('/')
    return all(part not in ('', '.', '..') for part in parts)


def contains_secret(text: str) -> bool:
    """A deliberately limited high-confidence scan, not a security guarantee."""
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def markdown_link_errors(root: Path, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for target in LINK_PATTERN.findall(text):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        candidate = (path.parent / unquote(parsed.path)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f'{path.relative_to(root)}: link escapes repository')
            continue
        if not candidate.exists():
            errors.append(f'{path.relative_to(root)}: missing local link {target}')
    return errors


def status_errors(root: Path, data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        return ['report/status.json: expected schema_version 1']
    components = data.get('components')
    if not isinstance(components, list) or not components:
        return ['report/status.json: components must be a non-empty list']
    seen: set[str] = set()
    for item in components:
        if not isinstance(item, dict):
            errors.append('report/status.json: component must be an object')
            continue
        identifier = item.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', identifier):
            errors.append('report/status.json: invalid component id')
            continue
        if identifier in seen:
            errors.append(f'{identifier}: duplicate component id')
        seen.add(identifier)
        stage = item.get('status')
        if stage not in STATUSES:
            errors.append(f'{identifier}: unknown status')
        evidence = item.get('evidence')
        if not isinstance(evidence, list):
            errors.append(f'{identifier}: evidence must be a list')
            continue
        if stage != 'planned' and not evidence:
            errors.append(f'{identifier}: non-planned claims require evidence paths')
        for value in evidence:
            if not safe_relative_path(value):
                errors.append(f'{identifier}: invalid evidence path')
                continue
            candidate = root / value
            if not candidate.is_file() or candidate.is_symlink():
                errors.append(f'{identifier}: evidence file missing or symlink: {value}')
                continue
            if not candidate.resolve().is_relative_to(root.resolve()):
                errors.append(f'{identifier}: evidence escapes repository')
        if stage in STATUSES[2:]:
            if not re.fullmatch(r'[0-9a-f]{40}', str(item.get('verified_commit', ''))):
                errors.append(f'{identifier}: verified stages require a full source commit SHA')
            if not item.get('tool_version') or not item.get('reviewer'):
                errors.append(f'{identifier}: verified stages require tool_version and reviewer')
    return errors


def check_repository(root: Path) -> list[str]:
    """Return issues. Passing does not prove the contents of evidence files."""
    root = root.resolve()
    errors: list[str] = []
    if not root.is_dir():
        return ['repository directory does not exist']
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f'missing required file: {name}')
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if relative.startswith(EXCLUDED_PREFIXES):
            continue
        if not safe_relative_path(relative):
            errors.append(f'non-ASCII or unsafe path: {relative}')
        if path.is_symlink():
            errors.append(f'symlinks are not allowed in the public scaffold: {relative}')
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or (path.name.startswith('.env') and path.name != '.env.example'):
            errors.append(f'private/generated file is not permitted in public source: {relative}')
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f'file exceeds the current 5 MiB public-source review limit: {relative}')
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue  # Images still require human privacy/license review.
        try:
            text = path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            errors.append(f'not readable UTF-8 source: {relative}')
            continue
        if contains_secret(text):
            errors.append(f'possible credential in {relative}; matched value is not printed')
        if path.suffix == '.md':
            errors.extend(markdown_link_errors(root, path, text))
    try:
        ledger = json.loads((root / 'report/status.json').read_text(encoding='utf-8'))
        errors.extend(status_errors(root, ledger))
    except (OSError, ValueError) as exc:
        errors.append(f'report/status.json: unreadable or invalid JSON ({type(exc).__name__})')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check_repository(args.root)
    if errors:
        for issue in errors:
            print(f'ERROR: {issue}', file=sys.stderr)
        return 1
    print('PASS: repository foundations, local links, and claim-ledger checks.')
    print('Not verified: FPGA simulation, synthesis/implementation, board behavior, performance, or all private data.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
