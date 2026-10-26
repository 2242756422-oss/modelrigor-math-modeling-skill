# Install Prompt

只安装 modelrigor 整个文件夹，先定位实际用户 Skill 目录并备份同名目录。
外部辅助资源（如 cumcm-step-review）仅作为可选只读资源；缺失时自动使用原生 Matplotlib 与标准工具平滑降级，不破坏任何核心数学建模与验证功能。

安装包第一层应为 modelrigor（或 modelrigor-math-modeling-skill），根目录下包含 SKILL.md 且 YAML name 一致为 modelrigor。
运行 `python scripts/check_skill_integrity.py <安装根> --scope package`，另外可运行 skill-creator 的 quick_validate。

包 PASS 表示代码、模板、接口与回归测试全部通过，不代表任何具体学术论文或竞赛成果的免审通过。真实论文渲染验收另使用 `--scope full --real-paper <DOCX> --real-render-dir <逐页PNG> --renderer-artifact <真实结构化render manifest> --page-review <实际逐页检查JSON>`。缺证据明确标记 NOT_ASSESSED，不伪造回执或人工审阅记录。
