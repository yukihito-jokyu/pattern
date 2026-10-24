<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/context.py の mission()。証拠はファイルで渡し、このプロンプトは仕事と証拠の場所だけを書く（STATE-03） -->
${job}

# あなたの証拠

証拠はディスクの `context/` にある。読むこと。この依頼文だけから答えない。

${layout}

${block_layout_legend}

まず `task.md` と今のスキルを読む。使える実行と候補をすべて数え上げ、決める前にそれぞれを少なくとも1回は調べる。候補については、編集元から何が変わったか、その実行で振る舞いの何が変わったか、何がよくなったか、何が後退したか未解決のまま残ったかを比べる。それから、どの編集にも関わる証拠を深く読む。すべての変更の裏にある軌跡の場面を挙げる。場面にたどれない変更は推測である。
