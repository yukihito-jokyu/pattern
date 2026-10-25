# 調査記録

確認日: 2026-10-23、Asia/Tokyo。指定技術はClaude、Codex、HTMLです。周辺依存を追加せず、実行言語と保存形式は保守的な既定値にしました。

## Claude Code 2.1.308

- 確認方法：claude --version → 2.1.308 (Claude Code)
- 確認の状態：確認済み
- 公式の推奨：[Hooks reference](https://code.claude.com/docs/en/hooks)のstdin JSON、イベント一覧、exit0の挙動を確認。
- 採用するもの：プロジェクトsettings.json、tool_use_id、明示失敗のPostToolUseFailure（OPS-06）。
- 採用しないもの：Read/Write/Editの本文保存、transcript読み取り、権限判断の返却。操作・目的・結果のv2はADR 0002で更新。
- ツールにできないこと：hook未発火と隠れた推論の観測。

## Codex 0.162.0-alpha.17.2

- 確認方法：codex --version → codex-cli 0.162.0-alpha.17.2、codex features list → hooks stable true
- 確認の状態：確認済み
- 公式の推奨：[Hooks](https://learn.chatgpt.com/docs/hooks)、[Build skills](https://learn.chatgpt.com/docs/build-skills)。
- 採用するもの：.codex/hooks.json、.agents/skills、製品でのhook信頼。非構造化の結果はcompleted（OPS-06）。
- 採用しないもの：notifyだけの記録、自動trust、config.tomlの変更。
- ツールにできないこと：ホスト側や特殊な実行経路の完全観測。クラウドのローカルcommand hook保証。

## Python標準ライブラリ（検証3.9.6）

- 確認方法：python3 --version → Python 3.9.6
- 確認の状態：確認済み
- 公式の推奨：[fcntl](https://docs.python.org/3/library/fcntl.html)、[unittest](https://docs.python.org/3/library/unittest.html)、[ast](https://docs.python.org/3/library/ast.html)。
- 採用するもの：Unixロック、json、hmac、argparse、unittest、ASTとtabnanny。既設Pythonで検証し、3.9互換構文を維持（TOOL-04）。利用先では保守対象のPythonを選ぶ。
- 採用しないもの：外部パッケージ、グローバル導入、Python3.9の新規インストール。
- ツールにできないこと：静的な型整合性の証明。型注釈を構造検査し、保存境界でJSONの型とキー集合を実行時検証する。品質検査の範囲は空白・JSON整形・AST・字下げ・依存境界であり、汎用formatterや静的型チェッカーとは異なる。

## HTML Living Standard（2026-10-23取得） / Node.js 24.22.1

- 確認方法：node --version → v24.22.1、[script要素の仕様](https://html.spec.whatwg.org/multipage/scripting.html#the-script-element)を取得。
- 確認の状態：確認済み
- 公式の推奨：JSONのscript埋め込み制約、DOMによるテキスト表示。
- 採用するもの：インラインCSS/JS、application/json、textContent、CSP（OPS-04）。構文検査にnode --check。
- 採用しないもの：CDN、外部font、外部通信。
- ツールにできないこと：欠けたログと課金の復元。

## 独自品質検査 1.0.0

- 確認方法：python3 scripts/quality.py --help、make check。
- 確認の状態：確認済み
- 採用するもの：STR-01、DEP-01、NAM-01、CODE-01、TEST-01、TOOL-02、TOOL-04。標準APIに基づく構造検査。
- 採用しないもの：未導入の外部lintルール名。抑止はguardで禁止（TOOL-01）。
- ツールにできないこと：変更の意味の整合。PROC-02/03のレビューで補う。
