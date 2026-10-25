# 構造と変更の範囲

配布スキルのscriptsに収集・導入・分析をまとめます。スキル本体とassetsを同じディレクトリに持つことで、別プロジェクトへコピーしても分析できます。Claudeの.claude/skillsを正本、Codexの.agents/skillsを相対リンクにして、手順の複製を防ぎます。

データは「製品のstdin JSON → record → event_modelの正規化 → ローカルJSONL → analyze → 単体HTMLと根拠JSON」の順に流れます。installは製品設定へrecordの絶対パスを書き、cwdへの依存をなくします。

## 依存の許可表

| 呼び出す側 | 標準ライブラリ | event_model | record/install/analyze | HTML |
|---|---|---|---|---|
| event_model | 許可 | 自己import禁止 | 禁止 | 禁止 |
| record | 許可 | 許可 | 禁止 | 禁止 |
| install | 許可 | 許可 | 禁止 | パッケージとしてコピーのみ |
| analyze | 許可 | 許可 | 禁止 | assetsをデータとして読む |
| tests | 許可 | 許可 | 許可 | 出力の契約を確認 |
| scripts/demo | 許可 | 許可 | 禁止 | 生成はMakefile経由 |

AST検査はDEP-01、配置はSTR-01で強制します。HTMLのデータ表示はtextContentだけを使います。

## 公開面

| 公開面 | 契約 |
|---|---|
| record.py CLI | --source / --log-dir / --intent / --context、stdin JSON、終了0。開始context以外はstdout空 |
| install.py CLI | --project / --providers / --apply / --in-place、既定は変更予定表示 |
| analyze.py CLI | 入力JSONL群 / --output / --summary / --synthetic |
| event_model.py | SOURCE_EVENTS、normalize、validate_event、parse_time、script_jsonと定数 |
| HTML / JSON | report_version=2。events、calls、metrics、quality、locationsとpurpose_evidenceが根拠 |

内部Python関数はテストのためにimportできます。別製品の統合は公開CLIから行います。保存したv1のキーや意味を変更する場合はPROC-03の互換性手順が必要です。

v2ではrecord --intentの申告も同じJSONLへ追記する。analyzeのattach_purposesがscopeと入力指紋を照合し、次の1操作へ結ぶ。操作・目的・結果の追加とv1読み取り互換はADR 0002を参照。

## 変更シナリオ

| 変更 | 触るファイル | 理由 |
|---|---|---|
| 製品のhookを追加 | event_model、integration、tests、demo | 共通一覧から導入設定も作る |
| ログへメタデータを追加 | event_model、record、analyze、schema、tests、demo | 保存境界と読み取り境界を同期 |
| 新しい集計値 | analyze、dashboard、metrics、tests | 分母と画面を同期 |
| フィルター追加 | dashboard、metrics、UI検証 | 集計対象の意味を表示に合わせる |
| 導入先の設定形式を変更 | install、integration、tests | 既存設定の保持と再導入を検証 |
| 保存上限を変更 | event_model、schema、tests | 境界と説明を一致させる |
| 規則の変更 | ADR、rules、検査、build_probes、見本 | 検査の効力をprobeで証明 |

## コードで確認できる境界

[record.py 122行目](/Users/opm008761/Documents/project/practice/claude-codex-cli/.claude/skills/agent-behavior-html/scripts/record.py:122:1)のmain:

> print("observer: recording failed; event not saved", file=sys.stderr)

記録に失敗しても固定の診断を返し、例外本文を出さない境界です。

[event_model.py 130行目](/Users/opm008761/Documents/project/practice/claude-codex-cli/.claude/skills/agent-behavior-html/scripts/event_model.py:130:1)のoutcome:

> return "completed", None

成否の根拠が無い記録を、不明のまま残す境界です。実際の行番号付き根拠は利用時に対象ファイルから確認します。
