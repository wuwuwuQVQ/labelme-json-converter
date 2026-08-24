"""Tkinter desktop interface for Labelme JSON Converter."""

from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Optional, Protocol, Sequence, Tuple

from . import __version__
from .converter import BatchSummary, FileResult, convert_path, format_bytes


class DialogService(Protocol):
    def choose_json_file(self) -> str:
        ...

    def choose_directory(self, title: str, must_exist: bool = True) -> str:
        ...


class NotificationService(Protocol):
    def warning(self, title: str, message: str) -> None:
        ...

    def error(self, title: str, message: str) -> None:
        ...

    def info(self, title: str, message: str) -> None:
        ...


class TkDialogService:
    def choose_json_file(self) -> str:
        return filedialog.askopenfilename(
            title="选择旧版 Labelme JSON",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*")],
        )

    def choose_directory(self, title: str, must_exist: bool = True) -> str:
        return filedialog.askdirectory(title=title, mustexist=must_exist)


class TkNotificationService:
    def warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)


class ConverterApp:
    def __init__(
        self,
        root: tk.Tk,
        dialogs: Optional[DialogService] = None,
        notifications: Optional[NotificationService] = None,
    ) -> None:
        self.root = root
        self.dialogs = dialogs or TkDialogService()
        self.notifications = notifications or TkNotificationService()
        self.events: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.running = False
        self.closed = False
        self._poll_after_id: Optional[str] = None

        root.title(f"Labelme JSON 转换工具 {__version__}")
        root.minsize(760, 560)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.mode = tk.StringVar(value="file")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.progress_text = tk.StringVar(value="请选择输入和输出目录")
        self.progress_value = tk.DoubleVar(value=0)

        self._build_ui()
        self._schedule_poll()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(7, weight=1)

        ttk.Label(
            container,
            text="Labelme JSON 转换工具",
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(
            container,
            text="转换为 Labelme 6.3.0 无内嵌图像格式，完整保留标注信息。",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 18))

        mode_frame = ttk.LabelFrame(container, text="输入类型", padding=10)
        mode_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.file_radio = ttk.Radiobutton(
            mode_frame,
            text="单个 JSON 文件",
            variable=self.mode,
            value="file",
            command=self._mode_changed,
        )
        self.file_radio.pack(side="left", padx=(0, 20))
        self.directory_radio = ttk.Radiobutton(
            mode_frame,
            text="文件夹（递归处理）",
            variable=self.mode,
            value="directory",
            command=self._mode_changed,
        )
        self.directory_radio.pack(side="left")

        ttk.Label(container, text="输入路径：").grid(row=3, column=0, sticky="w", pady=6)
        self.input_entry = ttk.Entry(container, textvariable=self.input_path)
        self.input_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        self.input_button = ttk.Button(container, text="选择…", command=self._choose_input)
        self.input_button.grid(row=3, column=2, pady=6)

        ttk.Label(container, text="输出目录：").grid(row=4, column=0, sticky="w", pady=6)
        self.output_entry = ttk.Entry(container, textvariable=self.output_path)
        self.output_entry.grid(row=4, column=1, sticky="ew", padx=8, pady=6)
        self.output_button = ttk.Button(container, text="选择…", command=self._choose_output)
        self.output_button.grid(row=4, column=2, pady=6)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(14, 8))
        action_frame.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(
            action_frame,
            variable=self.progress_value,
            maximum=100,
            mode="determinate",
        )
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.start_button = ttk.Button(action_frame, text="开始转换", command=self._start)
        self.start_button.grid(row=0, column=1)

        ttk.Label(container, textvariable=self.progress_text).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        self.log = ScrolledText(container, height=14, wrap="word", state="disabled")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew")
        self._append_log("转换规则：version=6.3.0，imageData=null，imagePath 仅保留文件名。\n")

    @property
    def interactive_widgets(self) -> Tuple[ttk.Widget, ...]:
        return (
            self.file_radio,
            self.directory_radio,
            self.input_entry,
            self.input_button,
            self.output_entry,
            self.output_button,
            self.start_button,
        )

    def _mode_changed(self) -> None:
        self.input_path.set("")
        self.progress_text.set("请选择输入和输出目录")

    def _choose_input(self) -> None:
        if self.mode.get() == "file":
            selected = self.dialogs.choose_json_file()
        else:
            selected = self.dialogs.choose_directory("选择包含 Labelme JSON 的文件夹")
        if selected:
            self.input_path.set(selected)
            if not self.output_path.get():
                source = Path(selected)
                self.output_path.set(str(source.parent / f"{source.stem}_labelme_6.3.0"))

    def _choose_output(self) -> None:
        selected = self.dialogs.choose_directory("选择输出目录", must_exist=False)
        if selected:
            self.output_path.set(selected)

    def _start(self) -> None:
        if self.running:
            return
        source_text = self.input_path.get().strip()
        output_text = self.output_path.get().strip()
        if not source_text or not output_text:
            self.notifications.warning("缺少路径", "请先选择输入路径和输出目录。")
            return

        source = Path(source_text).expanduser()
        output = Path(output_text).expanduser()
        if not source.exists():
            self.notifications.error("输入错误", f"输入路径不存在：\n{source}")
            return
        if self.mode.get() == "file" and not source.is_file():
            self.notifications.error("输入错误", "当前是单文件模式，请选择一个 JSON 文件。")
            return
        if self.mode.get() == "directory" and not source.is_dir():
            self.notifications.error("输入错误", "当前是文件夹模式，请选择一个目录。")
            return

        self.running = True
        self.progress_value.set(0)
        self.progress_text.set("正在扫描 JSON 文件…")
        self._set_controls_enabled(False)
        self._append_log(f"\n输入：{source}\n输出：{output}\n")
        threading.Thread(
            target=self._run_conversion,
            args=(source, output),
            daemon=True,
        ).start()

    def _run_conversion(self, source: Path, output: Path) -> None:
        try:
            summary = convert_path(
                source,
                output,
                progress_callback=lambda done, total, result: self.events.put(
                    ("progress", (done, total, result))
                ),
                total_callback=lambda total: self.events.put(("total", total)),
            )
            self.events.put(("complete", summary))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def process_pending_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "total":
                    self.progress_text.set(f"发现 {int(payload)} 个 JSON 文件")
                elif event == "progress":
                    done, total, result = payload
                    self.progress_value.set((done / total * 100) if total else 100)
                    self.progress_text.set(f"正在处理 {done}/{total}：{result.source.name}")
                    self._append_result(result)
                elif event == "complete":
                    self._finish(payload)
                elif event == "error":
                    self._fail(str(payload))
        except queue.Empty:
            return

    def _schedule_poll(self) -> None:
        if not self.closed:
            self._poll_after_id = self.root.after(100, self._poll_events)

    def _poll_events(self) -> None:
        self._poll_after_id = None
        self.process_pending_events()
        self._schedule_poll()

    def _append_result(self, result: FileResult) -> None:
        labels = {
            "converted": "成功",
            "compatible": "已兼容",
            "skipped": "跳过",
            "failed": "失败",
        }
        self._append_log(
            f"[{labels.get(result.status, result.status)}] {result.source} — {result.message}\n"
        )

    def _finish(self, summary: BatchSummary) -> None:
        self.running = False
        self.progress_value.set(100)
        self._set_controls_enabled(True)
        text = (
            f"处理完成：共 {summary.total} 个，成功 {summary.converted} 个，"
            f"已兼容 {summary.compatible} 个，跳过 {summary.skipped} 个，"
            f"失败 {summary.failed} 个。\n"
            f"输入大小：{format_bytes(summary.input_bytes)}；"
            f"新写入大小：{format_bytes(summary.output_bytes)}。\n"
            f"报告：{summary.report_path}"
        )
        self.progress_text.set(text.replace("\n", "  "))
        self._append_log(text + "\n")
        self.notifications.info("转换完成", text)

    def _fail(self, message: str) -> None:
        self.running = False
        self._set_controls_enabled(True)
        self.progress_text.set("转换未完成")
        self._append_log(f"[错误] {message}\n")
        self.notifications.error("转换失败", message)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in self.interactive_widgets:
            widget.configure(state=state)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self) -> None:
        self.closed = True
        if self._poll_after_id is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Labelme JSON Converter")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ui-smoke-test", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_argument_parser().parse_args(argv)
    if args.self_test:
        from .diagnostics import run_core_self_test

        raise SystemExit(run_core_self_test())
    if args.ui_smoke_test:
        from .diagnostics import run_ui_smoke_test

        raise SystemExit(run_ui_smoke_test())

    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

