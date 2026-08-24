"""Labelme JSON conversion and batch-processing logic."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple


TARGET_VERSION = "6.3.0"

STATUS_CONVERTED = "converted"
STATUS_COMPATIBLE = "compatible"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"


class LabelmeValidationError(ValueError):
    """Raised when a JSON document is not a supported Labelme document."""


@dataclass(frozen=True)
class FileResult:
    source: Path
    destination: Path
    status: str
    message: str
    input_bytes: int = 0
    output_bytes: int = 0


@dataclass
class BatchSummary:
    input_path: Path
    output_directory: Path
    results: List[FileResult] = field(default_factory=list)
    report_path: Optional[Path] = None

    @property
    def total(self) -> int:
        return len(self.results)

    def count(self, status: str) -> int:
        return sum(result.status == status for result in self.results)

    @property
    def converted(self) -> int:
        return self.count(STATUS_CONVERTED)

    @property
    def compatible(self) -> int:
        return self.count(STATUS_COMPATIBLE)

    @property
    def skipped(self) -> int:
        return self.count(STATUS_SKIPPED)

    @property
    def failed(self) -> int:
        return self.count(STATUS_FAILED)

    @property
    def input_bytes(self) -> int:
        return sum(result.input_bytes for result in self.results)

    @property
    def output_bytes(self) -> int:
        return sum(result.output_bytes for result in self.results)


ProgressCallback = Callable[[int, int, FileResult], None]
TotalCallback = Callable[[int], None]


def portable_image_basename(image_path: str) -> str:
    """Return the filename from either a Windows or POSIX image path."""
    if not isinstance(image_path, str) or not image_path.strip():
        raise LabelmeValidationError("imagePath 必须是非空字符串")

    normalized = image_path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1]
    if filename in {"", ".", ".."}:
        raise LabelmeValidationError("imagePath 中没有有效的图片文件名")
    return filename


def convert_document(document: Mapping[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Convert one decoded document without mutating it.

    Returns ``(converted_document, was_already_compatible)``. Only ``version``,
    ``imageData`` and ``imagePath`` may change.
    """
    if not isinstance(document, Mapping):
        raise LabelmeValidationError("JSON 顶层必须是对象")
    if not isinstance(document.get("shapes"), list):
        raise LabelmeValidationError("缺少 Labelme shapes 数组")
    if "imagePath" not in document:
        raise LabelmeValidationError("缺少 Labelme imagePath 字段")

    filename = portable_image_basename(document["imagePath"])
    was_compatible = (
        document.get("version") == TARGET_VERSION
        and document.get("imageData") is None
        and document.get("imagePath") == filename
    )

    converted = dict(document)
    converted["version"] = TARGET_VERSION
    converted["imageData"] = None
    converted["imagePath"] = filename
    return converted, was_compatible


def discover_json_files(input_path: Path, output_directory: Path) -> List[Path]:
    """Find JSON files and exclude an output subtree under the input."""
    source = input_path.expanduser().resolve()
    output = output_directory.expanduser().resolve()

    if not source.exists():
        raise FileNotFoundError(f"输入路径不存在：{source}")
    if source.is_file():
        if source.suffix.lower() != ".json":
            raise ValueError("单文件模式只能选择 .json 文件")
        return [source]
    if not source.is_dir():
        raise ValueError(f"输入路径不是普通文件或目录：{source}")

    files = []
    for candidate in source.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() != ".json":
            continue
        resolved_candidate = candidate.resolve()
        if _is_relative_to(resolved_candidate, output):
            continue
        files.append(resolved_candidate)
    return sorted(files, key=lambda path: str(path).casefold())


def convert_path(
    input_path: Path,
    output_directory: Path,
    progress_callback: Optional[ProgressCallback] = None,
    total_callback: Optional[TotalCallback] = None,
) -> BatchSummary:
    """Convert one JSON file or a directory tree and write a text report."""
    source = input_path.expanduser().resolve()
    output = output_directory.expanduser().resolve()
    files = discover_json_files(source, output)
    if total_callback is not None:
        total_callback(len(files))

    output.mkdir(parents=True, exist_ok=True)
    summary = BatchSummary(input_path=source, output_directory=output)

    for index, json_file in enumerate(files, start=1):
        destination = (
            output / json_file.name
            if source.is_file()
            else output / json_file.relative_to(source)
        )
        result = _convert_file(json_file, destination)
        summary.results.append(result)
        if progress_callback is not None:
            progress_callback(index, len(files), result)

    summary.report_path = write_report(summary)
    return summary


def write_report(summary: BatchSummary) -> Path:
    """Write a timestamped UTF-8 conversion report."""
    generated_at = datetime.now()
    report_path = summary.output_directory / generated_at.strftime(
        "conversion_report_%Y%m%d_%H%M%S_%f.txt"
    )
    status_labels = {
        STATUS_CONVERTED: "成功转换",
        STATUS_COMPATIBLE: "已兼容",
        STATUS_SKIPPED: "跳过",
        STATUS_FAILED: "失败",
    }
    lines = [
        "Labelme JSON -> 6.3.0 转换报告",
        f"生成时间：{generated_at.astimezone().isoformat(timespec='seconds')}",
        f"输入路径：{summary.input_path}",
        f"输出目录：{summary.output_directory}",
        "",
        f"文件总数：{summary.total}",
        f"成功转换：{summary.converted}",
        f"已兼容：{summary.compatible}",
        f"跳过：{summary.skipped}",
        f"失败：{summary.failed}",
        f"输入总大小：{format_bytes(summary.input_bytes)} ({summary.input_bytes} bytes)",
        f"新写入总大小：{format_bytes(summary.output_bytes)} ({summary.output_bytes} bytes)",
        "",
        "文件明细：",
    ]
    for result in summary.results:
        lines.append(
            f"[{status_labels.get(result.status, result.status)}] "
            f"{result.source} -> {result.destination} | "
            f"{result.input_bytes} -> {result.output_bytes} bytes | {result.message}"
        )

    _atomic_write(report_path, ("\n".join(lines) + "\n").encode("utf-8"))
    return report_path


def format_bytes(size: int) -> str:
    value = float(size)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{size} B"


def _convert_file(source: Path, destination: Path) -> FileResult:
    input_bytes = 0
    try:
        input_bytes = source.stat().st_size
        if destination.exists():
            return FileResult(
                source,
                destination,
                STATUS_SKIPPED,
                "输出文件已存在，未覆盖",
                input_bytes,
            )

        with source.open("r", encoding="utf-8-sig") as handle:
            document = json.load(handle)
        converted, was_compatible = convert_document(document)
        encoded = (json.dumps(converted, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        _atomic_write(destination, encoded)
        return FileResult(
            source,
            destination,
            STATUS_COMPATIBLE if was_compatible else STATUS_CONVERTED,
            "原文件已符合目标格式，已复制" if was_compatible else "转换完成",
            input_bytes,
            len(encoded),
        )
    except Exception as exc:  # One bad file must not abort a batch.
        return FileResult(
            source,
            destination,
            STATUS_FAILED,
            f"{type(exc).__name__}: {exc}",
            input_bytes,
        )


def _atomic_write(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"输出文件已存在：{destination}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            raise FileExistsError(f"输出文件已存在：{destination}")
        os.replace(str(temporary_path), str(destination))
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False

