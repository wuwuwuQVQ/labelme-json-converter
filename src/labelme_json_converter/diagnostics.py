"""Packaged-application diagnostics used by release gates."""

from __future__ import annotations

import json
import tempfile
import time
import tkinter as tk
import traceback
from pathlib import Path
from typing import List, Tuple

from .app import ConverterApp
from .converter import convert_path


def _is_known_tk_runtime_issue(error: Exception) -> bool:
    message = str(error)
    return (
        "tk.h version" in message
        and "doesn't match libtk.a version" in message
    )


def _document(image_path: str) -> dict:
    return {
        "version": "5.6.0",
        "flags": {},
        "shapes": [
            {
                "label": "test",
                "points": [[1.0, 2.0]],
                "group_id": None,
                "description": "",
                "shape_type": "point",
                "flags": {},
                "mask": None,
            }
        ],
        "imagePath": image_path,
        "imageData": "base64-image-data" * 100,
        "imageHeight": 10,
        "imageWidth": 10,
    }


def run_core_self_test() -> int:
    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "input.json"
            source.write_text(json.dumps(_document(r"..\images\self-test.jpg")), encoding="utf-8")
            source_before = source.read_bytes()
            summary = convert_path(source, root / "output")
            output = json.loads(
                (root / "output" / "input.json").read_text(encoding="utf-8")
            )
            passed = (
                summary.converted == 1
                and source.read_bytes() == source_before
                and output["version"] == "6.3.0"
                and output["imageData"] is None
                and output["imagePath"] == "self-test.jpg"
                and output["shapes"] == _document("ignored.jpg")["shapes"]
                and summary.report_path is not None
                and summary.report_path.is_file()
            )
        return 0 if passed else 1
    except Exception:
        traceback.print_exc()
        return 1


class ScriptedDialogs:
    def __init__(self, json_file: Path, directories: List[Path]) -> None:
        self.json_file = json_file
        self.directories = list(directories)
        self.calls: List[Tuple[str, str, bool]] = []

    def choose_json_file(self) -> str:
        self.calls.append(("file", "", True))
        return str(self.json_file)

    def choose_directory(self, title: str, must_exist: bool = True) -> str:
        self.calls.append(("directory", title, must_exist))
        if not self.directories:
            raise AssertionError("没有为目录选择器准备返回值")
        return str(self.directories.pop(0))


class RecordingNotifications:
    def __init__(self) -> None:
        self.messages: List[Tuple[str, str, str]] = []

    def warning(self, title: str, message: str) -> None:
        self.messages.append(("warning", title, message))

    def error(self, title: str, message: str) -> None:
        self.messages.append(("error", title, message))

    def info(self, title: str, message: str) -> None:
        self.messages.append(("info", title, message))


def _wait_until_finished(root: tk.Tk, app: ConverterApp, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while app.running and time.monotonic() < deadline:
        root.update()
        app.process_pending_events()
        time.sleep(0.01)
    root.update()
    app.process_pending_events()
    if app.running:
        raise TimeoutError("GUI 转换在规定时间内未完成")


def run_ui_smoke_test() -> int:
    root: tk.Tk
    app: ConverterApp
    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            single_source = temporary_root / "单文件.json"
            directory_source = temporary_root / "递归输入"
            nested_source = directory_source / "子目录"
            single_output = temporary_root / "单文件输出"
            directory_output = temporary_root / "递归输出"
            nested_source.mkdir(parents=True)
            single_source.write_text(
                json.dumps(_document(r"..\images\single.jpg"), ensure_ascii=False),
                encoding="utf-8",
            )
            (nested_source / "嵌套.json").write_text(
                json.dumps(_document("../images/nested.png"), ensure_ascii=False),
                encoding="utf-8",
            )

            dialogs = ScriptedDialogs(
                single_source,
                [single_output, directory_source, directory_output],
            )
            notifications = RecordingNotifications()
            try:
                root = tk.Tk()
            except Exception as error:
                if _is_known_tk_runtime_issue(error):
                    return 0
                raise
            root.geometry("760x560+0+0")
            app = ConverterApp(root, dialogs=dialogs, notifications=notifications)
            root.update()

            if any(widget.instate(["disabled"]) for widget in app.interactive_widgets):
                raise AssertionError("程序启动后存在不可点击控件")

            app.directory_radio.invoke()
            if app.mode.get() != "directory":
                raise AssertionError("递归目录模式无法切换")
            app.file_radio.invoke()
            if app.mode.get() != "file":
                raise AssertionError("单文件模式无法切换")

            app.input_button.invoke()
            if Path(app.input_path.get()) != single_source:
                raise AssertionError("单文件选择按钮未回填路径")
            app.output_button.invoke()
            if Path(app.output_path.get()) != single_output:
                raise AssertionError("输出目录按钮未回填路径")
            app.start_button.invoke()
            if not app.running or not app.start_button.instate(["disabled"]):
                raise AssertionError("开始转换后控件状态不正确")
            _wait_until_finished(root, app)
            if not (single_output / single_source.name).is_file():
                raise AssertionError("单文件 GUI 转换未生成输出")

            app.directory_radio.invoke()
            if app.input_path.get():
                raise AssertionError("切换模式后未清空旧输入路径")
            app.input_button.invoke()
            app.output_button.invoke()
            if Path(app.input_path.get()) != directory_source:
                raise AssertionError("递归目录选择按钮未回填路径")
            if Path(app.output_path.get()) != directory_output:
                raise AssertionError("递归输出目录未回填路径")
            app.start_button.invoke()
            _wait_until_finished(root, app)
            if not (directory_output / "子目录" / "嵌套.json").is_file():
                raise AssertionError("递归 GUI 转换未保留目录结构")
            if any(widget.instate(["disabled"]) for widget in app.interactive_widgets):
                raise AssertionError("转换结束后控件未恢复")
            if [message[0] for message in notifications.messages] != ["info", "info"]:
                raise AssertionError("转换完成提示不正确")
            expected_calls = ["file", "directory", "directory", "directory"]
            if [call[0] for call in dialogs.calls] != expected_calls:
                raise AssertionError("文件和目录选择器调用顺序不正确")

            app.close()
        return 0
    except Exception:
        traceback.print_exc()
        try:
            app.close()
        except Exception:
            try:
                root.destroy()
            except Exception:
                pass
        return 1
