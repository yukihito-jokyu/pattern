# Codex実セッションの検証

日付: 2026-10-24。結果: 実操作の記録は未確認。CLIの実起動と、Codex自身によるhooks設定の読み込みを確認した。

Codex 0.162.0-alpha.17.2はChatGPTへログイン済みで、既定モデルはgpt-6.1-sol。`codex exec --skip-git-repo-check --ephemeral --sandbox workspace-write --json`をこのプロジェクトで起動し、確認用文字列を出すPythonコマンドを1回実行するよう依頼した。サンドボックス内ではapp-server初期化が権限エラーになったため、許可を得て外側から再試行した。

実セッションは開始したが、モデル要求は`workspace routing discovery failed`で終了した。WebSocketとHTTPSの再試行後もexit 1となり、ツール実行へ進まなかった。公式の`codex doctor --json`も、ChatGPTのHTTP到達不可とDNSのlookup failedを報告した。認証と設定の読み込みは正常と報告されている。

モデル接続とは別に、Codexの公式app-server API `hooks/list`を読み取り専用で呼び出した。`.codex/hooks.json`の12件すべてが読み込まれ、enabled=true、設定エラー0件、警告0件だった。12件すべてtrustStatus=untrustedであり、実行には利用者による確認が必要である。信頼状態の変更や一時的な信頼チェックの迂回は行っていない。`.agent-logs`のJSONLは0件だった。

したがって、設定の認識までを実測済みとし、SessionStartやUserPromptSubmitを含むhook発火、ツール操作の前後、目的・結果の保存は実セッション未検証とする。以前の合成stdinによる契約テストとは区別する。

計測した値と実行引数は[検証結果](../../.foundation/codex-live-check.json)、Codex自身が返した一覧は[hooks/listの応答](../../.foundation/codex-native-hooks-read.json)に保存した。応答はこのプロジェクトのhooksに絞り、認証情報や会話履歴を保存していない。

再検証にはchatgpt.comへ接続できる環境が必要になる。その環境でこのディレクトリを作業先としてCodexを起動し、`/hooks`で12件のコマンドを確認して信頼する。その後、確認用コマンドを実行し、`.agent-logs`のPreToolUseとPostToolUseに同じtool_use_idが入り、操作・目的・観測結果がHTMLへ出ることを確認する。目的はdescriptionまたは開始hookが案内する明示的な申告で記録する。

信頼待ちのhookはスキップされる仕様と、ツールhookの対応範囲は[公式hooks仕様](https://learn.chatgpt.com/docs/hooks)を参照する。
