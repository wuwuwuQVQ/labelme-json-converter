# Labelme JSON Converter

[![CI](https://github.com/wuwuwuQVQ/labelme-json-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/wuwuwuQVQ/labelme-json-converter/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/wuwuwuQVQ/labelme-json-converter)](https://github.com/wuwuwuQVQ/labelme-json-converter/releases)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

将旧版或仍包含 Base64 图像数据的 Labelme JSON 转换为 Labelme 6.3.0 无内嵌图片格式。提供单文件和递归目录图形界面，完整保留标注内容，绝不覆盖源文件。

> **English summary:** A cross-platform desktop utility that removes embedded Base64 image data from Labelme JSON files, normalizes them to the Labelme 6.3.0 format, and preserves all annotations. Portable builds are provided for Windows, macOS, and Linux.

## 转换规则

- `version` 设置为 `6.3.0`。
- `imageData` 字段保留，值设置为 `null`。
- `imagePath` 只保留图片文件名，同时识别 Windows `\` 和 POSIX `/` 路径。
- `shapes`、坐标、标签、尺寸、flags 和未知扩展字段原样保留。
- 输出使用 UTF-8 和两空格缩进；原文件不会被修改或覆盖。

转换后的 JSON 不再包含图片。需要在 Labelme 中重新打开时，请把对应原图放在转换后 JSON 的同一目录。

## 下载

从 [Releases](https://github.com/wuwuwuQVQ/labelme-json-converter/releases/latest) 下载与电脑匹配的 ZIP：

| 系统 | 下载文件 | 支持范围 |
|---|---|---|
| Windows | `Labelme-JSON-Converter-Windows-x86_64.zip` | Windows 10/11 64 位 |
| Apple Silicon Mac | `Labelme-JSON-Converter-macOS-arm64.zip` | M1/M2/M3/M4，macOS 12+ |
| Intel Mac | `Labelme-JSON-Converter-macOS-x86_64.zip` | Intel，macOS 12+ |
| Linux | `Labelme-JSON-Converter-Linux-x86_64.zip` | Ubuntu 22.04+/glibc 2.35+ |

这些成品已包含 Python 和 Tkinter，接收方不需要安装 Python。可使用同一 Release 中的 `SHA256SUMS.txt` 检查下载完整性。

## 使用方法

1. 解压对应系统的 ZIP 并启动程序。
2. 选择“单个 JSON 文件”或“文件夹（递归处理）”。
3. 点击输入路径旁的“选择…”并选择文件或目录。
4. 点击输出目录旁的“选择…”。
5. 点击“开始转换”。
6. 查看界面摘要和输出目录中的 `conversion_report_*.txt`。

已有输出文件会被跳过，某个损坏 JSON 不会中断其他文件的转换。

### 首次启动提示

- **Windows：** 内部测试版没有商业代码签名。如 SmartScreen 拦截，请确认文件来自本仓库 Release，再选择“更多信息”→“仍要运行”。
- **macOS：** 应用没有 Apple 开发者公证。首次启动可在 Finder 中按住 Control 点击应用，选择“打开”。
- **Linux：** 如程序没有执行权限，运行 `chmod +x labelme-json-converter`；需要桌面图形环境。

## 从源码运行

需要 Python 3.9+ 且包含 Tkinter：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m labelme_json_converter
```

Windows PowerShell 激活虚拟环境时使用 `.venv\Scripts\Activate.ps1`。仓库也提供 `run_windows.bat`、`run_macos.command` 和 `run_linux.sh`。

## 测试与诊断

```bash
python -m unittest discover -s tests -v
python -m labelme_json_converter --self-test
python -m labelme_json_converter --ui-smoke-test
```

无桌面的 Linux 使用：

```bash
xvfb-run -a python -m unittest discover -s tests -v
xvfb-run -a python -m labelme_json_converter --ui-smoke-test
```

GUI 烟雾测试会真实调用模式切换、输入/输出路径按钮和开始转换按钮，并验证单文件及递归目录结果。

## 本地封装

先安装项目与固定版本的构建依赖：

```bash
python -m pip install . -r requirements-build.txt
```

- Windows PowerShell：`./scripts/build_windows.ps1`
- macOS：`bash scripts/build_macos.sh`
- Linux x86_64：`bash scripts/build_linux.sh`
- 干净源码包：`python scripts/build_source.py`

正式成品由 GitHub Actions 在对应原生系统构建，不能在 macOS 上直接生成可信的 Windows EXE。

## 发布新版本

1. 更新 `pyproject.toml`、`src/labelme_json_converter/__init__.py` 和 `CHANGELOG.md` 中的版本。
2. 确认 `main` 分支 CI 全部通过。
3. 创建标签，例如 `git tag v1.0.1 && git push origin v1.0.1`。
4. Actions 自动构建四个平台、生成 SHA-256 并创建草稿 Release。
5. 按 [`docs/release-checklist.md`](docs/release-checklist.md) 在真实系统验收后发布草稿。

## 隐私与安全

本项目不需要网络连接，不上传或收集任何数据。请勿向仓库、Issue 或测试目录提交真实患者影像、未脱敏标注、姓名、病历号或其他敏感信息。安全问题请参阅 [SECURITY.md](SECURITY.md)。

## 许可证

[MIT License](LICENSE)
