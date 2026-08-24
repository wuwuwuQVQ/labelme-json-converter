"""Create a clean source archive without local data or build artifacts."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "dist-release" / "Labelme-JSON-Converter-Source.zip"
ARCHIVE_ROOT = "labelme-json-converter"
EXCLUDED_PARTS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "dist-release",
    "release",
    "venv",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".json", ".jpg", ".jpeg", ".png"}


def should_include(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name == ".DS_Store" or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = OUTPUT.with_suffix(".zip.tmp")
    if temporary_output.exists():
        temporary_output.unlink()
    with zipfile.ZipFile(temporary_output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PROJECT_ROOT.rglob("*")):
            if not should_include(path):
                continue
            relative = path.relative_to(PROJECT_ROOT)
            info = zipfile.ZipInfo(str(Path(ARCHIVE_ROOT) / relative))
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = path.stat().st_mode
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())
    os.replace(temporary_output, OUTPUT)
    with zipfile.ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("源码 ZIP 完整性检查失败")
    print(f"源码包：{OUTPUT}")


if __name__ == "__main__":
    main()

