# Claude / Codex の行動ログとHTML分析

Claude CodeとCodexのhooksで「何をしたか・なぜしたか・どうなったか」をJSONLへ記録し、行動分析HTMLを作る再利用パターンです。操作対象・コマンド・短い目的・結果抜粋を保存します。目的は明示された説明を使い、未記録なら推測で埋めません。プロンプト・会話履歴・Read/Write/Editのファイル本文は保存しません。

まず[合成ログのHTML見本](examples/demo.html)を開くと、認証不具合の調査・再現・修正・再テストをたどれます。42イベント・12操作・2セッションの見本で、実測ログではありません。

## 利用先へ導入する

macOS/Linuxのローカル実行が対象です。Python標準ライブラリだけで動作します。保守対象のPythonを利用してください。この作業環境での契約検証はPython 3.9.6、Claude Code 2.1.308、Codex 0.162.0-alpha.17.2の仕様に基づきます。

このパターン自身の`.claude/settings.json`と`.codex/hooks.json`にも、行動記録hookを接続しています。このディレクトリをプロジェクトとして開いて利用します。`make hooks`は既存の正本スキルを使って設定を再生成するコマンドです。絶対パスを含むため、コピー・移動後は古い行動記録handlerを除いてから`make hooks`を実行してください。再起動とCodexの`/hooks`での信頼が必要です。

このディレクトリで次を実行します。`/absolute/path/to/project`は導入先へ置き換えます。

```bash
# 変更予定を表示
python3 .claude/skills/agent-behavior-html/scripts/install.py --project /absolute/path/to/project
# 両製品のhooksとスキルを導入
python3 .claude/skills/agent-behavior-html/scripts/install.py --project /absolute/path/to/project --apply
```

片方だけなら`--providers claude`または`--providers codex`を追加します。既存の設定とhooksは維持し、変更前のファイルを`.agent-observer/backups/`へ退避します。導入後にエージェントを再起動します。Codexでは`/hooks`から内容を確認し信頼してください。

導入先のClaudeでは`/agent-behavior-html`、Codexでは`$agent-behavior-html`で利用できます。「このプロジェクトの行動ログをHTMLで分析して」と依頼しても利用できます。グローバル設定の変更は不要です。

操作の目的は、Bashなどのdescriptionに書きます。説明欄がない操作については、開始hookが案内する`record.py --intent`へ短い目的・期待結果・次の操作の入力を渡します。hookは実際の操作と結果を記録し、分析器が同一セッション・同一入力へ対応付けます。詳しくは[目的を記録する手順](.claude/skills/agent-behavior-html/SKILL.md#操作の目的を記録する)を参照してください。

## ログからHTMLを作る

導入先で短い操作を行い、`.agent-logs/`へ記録された後に実行します。

```bash
python3 /absolute/path/to/project/.agent-observer/agent-behavior-html/scripts/analyze.py \
  /absolute/path/to/project/.agent-logs \
  --output /absolute/path/to/project/reports/agent-behavior.html
```

HTMLと同名のJSONができます。HTMLには操作・目的・出所・期待結果・観測結果を並べたカードと、全操作の表を表示します。製品・セッション・ツール・成否の絞り込み、目的や結果の検索、同じ入力の繰り返し、欠落と根拠の確認ができます。外部通信はありません。旧v1ログも読めます。

所要時間は前後hook受信時刻の差です。成否が分からない記録はcompletedとし、失敗率の分母から除きます。ツールIDなしのイベントは推測で結合しません。これらの違いと分母は[指標定義](.claude/skills/agent-behavior-html/references/metrics.md)にあります。

## パターンを変更する

このディレクトリでClaude CodeまたはCodexを起動します。AGENTS.mdが実装・レビュー用スキルへ案内します。開発検査にはPythonとNode.jsが必要です。

```bash
make check
make demo
make probes
python3 .foundation/bin/rules_check.py --root . --final
```

`make fix`は行末空白・改行・JSONを整えます。PythonのAST・字下げ・依存境界とJavaScript構文を別に検査します。静的型チェッカーを使わず、型注釈とログ境界の実行時検証を組み合わせています。

利用手順は[配布スキル](.claude/skills/agent-behavior-html/SKILL.md)、全体設計は[設計の入口](docs/design/overview.md)、検証範囲は[収束試験の記録](docs/design/convergence-report.md)を参照してください。

## 観測範囲

内部の推論、料金、トークン数、フックが発火しない操作は復元しません。Codexのホスト側ツール、一部の特殊経路、クラウド、Windowsはこのパターンの動作確認対象外です。ローカルhookが信頼されていることと、実際にログが増えることを導入先で確認してください。

ログの自動削除は行いません。利用者が日付ファイル単位で保管期間を決めます。停止・更新・バックアップからの復元は[接続の説明](.claude/skills/agent-behavior-html/references/integration.md)にあります。
