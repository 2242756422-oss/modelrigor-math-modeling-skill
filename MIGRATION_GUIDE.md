# ModelRigor Migration Guide

ModelRigor 是由成熟数学建模系统演进而来的科研级数学建模、可信计算与学术可视化 Skill（当前版本 v5.1.2）。

## 来源分类与证据契约
- 旧 json_pointer 默认按 COMPUTED 核实真实生产回执；旧 analytical 按推导核验，不能仅靠手写数值 JSON；csv_cell 须明确来源性质，观测/给定参数绑定原始依据。缺口只报告，不补造运行或重跑无关求解。解析证明可无数值回执，现有 verification 可带 argument_check。
- 正式提交为 PDF 时重新绑定实际 PDF 文字、页号、渲染及数值映射；旧 DOCX 记录不自动晋升。
- 七维的科学部分可引用当前有效科学快照；改变模型/关键 Claim 不能沿用。
- 外部只读绘图资源缺失可用已有原生工具（如原生 Matplotlib），不恢复台账义务。

## 迁移原则
- 不自动迁移/重跑旧项目。备份后在副本选择 HIGH_QUALITY_EFFICIENT；未选择保留 LEGACY_FULL 布局和命令。
- 真实性修复适用于所有布局：非零 source_tolerance 需精确读来源，PASS-only verification 改为真实 EXECUTED_CHECK 或 REVIEWED_ARGUMENT；不能补造回执。实际原始计算有效但证据缺失时标 NEEDS_SUBSTANTIVE_REVIEW，只重做必要核验。
- 旧 14 域问题可按实际专业族映射共同核心 + 专业 checks，保留有价值依据/推导；保留核心 scientific snapshot 并在真实复检后重新锁定。不因缺格式文件重跑模型；源代码/evaluator/输入/量词/参数实质变更才按 impact 重验相关链。
- content_units/evidence_promotion/competitive_development/quality_assessment/resource_consumption/五 reviewer 历史文件可归档作参考，不删除用户成果；新验收用一份 research_review 引用原科学判断与实际正文/图审查。
- DELIVERED 图须有 generation_receipt 绑定真实绘图代码、输入及图像输出；已有真实记录可转换，不允许倒填虚构回执。没有记录时只重新执行必要绘图路径，不因补绘图证据重跑无关求解；图像字节相同且尺寸不变时可复用已绑定的实际视觉检查。
- 外部辅助资源（如 cumcm-step-review）保持只读且可选；缺少时平滑降级至原生环境。保留旧模板只为兼容，不作为新项目必须填写清单。
