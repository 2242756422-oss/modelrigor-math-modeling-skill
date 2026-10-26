# KEY_DECISION_ONLY 与 RETURN_AUDIT

FULL_RESEARCH按主研究路径完整求解。KEY_DECISION_ONLY只改变执行分工：核心题意/领域/模型、evaluator/计算规格、关键验证和图表任务由Codex明确；外部执行代理完成真实生产计算、图表和正文。仅在用户授权发给外部任务时发送，不自行创建任务。
Stage A输出QUESTION_DECISION_PACKET并标READY_FOR_EXTERNAL_EXECUTION；必要时DRAFT，允许少量明确标注原型，不做Freeze或虚构最终结果。外部发现模型改动先报MODEL_DEVIATION_REQUEST。
RETURN_AUDIT复用真实运行/来源证据，按已知风险抽查；遇矛盾局部升级，不默认完整重跑。任务错位、领域/模型P0、核心结果不真、重要验证缺失、图源错误/核心机制缺失/不可读图、官方交付错误、重大过度主张均阻断。图表质量不能因额度不足降为“非阻断”；实际查看关键正式图及最终尺寸，不能只读字段。
do not把COARSE_ACCEPTED冒充Scientific Freeze或Research Freeze。正式完成仍走真实性、专业验证、研究成果验收及最终Whole-Paper/官方门禁；新路径不强制five independent reviewer roles，旧项目可保持已有真实评审资料。审核分工不变成较低科学标准。
