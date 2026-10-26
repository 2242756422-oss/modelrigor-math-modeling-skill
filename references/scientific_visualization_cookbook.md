# Scientific Visualization Cookbook

本文件只在已经确定“需要一张图”之后帮助选图和定稿；它不产生图数配额，也不替代`Visual Research Engine`、Figure Contract、数据/结果hash和A4页面QA。项目已有`visual_semantics.json`时，颜色、线型、marker语义以项目文件为先。

## 先按研究问题选图，而不是按“看起来高级”选图

- 单变量趋势/时间过程：`line`；需要累计量才用`area`。有不确定性时优先line+ribbon/errorbar，而不是再画一张重复折线。
- 两变量关系：`scatter`；样本密集时`hexbin`；点大小有第三变量且语义明确时`bubble`。
- 单变量分布：`histogram/density/ecdf`；组间分布优先`box/violin/raincloud`，样本少时保留原始点。
- 多变量相关/矩阵结构：`correlation_matrix/heatmap/cluster_heatmap`；色标必须有定义，发散量以有意义中心值对称编码。
- 参数敏感性：一维可`line/tornado`，二维可`sensitivity_matrix/contour`，三维连续关系可`surface+contour`；不要为展示3D而使用3D。
- 模型误差与验证：预测-真实用`parity`，残差结构用`residual`，分布假设用`qq`，区间覆盖用`interval/errorbar`；分类任务按需要使用`roc/pr/calibration/confusion_matrix`，不能用单一AUC替代全部验证。
- 方法/模型比较：少量模型单指标用`dot/bar`；带区间或效应量用`forest`；多指标多模型用`heatmap`或紧凑`multi_panel_composite`。
- 优化：过程稳定性用`convergence`；低维目标结构用`objective_landscape/contour/response_surface`；约束或权重变化用`sensitivity_matrix`；只画最优值而不解释可行域通常不足。
- 结构和机理：几何关系用`geometry_schematic`，物理/业务机理用`schematic`，算法步骤用`workflow/algorithm_architecture`；结构图必须表达真实模型关系，不装饰。
- 流量/网络：有守恒流量才用`sankey`；关系网络用`network`；环形关系仅在弦结构确有优势时用`chord`。
- 空间：需要地理/空间位置才用`map`；若空间只是索引，不强行地图化。

## Composite Figure

当2–4个证据回答同一主问题且共享变量/样本/场景时，可设计`multi_panel_composite`。每个panel必须有独立任务，使用(a)(b)(c)…标签；共享轴、共享legend或colorbar只在尺度和定义一致时使用。不得把无关图拼在一起制造“图多”。

常见高价值组合：

- 主结果 + 机制解释 + 局部放大/边界；
- 预测一致性 + 残差 + 误差分布；
- 收敛 + 多seed稳定性 + 最终解比较；
- 一维敏感性 + 二维交互热图；
- Benchmark主指标 + 区间/波动 + 计算代价。

## Micro-style与出版检查

- 数据优先、背景简洁；禁止jet/rainbow和无信息3D、阴影、渐变。
- 颜色同时配合线型/marker保证灰度可辨；颜色语义跨全文一致。
- 坐标轴必须有变量名和单位；尺度、截断、对数轴和归一化需在图注或正文解释。
- 图例不遮挡证据；高密度点使用透明度/hexbin/抽样显示，但统计量仍基于完整数据。
- 误差棒/置信带必须说明定义、置信水平与计算方法；显著性标记必须有真实检验来源。
- 多panel对齐轴、字号、留白和panel标签；共享colorbar必须对应同一数值映射。
- 最小字号、线宽、marker、DPI和最终尺寸以实际A4插入后的可读性为准，而不是单独PNG看起来清晰就算PASS。
- 优先输出可复现的矢量SVG/PDF或高分辨率PNG；最终仍要经过现有hash、caption和Word页面QA。

## 禁止机械继承

不规定每问必须有图、流程图必须固定布局、问题分析达到某字数就补图、每图必须保留原图型，也不规定固定Nature色板。已有图仅做视觉重绘时应保持数据和主结论；若Figure Editor判断研究表达明显更适合另一图型，可以重新设计，但必须重新绑定数据、caption、Figure记录和QA。
