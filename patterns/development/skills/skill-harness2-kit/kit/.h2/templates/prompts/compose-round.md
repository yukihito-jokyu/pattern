<!--
Copyright 2026 Google LLC
Licensed under the Apache License, Version 2.0.
Source: google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335, harness2/core/prompts.py
Modified: Japanese translation and adaptation to Claude Code skills; attribution added for distribution.
Full license and notices: kit/claude/skills/skill-harness2/references/third-party-notices.md
Installed notices: .claude/skills/skill-harness2/references/third-party-notices.md
-->
<!-- harness2 core/prompts.py の compose_round() -->
あなたは、逐次の改善の流れで、${k} 段のうちの第 ${t} 段の版を合成している。

# 仕事

${work}

# あなたが持っているもの

元のスキルでの実行（共有の証拠で、段をまたいで変わらない）、この段の INV と DOM の候補とその実行、前のすべての段の候補・版・軌跡がある。前の段の版の実行は、この段での方針どおりの証拠である。それは、あなたが編集しているスキルが実際に何をするかを示す。

${first_round}

# あなたの仕事

${round_job}

次のどれも正当である。
- 段をまたいで合わせる。前の段で捨てた候補も、後の実行が支持するなら含めてよい
- 前の段の版をそのまま再現する。その状態が単に最もよく、後の段がそこから離れたなら
- この段の最もよい候補を採る
- KEEP_BASE

${block_keep_base}

ここでの KEEP_BASE は、`context/harness/` にある今の版を変えないことを意味し、元のスキルに戻すことではない。notes には、どの段の編集が残り、どれを捨てたか戻したかを書く。

${block_answer_free}

${block_evidence_boundary}

${block_surface}
