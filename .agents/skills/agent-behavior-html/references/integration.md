# Claude / Codexへの接続

確認日: 2026-10-23。詳細は[Claude Codeのhooks](https://code.claude.com/docs/en/hooks)と[Codexのhooks](https://learn.chatgpt.com/docs/hooks)を参照する。

| 項目 | Claude Code | Codex |
|---|---|---|
| 設定先 | .claude/settings.json | .codex/hooks.json |
| スキル入口 | .claude/skills/agent-behavior-html | .agents/skills/agent-behavior-html |
| 主な記録 | SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、PermissionRequest、SubagentStart、SubagentStop、PreCompact、PostCompact、Stop、SessionEnd | 左と同じ共通イベント |
| 固有記録 | PostToolUseFailure、Notification | Interrupt |
| stdin | 製品のhook JSON | 製品のhook JSON |
| 正常時の出力 | 記録はstdoutなし・exit0。UserPromptSubmit/SubagentStartはJSONのadditionalContext | 左と同じ |

Codexではプロジェクト層とhook定義の信頼が必要である。`/hooks`で内容を確認して信頼する。定義を変更すると再レビューになる。管理者がhooksを無効化している場合はこの設定で上書きしない。導入処理はconfig.tomlを書き換えず、自動trustを行わない。

v2はUserPromptSubmit/SubagentStartのコマンドに`--context`を付け、session_id・turn_id・agent_idと目的記録の手順をモデルへ渡す。`--intent`で書くActionIntentは内部の申告イベントであり、製品のhooks設定へ追加しない。Bash等のdescriptionは任意なので、目的の記録を全操作について保証しない。HTMLは未記録・対応不明も表示する。製品のtranscriptを解析して理由を作る処理は持たない。

導入先には共通の`.agent-observer/agent-behavior-html/`をコピーし、両製品の入口をそこへの相対リンクにする。コマンドはPythonとスクリプトとログ先を絶対パスにしてshell quoteする。エージェントのcwdがサブディレクトリへ移っても記録先は変わらない。プロジェクトを移動した場合は絶対パスが古くなるため、古い観測hookを除いてから移動先で導入する。

パターンのソースプロジェクトは`--in-place`で既存の`.claude/skills/agent-behavior-html/`を直接使う。`make hooks`がこの設定を生成する。`.claude/settings.json`と`.codex/hooks.json`から呼ばれるcollectorが存在し、対応する全イベントへ接続されていることをqualityと契約テストで検査する。設定から起動したコマンドへ合成stdinを渡す検査と、製品の実セッションでhookが発火する検査は区別する。

既存のsettingsの別キーとhook配列は維持する。変更前の設定と.gitignoreを`.agent-observer/backups/<ID>/`へ保存する。再実行は同じコマンドを重複追加しない。同名の別スキルがある場合と配布スキルに差分がある場合は上書きせず停止する。更新時は変更を退避し、古い観測hookとスキル入口を除いてから導入する。稼働中のスキルを上書きする自動更新は持たない。

停止する場合は、該当製品のhooks設定からこのスキルの`record.py --source ...`を呼ぶhandlerだけを削除し、製品を再起動する。元の設定を復元する場合は、バックアップ以後に加えた別変更が無いか確認してから行う。ログは自動削除しない。日付入りのファイル単位で利用者が保管期間を決める。鍵は既存ログの分析には不要だが、新旧の入力指紋の比較には同じ鍵が必要になる。

対応範囲はmacOS/Linuxのローカル実行。Windowsはfcntlとshellの違いがあるため対象外。Codexのホスト側ツールや一部の特殊実行経路にはツールhookが発火しない。クラウド実行のローカルcommand hookを保証しない。プロンプト送信とStopは観測できても、途中の全操作・実行結果の成否が分かるとは限らない。

記録は監査の完全性を証明するものではない。書き込み失敗、入力上限超過、0.5秒のロック待ち超過では、固定のstderrとexit0で本来の実行を続ける。この場合はログ自体に失敗を残せず、前後欠落にも現れないことがある。導入後は実際の短い操作を1件行い、`.agent-logs/*.jsonl`が増えることを確認する。
