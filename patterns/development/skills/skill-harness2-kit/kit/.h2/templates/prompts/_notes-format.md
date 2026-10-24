<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の aggregate() の「NOTES FORMAT」 -->
# notes の形

1つの `<notes>` の区画に、決めたことを1行ずつ、次の形で書く。

    kept|revised|dropped -> <どの編集> -> <決めた根拠の軌跡の場面か、基準の集まりの傾向。集まりなら数を添える。例「基準の実行 ${example_failed}/${k} で失敗」>

根拠の無い決定は、次に読む人が確かめられない決定である。
