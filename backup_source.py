"""Create a timestamped backup of the B3 source tree.

The demo database, runtime logs, built frontend, Python dependencies and the
portable release bundle are intentionally excluded: this backs up source code
and documentation, which is what should be restored before/after a code change.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / "backups"

TARGETS = [
    "README.md",
    "backup_source.py",
    "start_backend.bat",
    "start_frontend.bat",
    "start_single_server.bat",
    "build_frontend.bat",
    "run_tests.bat",
    "backend/app",
    "backend/tests",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/portable_launcher.py",
    "backend/b3_portable.spec",
    "frontend/src",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "docs",
    "samples",
    "release/B3-Portable/START_B3.bat",
    "release/B3-Portable/README-PORTABLE.txt",
]

EXCLUDED_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "dist", "data", "logs", ".env",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files() -> list[Path]:
    files: set[Path] = set()
    for raw in TARGETS:
        target = ROOT / raw
        if not target.exists():
            continue
        if target.is_file():
            files.add(target)
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(ROOT).parts
            if any(part in EXCLUDED_DIRS for part in rel_parts):
                continue
            if path.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            files.add(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def main() -> int:
    label = ""
    if len(sys.argv) > 1:
        label = re.sub(r"[^0-9A-Za-z._-]+", "-", sys.argv[1]).strip("-")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"b3-source-{stamp}" + (f"-{label}" if label else "")
    BACKUP_DIR.mkdir(exist_ok=True)
    zip_path = BACKUP_DIR / f"{name}.zip"
    files = collect_files()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    zip_hash = sha256(zip_path)
    manifest_path = BACKUP_DIR / f"{name}-manifest.txt"
    lines = [
        "B3 source backup manifest",
        f"created_at: {datetime.now().isoformat(timespec='seconds')}",
        f"label: {label or '-'}",
        f"archive: {zip_path.name}",
        f"archive_sha256: {zip_hash}",
        f"file_count: {len(files)}",
        "",
        "files:",
    ]
    lines.extend(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in files)
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "BACKUP_OK",
        "archive": str(zip_path),
        "manifest": str(manifest_path),
        "file_count": len(files),
        "bytes": zip_path.stat().st_size,
        "sha256": zip_hash,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
