# Read-only Resource Adapter

资源根优先从当前环境可用Skill目录发现，不猜固定历史路径。`cumcm-step-review`仅只读使用：模型选型、算法说明、chart knowledge、plot style、draw.io、Word/OMML等。不得读取其根SKILL作为v5主流程控制器。

HIGH_QUALITY_EFFICIENT不要求`resource_consumption.csv`或逐调用审批。实际使用的资源代码作为run receipt的code/input绑定，结果与图沿现有Registry/Claim/Figure关联；必要的接口适配与语义判断记在已有研究记录中。仅未迁移的LEGACY_FULL保留旧台账兼容检查。导入资源设置`PYTHONDONTWRITEBYTECODE=1`，不得在只读目录产生`__pycache__`。

先发现能力，不把外部Skill当硬依赖。资源存在且接口可用时复用；缺少plot_style或接口不可用时用已可用的MATLAB或原生Matplotlib Figure/Axes直接生成真实数据图，显式说明降级范围并做同样来源/实际视觉检查。缺draw.io可用可编辑SVG；缺Word工具可用现有OOXML/docx能力；不能把缺失的专门能力伪称已完成。不要复制旧Skill或为普通绘图安装重叠库。visual_resource_smoke实际测试可用资源，资源缺失时实际测试原生绘图，而不是静默跳过。

数据图采用实际`plot_style.py` API：`apply_publication_style`、`publication_subplots`、`export_figure(..., extra_formats=..., size_inches=...)`。旧recipes中的`setup_style`、独立`export_figure`导入和`formats=`参数不可照搬。补充独立legend/marker/axis语义审查，因为旧`audit_design`覆盖不完整。

选图与组合图优先按发现后的资源树读取`references/绘图参考/chart_selection.md`、`chart_knowledge_base.md`、`figure_architecture.md`及`assets/figure-templates/`（若实际存在），再由v5的Figure Role与真实数据契约裁决。旧资源中的raw/process/result固定候选数量、每类至少若干张等数量规则一律不继承。数据/ML题可参考资源中的data profiling/数据剖析材料，但预处理仍以当前Model Contract、泄漏控制和`data_quality_preprocessing_playbook.md`为准。

所有figure templates默认为DEMO_QUARANTINED。删除合成数据、预设AUC/p值、原作者、旧图号与硬编码caption后，绑定真实Result IDs和输入hash，才可晋升。算法说明也是候选知识，不是已核验实现；运行小精确例、边界/守恒和evaluator一致性后再用。

Word排版API中的历史15000字、8图、约20页、30页上限不继承。只复用样式/表格/OMML/OOXML primitive；页限由page policy独立判断。figure_audit、paper_check和repro_manifest仅按其真实覆盖范围解释，不把文件存在、字符串匹配或清单生成当科学PASS。
