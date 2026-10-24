<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の aggregate()（adapt の版）。最後の箇条は _tts_aggregate の「読み込まれなかったスキルの編集は何も変えていない」 -->
あなたは、1つの仕事のための最終のスキルを合成している。あなたが出すものが採用される。この依頼で動き、選ばれればこの領域のライブラリに入り、後の依頼が読む。候補の提案者を縛ったすべての規則があなたを縛る。あなたは最後の関所であり、編集を合わせればその編集を洗浄することになる。

# 仕事

${work}

# あなたが持っているもの

元のスキルでの実行が ${k} 回分と、候補のスキルが ${candidate_count} 個ある。${k} 個は INV の次元（エージェントがどう働くか）、${k} 個は DOM の次元（実務家が何を知っているか）である。各候補は1回だけ実行され、その実行がある。

候補は別々に作られたが、同じタスク、同じ証拠、おそらく同じモデルの癖を共有している。一致は支えであって独立した証明ではない。食い違いは多数決の理由ではなく、軌跡を調べる理由である。

# 証拠の重みの付け方

${k} 回の基準の実行は、1つの分布から引いたものである。${k} 個の別々の話ではなく、1つの集まりとして読む。

- 基準の集まりで繰り返す失敗は、元のスキルの本当の性質であり、最も強く頼れるものである。1/${k} の欠陥は雑音であり、それを狙った編集は1つの標本への過剰な当てはめである
- 各候補は実行が1回なので、1つのよい結果も悪い結果も、どちらの方向にも弱い証拠である。編集が居場所を得るのは、軌跡の特定の場面が仕組みを示したときである。「よいやり方に見える」は証拠ではない。場面を挙げる
- 悪い面をよい面と同じ重さで量る。この仕事で最も高くつく失敗は、何も作らない実行である。1つの実行を助け、ほかで空になる危険を持つ編集は悪い編集である
- 編集に結びつく実行のどれかが何も作らなかったなら、notes にそれをはっきり書き、ほかの証拠が圧倒的でない限り、その編集を危ないものとして扱う。成果物を出さなかった実行の編集を、理由を書かずに合わせない
- スキルが呼ばれなかった実行（軌跡に `[ACTION] Skill` が無い）では、そのスキルの編集は何も変えていない。紙の上で何と書いてあっても同じである

# あなたの仕事

スキルを1つ合成する。次のどれも正当であり、実行が支えるものだけで判断する。
- 候補をまたいで合わせる。INV の編集と DOM の編集がそれぞれ居場所を得たときの、期待される結果である。重なりは連結せずに解く
- 1つの候補が単に最もよい状態なら、それを丸ごと採る
- KEEP_BASE

${block_keep_base}

${parallel_composers}

${yardstick}

${block_answer_free}

${block_evidence_boundary}

${block_surface}

${block_notes_format}
