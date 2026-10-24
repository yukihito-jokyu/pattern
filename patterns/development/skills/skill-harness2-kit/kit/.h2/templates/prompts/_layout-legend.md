<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/context.py の ContextTree.layout の説明の文。どのパスが今回あるかは、上の一覧（Python が作る）が示す -->
各パスの中身は次のとおりである。一覧に無いものは今回は無い。

    context/task.md                  エージェントが受け取ったままの依頼文
    context/source/                  タスクの材料（実行の作業場所に置いたもの）
    context/decisions/<label>.md     前の段の編集と合成の決定（notes）
    context/rollouts/<label>.md      実行の軌跡の全体（切り詰めていない）
    context/deliverables/<label>.md  その実行が作ったもの（最後の返答と、作業場所で足した・変えたファイル）
    context/harness/                 今のスキルの木
    context/base_harness/            編集する前の元のスキルの木
    context/pool/<label>/            候補ごとの harness/（その木）、harness.diff（編集元との差分）、rollout.md（その実行の軌跡）、produced.md（その実行が作ったもの）
    context/library/                 この領域の前の依頼で選ばれたスキルと教訓。まず INDEX.md を読み、関係がありそうなものを開く
    context/adoption.json            選ばれたラベルと、選択で使った匿名の ID とラベルの対応

軌跡のすべてのイベントがある。軌跡はこの依頼文に収めるために切り詰められていない。1つの観測の中に、描画の側の切り詰めの印が入っていることがある。その印は描画の側のものであり、エージェントの振る舞いではない。エージェントの失敗として診断しない。
