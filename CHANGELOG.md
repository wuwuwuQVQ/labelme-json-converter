# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [1.0.1] - 2026-08-25

- 将 GitHub Actions 构建 Python 升级到 3.11，修复 macOS Intel runner 的 Tkinter 测试兼容问题。
- 更新官方 Actions 主版本，避免 Node.js 20 弃用警告。

## [1.0.0] - 2026-08-25

### Added

- Labelme JSON 5.x/含内嵌图像 JSON 转 6.3.0 无图像数据格式。
- 单文件与递归目录 Tkinter 图形界面。
- 原文件保护、输出冲突跳过、转换报告和 Unicode 路径支持。
- 核心自检与完整 GUI 按钮烟雾测试。
- Windows x86_64、macOS ARM64、macOS Intel、Linux x86_64 自动构建。
- GitHub 草稿 Release、SHA-256 校验和与人工发布门禁。
