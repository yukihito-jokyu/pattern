<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の propose() の「HOW TO DECIDE WHAT TO CHANGE」 -->
# 何を変えるかの決め方

すべての編集は、軌跡の中の場面にたどれなければならない。編集ごとに問う。どの実行が何をしたか、この文があればそれは変わったか。場面を挙げられないなら、その編集は推測であり、文脈を使うだけで何も得ない。次の順で選ぶ。
  1. 分かれ目。実行どうしで振る舞いが違った。エージェントは既にできるので、伝えるだけでよい。最も安く得られる改善である
  2. 繰り返された具体的な失敗。すべての実行で同じエラーか抜けがあった
  3. 軌跡に見えるが、まだ起きていない危険

実行が既に正しくできたことは直さない。スキルが既にはっきり書いていることを繰り返さない。重複した指示はほかの指示を薄める。

${candidate_of}

${round}

平均に寄せたり、全部を覆おうとしたりしない。あなたの次元の、最も擁護できる1つの版に絞る。後の段が比べて合わせる。
