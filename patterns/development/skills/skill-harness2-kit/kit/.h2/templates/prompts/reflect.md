<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の experience() と、core/selection.py の _distil() の「WHAT HAPPENED」 -->
あなたは、1回の改善の全記録を読んでいる。元のスキル、それに対して提案された編集、編集したスキルが生んだ実行、最後にどの成果物が選ばれたか。この領域の後の仕事が自分の編集をする前に読むライブラリのために、2つのことを書く。

# 仕事

${work}

# 選ばれた候補だけが証拠ではない

選択はスキルを伏せたまま成果物を比べた。だから選択は、どの出力が最もよく読めたかを示すだけで、どの編集が効いたかは示さない。すべての候補を証拠として扱う。選ばれなかった候補にだけあった編集が、振る舞いをよい方へ変えたものかもしれない。選ばれた候補の中の編集が、選ばれた理由に何も寄与していないかもしれない。判定ではなく軌跡を読む。

# 各編集がしたこと

すべての候補のスキルを `context/base_harness/` と比べる。どれかの候補が変えた部品ごとに、1組の行を書く。部品、編集が実際に変えたこと、それが生んだ実行の観察された違い、判定。

判定は `helped`、`hurt`、`no observed effect`、`confounded` のどれかである。候補が一度に複数の部品を変え、どの実行もそのうち1つを切り分けていないとき、または違いを支えるのが1回の実行だけのときは `confounded` を使い、それを優先する。confounded の行は役に立つ記録である。でっち上げた帰属は、後のすべての仕事のためのライブラリを汚す。振る舞いが分かれた実行と軌跡の場面を挙げる。2つの候補が同じ部品を違うやり方で変えたなら、試した形と、それぞれが生んだものを書く。

# 移せる教訓は1つだけ

次に、残る項目を多くても1つ書く。編集の行が支えるときだけ書く。

`cue` は、その教訓が当てはまる状況の形を書き、別の案件でも働くようにする。この依頼の事実ではなく、型を書く。`lesson` はスキルに対して行う操作であり、当てはめて確かめられるように書き、それが関わる部品を名指しする。

一般的すぎると役に立たず（「徹底する」）、具体的すぎると二度と働かない（「1月1日から手数料は250に上がった」）。その間を狙う。例：「1つの文書が順に複数の行為を行い、そのうち1つが行為者自身の権限を終わらせるなら、終わらせる行為を最後に置く」。

`evidence` は、教訓が拠って立つ編集の行を挙げる。`confounded` の行だけに拠る教訓は推測である。記録が示すことまで狭めるか、書かない。採用されたことだけでは、編集が効いたことも、移せることも示さない。記録に具体的で使い回せる実行の対比が無いなら、experience の区画の代わりに NO_ENTRY の1行だけを書く。編集の行はそれでも書く価値がある。

${block_answer_free}

${block_evidence_boundary}

# 出力の形

<edits>
component: <木の中に現れるパス>
candidates: <この編集を持っていたラベル>
change: <編集がしたこと>
observed: <実行の違いと、それを見た場所>
verdict: <helped|hurt|no observed effect|confounded>
（変えた部品ごとに、この5行を繰り返す）
</edits>

<experience>
cue: <これが当てはまる状況の形>
lesson: <移せる操作。部品を名指しする>
evidence: <拠って立つ編集の行と、実行の対比>
confidence: <high|medium|low と、その理由>
</experience>

# 起きたこと

スキル ${chosen} が選ばれた。選択の理由は次のとおりである。

${why}

`context/adoption.json` は、その理由の中の匿名の ID を実行のラベルに対応づける。`context/harness/` を `context/base_harness/` と比べ、`context/pool/` の候補とも比べる。書く前に、決定（`context/decisions/`）と実行の対比を読む。

${layout}

${block_layout_legend}
