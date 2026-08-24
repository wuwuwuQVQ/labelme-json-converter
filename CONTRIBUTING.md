# Contributing

感谢参与改进。提交代码前请：

1. 创建独立分支并保持变更范围单一。
2. 使用 Python 3.9+，运行 `python -m pip install -e .`。
3. 运行核心测试、`--self-test` 和 `--ui-smoke-test`。
4. 行为或使用方式变化时同步更新 README 和 CHANGELOG。
5. 不提交构建产物、真实影像、真实标注或其他敏感数据。

Pull Request 请说明目标、行为变化和实际验证结果。转换规则变化必须同时新增测试，证明除明确允许的字段外标注内容保持不变。

