# Verify Prompt

核查实际 ModelRigor v5.1.2 入口、完整目录、相对链接、模板、schema 和可选只读资源。
运行 `--scope package` 完整性检查：
`python scripts/check_skill_integrity.py . --scope package`
以及回归测试：
`pytest tests/`

确认严重来源不符及大容差、错误 winner、PASS-only verification 被拒；合法 bound 正 gap 不能满足精确最优；无 Benchmark 触发无工件义务；拒绝候选无图源义务，但要求的核心图不能被描述性主张覆盖；全白/无实际尺寸预览拒绝。
确认共同核心 + 适用专业检查，纯统计不强制 ML 切分；普通章节/年号不数字追踪；文字变化不触发科学失效、模型/evaluator/数据/代码变化影响相关链；阶段初始化不造全部管理工件。最终年度官方/匿名/支撑/AI 和实质全文视觉检查未做时明确未验证。
历史固定案例的布尔 counterfactual 只是分类逻辑测试，不当实际改善论文或图像质量通过。具体数学证明、领域正确性、图形编码/实际正文深度和研究质量必须真实审查。
