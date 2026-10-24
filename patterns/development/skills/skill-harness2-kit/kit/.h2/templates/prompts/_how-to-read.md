<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の _TTS_HOW。最後の問いは _tts_aggregate の「読み込まれなかったスキルの編集は何も変えていない」を、Skill の呼び出しの有無に読み替えて足した -->
# 証拠の読み方

同じ条件の実行どうしの違いが信号である。全部の実行が同じことをしたところでは、スキルが既に振る舞いを決めている。違いが出たところ（1つだけがファイルを書いた、1つがやり直しで予算を使い切った、1つが成果物を書く前に止まった）では、スキルが判断を運に任せている。その分かれ目が直すべき所である。それぞれについて問う。
  - 必要な手順が暗黙のままで、一部の実行だけがそれを行ったのではないか
  - 繰り返し起きる機械的な操作（形式の読み取り、2つの資料の突き合わせ、特定の種類のファイルの書き出し）の手順が無く、実行ごとに即興したのではないか
  - 道具のエラーが実行をまたいで繰り返され、使い方の手引きか補助のスクリプトで直せるのではないか
  - 成果物を書く前に予算を使い切った実行は無いか
  - スキルが呼ばれなかった実行（軌跡に `[ACTION] Skill` が無い）は無いか。呼ばれていなければ、本文と参照ファイルの編集はその実行を何も変えない

すべての変更は、特定の実行の場面か、作業場所の資料にたどれなければならず、notes でそれを示す。場面を挙げられない編集は推測であり、文脈を使うだけで何も得ない。
