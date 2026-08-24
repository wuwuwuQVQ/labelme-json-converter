# Release Checklist

草稿 Release 只有在下列项目全部完成后才能发布。

## 自动化门禁

- [ ] `main` 分支 CI 在 Windows、macOS ARM64、macOS Intel、Linux 全绿
- [ ] 四个平台封装任务成功
- [ ] 每个最终二进制的 `--self-test` 通过
- [ ] 每个最终二进制的 `--ui-smoke-test` 通过
- [ ] 四个 ZIP 均可完整解压
- [ ] `SHA256SUMS.txt` 与 Release 文件一致
- [ ] Release 中没有 JSON、图片、转换报告或其他真实数据

## Windows 10/11 x86_64

- [ ] EXE 可双击启动
- [ ] 单文件与递归目录模式可点击切换
- [ ] 两种模式下输入选择窗口类型正确
- [ ] 输出目录选择按钮可用
- [ ] 单文件转换成功且源文件不变
- [ ] 嵌套目录转换成功且目录结构保持
- [ ] 转换结束后按钮恢复可点击

## macOS Apple Silicon

- [ ] APP 可通过 Control 点击“打开”启动
- [ ] 重复完成 Windows 清单中的全部 GUI 操作

## macOS Intel

- [ ] APP 可通过 Control 点击“打开”启动
- [ ] 重复完成 Windows 清单中的全部 GUI 操作

## Ubuntu/Linux x86_64

- [ ] 可执行权限和 GUI 启动正常
- [ ] 重复完成 Windows 清单中的全部 GUI 操作

## 发布

- [ ] README 下载表与实际文件名一致
- [ ] CHANGELOG 已记录本版本
- [ ] 版本号与 Git 标签一致
- [ ] 人工验收人和日期已记录在草稿 Release 说明中
- [ ] 草稿 Release 已手动发布

