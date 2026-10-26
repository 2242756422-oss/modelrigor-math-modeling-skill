# 科学证据与真实性

结果来源转录必须精确一致，source_tolerance只能为0，嵌套非有限值也拒绝。数值误差发生在两次计算/解析结果之间：明确atol/rtol、依据与对结论影响，不能拿它覆盖登记来源错误。display由原始值按显示精度舍入，不信任任意display_tolerance。
record_run真实执行用户指定命令，保存代码/输入/输出/日志hash、运行时间、退出码；audit不执行回执内的不可信命令。程序结果由来源JSON Pointer/CSV读出，register_result不要求AI再抄raw。回执证明绑定与执行记录，不防止恶意伪造全部文件，不等于算法正确。

v5.1.2回执在实际argv中识别Python直接`.py`入口或工作目录内的普通源模块/包`-m`（包初始化源码自动绑定）；路径按绝对身份与符号链接目标核对，不看命令里的文件名子串。辅助源码可以登记但不伪称均已执行，额外脚本参数不证明导入。独立实现检查实际入口hash，附加未用文件不能制造独立性。Shell、`-c`、Notebook、MATLAB/R及外部模块搜索只记录LIMITED范围，不自动取得计算认证；可用`--entry-review`复用REVIEWED_ARGUMENT（精确command数组、code的完整hash绑定、argument/review_evidence和具名substantive_review）实质核查入口，仍标LIMITED/REVIEWED_ARGUMENT_NOT_AUTOMATIC_ENTRY_CERTIFICATION，不假装自动认证。明确识别的错入口不能靠论证豁免；有限范围论证可以支持真实复杂工作流，但不是任意动态程序证明。

回执保留真实`process_exit_code`，兼容`exit_code`同值；`provenance_status`另记PASS/FAIL/LIMITED。代码/输入记录执行前后hash及路径，变化/删除/符号链接换目标阻断来源认证；正常新输出与中间文件不当成输入篡改。原地预处理改用独立输出后进入下一运行；输入/代码/回执/输出不可混用。前后相等仅是两时点一致，不证明中途未变再恢复；不监控未登记副作用，不是沙箱。运行前已经改变的内容绑定本次真实版本，上游旧hash自然失效。旧有效回执仍可核当前依赖和argv入口，但明确LEGACY_POST_RUN_ONLY，不补造前hash；无法确认入口的旧记录不能自动认证。严格快照只在具体风险需要时采用，不默认复制全部大数据。
verification分EXECUTED_CHECK和REVIEWED_ARGUMENT。前者绑定回执及输出，重新核算机器可判断关系；后者绑定真实推导及具名实质判断，明确是审查论证、不是自动证明。PASS/method/独立角色名称均不作为证据。独立实现需不同代码哈希、相同科学定义、独立性范围与依据；不同seed/文件名不是独立验证。数学论证、独立数据、实现交叉验证各按真正风险采用。

## 条件证据

来源的category与JSON/CSV定位type分开：COMPUTED须有生产run receipt且实际生成来源文件，不能用只生成验证输出的回执充当求解；ANALYTICAL须有REVIEWED_ARGUMENT推导与实质审查，observed_value明确所审结论并与登记一致，可在已有verification的argument_check复用，不强制数值运行；OBSERVED/GIVEN在source.origin记provider、nature、原始hash locator，不冒充计算，输入不能替代待建模的输出；DEMO标注demo_label且不能作为批准科学结果。旧analytical推断为解析、json_pointer推断为计算；歧义csv_cell须显式分类。仍核verification、版本和来源值。匹配所审结论不是自动证明一般推导正确。

统一read_document/document_text读取DOCX、PDF、UTF-8文本；PDF locator支持`page=N::文字`并绑定实际提交文件hash。PDF无文字层/文字缺失或不可读时文字审查未完成，须OCR或核对转录，不从二进制字节猜文本。DOCX草稿转PDF提交后，以实际PDF重新关联数字、图文与逐页QA，不把DOCX哈希当PDF验收证据；文字提取不证明复杂公式/图像正确。

Benchmark仅有真正竞争方案/相对优越主张时触发。公平数据/evaluator/域/预算/终止/指标/方向/硬件，实际运行值自动排名；报告winner、方向、均值、gap/tolerance须可复现。随机比较的重复、配对和不确定性由科学问题决定；均值胜出不等于统计显著，统计主张需独立统计分析及假设审查。
Bound/Gap：合法bound与算术gap分开。有限穷举需真实完整域、实际evaluator输出及完整性论证；解析/松弛/solver certificate需有效域关系、推导、审查及边界。achieved须对应批准结果。合法界不能仅凭PASS认定。
Alternative Formulation必须是数学定义相同、不同路线的实质cross-check。Ablation需改变组件、固定条件、比较单位与混杂边界；不能由“少一个模块后指标降低”无条件推出因果。
Verification Pyramid按主风险选择守恒、代入、极限、精度/离散、可行性、独立实现、数据留出、识别/鲁棒性，不要求通用全套。
Scientific Freeze绑定科学工件/外部依赖与Claim digest，幂等冻结不重算。模型或关键依赖变化只重新验证受影响链；假设、量词、evaluator与结果跨问不能静默变化。
