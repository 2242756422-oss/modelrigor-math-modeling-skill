# Visual Research Engine Design

视觉机会从Model Closure开始，候选记录role、research question、message、输入与输出双hash、data identity、demo quarantine、chart type、成本、重要性、caption/Word定位和状态。角色覆盖是质量门禁，图数自适应。复杂物理过程缺已交付或等价机制证据即失败；理论证明可0图。

单调性判断针对“同一编码回答不同任务却无TASK_MATCH理由”，并结合未覆盖任务，避免为多样性使用错图。核心问尝试Hero图但不设配额。Table Portfolio与Figure Portfolio按信息结构分工。

数据图真实调用只读资源库`plot_style.py`的`apply_publication_style`、`publication_subplots`与`export_figure`。机制/架构使用SVG或draw.io。所有演示模板隔离：去除合成数据、硬编码AUC/p值、原作者和旧图号，绑定真实结果后才可用于论文。

最后将图插入确切Word并渲染A4页面；QA用结构化renderer manifest把DOCX、命令、工具版本、退出码和逐页PNG hash连成一条链，再以逐页review JSON检查图注、公式、表格、可读性、裁切和页码。机器拒绝空白页。图文件PASS不代表页面PASS，文档变化会使页面QA过期。
