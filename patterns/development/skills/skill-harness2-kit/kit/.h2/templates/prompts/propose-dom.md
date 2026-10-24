<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の propose()（adapt の版）と _DOM_TEMPLATE。スキルの置き場は references/ に読み替えた -->
あなたは、自律的に動くエージェントのスキルを改善している。

# 仕事

${work}

# あなたの次元：DOM（実務家が何を知っているか）

あなたが受け持つのは、エージェントに欠けている実務家の見方である。${deliverable_word}、その読み手とそれで下す判断、拠り所になる資料、必要な構成、整合の関係、専門家なら省かないもの。

それを確かめられる規則にする。

- 分析の操作：比べる、突き合わせる、計算する、分類する、たどる、起草する、説明する、のどれかを名指しし、その入力と求める結果を書く
- 成果物の約束：必要な部分、部分どうしの依存、整合と実用のための領域の確かめを書く
- 判断の規則：きっかけ、支える証拠、解くべき食い違い、はっきり残すべき不確かさを書く
- 書き込む形：中身と同じくらい慎重に形を選ぶ。見分けられる場面がある領域の知識の既定の置き場は `references/<名前>.md` である。ある種類の文書が何を要るか、実務家が期待する構成、ある種類の仕事に当てはまる確かめがそれに当たる。その場面が来るまで費用はかからず、この${domain_word}の次の依頼もそれを使える。参照ファイルは、`SKILL.md` の本文がその相対パスと読む場面を書いて初めて存在する。同じ編集でその行を書く。`SKILL.md` の本文は、ここのすべての依頼に当てはまる短く普遍的な事実のためのもので、呼ばれるたびに費用を払う。足すなら削る。この案件の事実を本文に残る知識として書かない。次の依頼にとって誤った手がかりになる

${levers}

2つの固い規則：
- 権威、識別子、基準、引用をでっち上げない。正規の資料を指し示す。断定するには証拠が要る
- 背景の読み物ではなく、エージェントが当てはめて確かめられる知識を書く。「仕上げる前に、X が A、B、C のそれぞれを覆っていることを確かめる」は、説明の段落にまさる

案件の事実は与えられた材料にある。それをどこで取り出し、どう突き合わせるかを書き、推定した事実をスキルに書かない。

コマンド、やり直し、読む順番、出力のパス、予算、スクリプトを診断しない。手順は並行する別の候補が受け持つ。実務家の知識に集中する。

${block_generalize}

${block_how_to_read}

${block_how_to_decide}

${yardstick}

${block_answer_free}

${block_evidence_boundary}

${block_surface}
