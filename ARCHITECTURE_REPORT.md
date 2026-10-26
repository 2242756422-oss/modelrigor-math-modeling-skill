# v5.0 实施架构

> 历史v5.0架构记录，保留溯源。v5.1活跃策略以SKILL.md、references/efficient_research_protocol.md与实际代码为准；新路径不再强制14问、全目录证据晋升、五角色逐问审稿和重复开发/质量台账。

此设计承接实施前 ARCHITECTURE_PROPOSAL.md 和 DIAGNOSIS_REPORT.md；论文Benchmark完成后进入独立构建目录。术语以用户要求为准：Scientific Freeze固定科学快照，Research Freeze表示竞争性开发完成，旧研究报告中的Research/Paper命名建议不作为新版规则。

## 规则、工件和判断

policy.json是版本、状态机、七质量维度、五审稿角色与规则ID的唯一机器源。根SKILL路由到domain、science、development、visual、whole-paper、resources六份协议。模板提供结构，空模板标记DRAFT，不可以通过冻结。schema检查类型、必填、枚举和引用；领域/充分性判断必须独立阅读实际工件，不把自填PASS视为科学证明。

脚本core.py提供可复用验证函数；cqex.py及配套单用途脚本提供init、audit、freeze、reopen、stale、scan-evidence、benchmark、route-depth与数字绑定命令。结果登记采用JSON Pointer、CSV行列、文本解析结论三种真实来源；所有来源绑定SHA256。数值比较区别来源精确一致与正文显示舍入，容忍度必须来自测量/数值/业务意义，不允许任意大容忍掩盖错误。

## 领域门禁

domain_model_map包含14项专业问题回答、逐层model_ladder、变量/参数/nuisance职责、文献到模型对象映射、省略层及其反事实风险、P0 issue与处置。理论问按数学对象和定理条件回答，可说明外部文献不适用；不是空白豁免。物理需机理/介质/边界/响应/观测，优化需状态/决策/约束/目标/执行，数据需生成机制/观测单位/切分/特征/验证。模型契约将domain对象与方程、evaluator输入输出相连。

P0不通过阻止新求解；历史科学结果允许有条件保留，不因此获得Research Freeze。新增领域层应回答是否可辨识、数据是否支持、误差是否主导，避免复杂化冒充专业性。

## 科学快照及依赖

scientific_manifest绑定model、evaluator、sources、results、verification的哈希与科学版本。下游handoff记录实际使用的上游版本、对象、符号、单位、假设与evaluator契约。核心文件变化使快照和所有依赖结果STALE；只改变写作版本不触发无意义重算，但正文与页面QA需更新。

Scientific Freeze检查模型闭合、假设账、来源、主风险验证、Claim–Evidence。Research Freeze额外检查domain、推导、方法、证据提升、图表、公式、内容、peer gap、独立评审、页面QA。全文发现欠展开可以REOPEN_FOR_DEVELOPMENT，保留科学快照；核心变化走科学复验。禁止先手写FROZEN再让检查器批准。

## 内容、页限与视觉

content_units按问题实际研究任务列required、importance、正文定位、支撑证据、展开状态。重要缺项或高价值证据未提升判UNDERDEVELOPED；已充分覆盖且存在冗余判OVERDEVELOPED；二者并存时优先修缺项并另列删减。不能以页/图/公式数推断。

page_budget初始UNSET，官方规则需当届年份、来源文件hash、条款位置、原文摘录、总页限与正文/摘要/文献/附录/封面/AI声明各范围。部分未知保留UNKNOWN，不虚构false。规则核验与内容判定独立。每次Freeze事件记录实际内容变化、图表和复用，再更新篇幅规划。

figure_candidates从Model Closure生成，role、question、message、source、chart、cost、page_cost、importance、status齐全。role需求来自实际模型理解任务；缺必要角色无有效等价表达阻止Research Freeze。单调性来自重复编码不能回答多种任务，而非同类图比例的机械阈值。Hero候选记录尝试及采用/拒绝理由。

数据图通过只读plot_style真实接口导出；科学结构走SVG/draw.io。模板仅作为布局primitive。resource_consumption记录执行、输入/输出与适配，demo数字和p值不能晋升真实证据。最终Word与全部A4页面绑定文档hash、页图hash和页号；人工检查字体、公式、线宽、marker、图例、panel、图注、图文比例、留白、分辨率、语言和邻图重复。机器验证绑定有效，人工判断视觉质量，二者不得互相冒充。

## 独立评审及验收

五角色分别接收最小原始工件、主Skill和任务，不提供期望结论。每份报告保存身份/会话或运行ID、独立输入hash、实际读取工件、问题位置及结论。复制结论不能算独立；运行环境无法提供独立评审时报告PENDING，不伪造五份PASS。质量维度无加权补偿。

integrity分包装、schema、编译、规则、流程、领域、内容、视觉、竞争质量、反膨胀十组。运行正反例、旧漏洞、真实B属性审查、匿名重命名和改善反事实；语义审查与脚本单测分开报告。不得把测试fixture的PASS直接当实际论文审查PASS。

## 交付与边界

新包完整重写活动规则，迁移文档只记录历史变化；不复制失效v3/v4政策进活动目录。安装包只含cumcm-question-expert一层，根SKILL YAML name一致。构建不修改现有安装与旧赛题。安装提示要求读取当前支持的Skill机制、备份同名旧目录、整个目录替换、完整校验并报告权限失败；step-review保持只读资源，selector不安装。
