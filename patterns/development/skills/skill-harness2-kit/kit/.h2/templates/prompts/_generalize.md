<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の _TTS_GENERALIZE。採用したスキルは後の別の依頼でも動くため、adapt の GENERALIZE（この作業場所の事実を書き込む）ではなくこちらを写した（ADR 0005） -->
# 一般化し、暗記しない

このスキルは、この${domain_word}のほかの依頼にも使われる。選ばれれば、この${domain_word}のライブラリに入り、後の依頼はそれを手本として読む。人が採用すれば、利用者のスキルとして、これからの依頼すべてで動く。使い回せる手順を書く（「書き込む前に、すべての数値を正本の資料と照らし合わせる」）。この依頼に固有のこと（「1月1日から手数料は250に上がった」）は書かない。依頼に固有の発見は notes に書き、スキルには書かない。目の前の依頼だけに効く編集は、この${domain_word}のほかの依頼すべてで費用を払わせ、そこでは何も得ない。

`context/library/` には、この${domain_word}の前の依頼ごとに、そこで選ばれたスキルの木の全体と、選ばれた理由のメモがある。まず `INDEX.md` を読み、関係がありそうなものを開く。実績のある部品を、本当に合うときに使い回すか手直しするのはよいことだが、この依頼の問いを決めつけてはならない。それらのファイルは、あなたのスキルが動く場所には無い。使いたい部品は `context/harness/` に写す。使い回す部品が名指しするスクリプトや参照ファイルも一緒に写さないと、木は検証で捨てられる。前の依頼の部品が作業場所について述べていることは確かめ直す。そこでは事実でも、ここでは仮説である。
