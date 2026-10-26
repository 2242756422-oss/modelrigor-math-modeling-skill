# Whole-Paper Final Audit

触发：Whole Problem Map主要问题正文全部SOLVED/DRAFTED/FROZEN或等价，之后且摘要定稿/全文最终压缩/Word排版/提交版之前。单问不完整执行此审计。AUDIT只报告、不自动重画；授权修改后按优先级局部处理。

先科学一致性：当前Research验收和Scientific快照、跨问evaluator/量词/假设/单位/符号、上游依赖与Result/Claim来源。关键数值映射，不机械追踪年份/章节/公式常数。全部正文需要实际阅读，七维评价可引用已验证科学事实；全局竞争叙事和贡献另做实质判断，不强制重新五角色运行。

## Whole-Paper Figure Inventory

final_visual_inventory读取图、table和page_budget，生成whole_paper_figure_inventory.json及WHOLE_PAPER_FIGURE_AUDIT.md，状态PENDING_ACTUAL_WHOLE_PAPER_REVIEW。计数来自已登记元数据，不能当质量通过。
记录Figure ID、Question、Section、Role、Chart Type、Panel Count与逐panel任务、Evidence Claim、Referenced By、Color Semantics、Page Cost、Status。Formal Figure Count / Effective Panel Count / Evidence-bearing Figure Count分别统计，另Table Count。实际阅读全文/Word图像，补登记仅嵌入Word的flowchart、mechanism、algorithm和subfigure，不仅按文件名计数；核实panel数及独立证据任务。

## 一次完整Portfolio审查

- 视觉密度：连续文字/公式、前后半图集中、多个图堆叠却无分析、存在2–3页明显可视机会但无图。无每页/每问图数指标。
- 角色覆盖：论文真的存在的机制/几何、核心结果、算法选择影响、协同/分配/时空、区间覆盖、最终系统结构是否缺表达；不要求角色全套。
- 跨問重复：trajectory/convergence/timeline/bar/heatmap等是否新增结构未画或同构本来合理；不为多样化强换图。
- ADD_MISSING_FIGURE仅为不可替代机制、创新、压长文、难懂关键结论、多主体/时空、总体方案、二维决策/响应/不确定结构。每项写“不加损失什么”；只为更多好看禁止。
- 同时寻找DELETE、MERGE、MOVE_TO_APPENDIX、CONVERT_TO_TABLE：重复表数字、证据重复、低信息收敛、装饰参数柱、未引用/无分析、低优先验证占篇幅。图数可增/减/不变。
- 实际打开每张正式图及最终A4页面：科学图源/编码、字体字号线宽marker、轴单位、legend/colorbar、panel、caption、白底留白；同实体跨全文保持视觉语义，不机械固定色。
- 图文：第一次引用 → 图 → 解释。图不先于引导、不只“如图所示”，caption不代正文分析，距离适当。
- 读取page_budget并按当届官方限额取舍：先删重复文字/合并/高密图替文字/低优验证附录，不删除核心模型/结果图。

最终报告至少：三种Figure计数、Table Count、各问/Role分布、密度、重复、缺图/删除/合并/附录候选、一致性、预算影响、最终Portfolio。逐图KEEP / POLISH / REDRAW / MERGE / DELETE / MOVE_TO_APPENDIX / CONVERT_TO_TABLE；缺图ADD_MISSING_FIGURE；P0核心论证缺失、P1明显提升、P2有空间再做。实际审阅完成才写Status: REVIEWED，并由具名whole_research_review绑定报告/最终正文证据。清单生成不能替代该判断。

## 最终交付

cqex audit-paper自动检查全局registries/版本/关键数值、有效DOCX、真实render manifest和所有A4页的hash/页号/检查记录。新路径另核contest_rule_profile年度来源/格式/页数/支撑/匿名/AI资料和实际全文审查。人工页审查包含clipping、captions、equations、tables、readability、pagination；自动检查只能保证绑定，不保证视觉/科学判断真实正确。
表达欠充分可REOPEN_FOR_DEVELOPMENT，保留科学快照；科学改变走相关复验。默认先报告，未授权不批量改论文。
