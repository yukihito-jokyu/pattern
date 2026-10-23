# 検査の種類

<!-- 生成物。scripts/gen_docs.py が checks.KINDS から作る。手で編集せず make docs で作り直す -->

検査の `kind` に書ける種類の一覧である。どの種類にも `id`、`kind`、`severity` が要る。

| kind | 判定 | 必須の項目 | 書いてよい項目 | 合格の条件 | 正解の使い方 |
|---|---|---|---|---|---|
| `contains` | 機械 | `value` | `target` | 対象の文字列に value が含まれる（NFKC で正規化し、空白の並びを1つにして比べる） | 使わない |
| `not_contains` | 機械 | `value` | `target` | 対象の文字列に value が含まれない（比べ方は contains と同じ） | 使わない |
| `regex` | 機械 | `pattern` | `target` | 対象の文字列のどこかが正規表現 pattern に一致する（Python の re.search、複数行モード） | 使わない |
| `equals` | 機械 | — | `target`, `value`, `expected_file` | 対象の文字列が正解と一致する（NFKC で正規化し、行末の空白と前後の空行を除いて比べる） | value、expected_file、ケースの expected の順に、最初にあるものを正解にする |
| `json_equals` | 機械 | — | `target`, `value`, `expected_file` | 対象の文字列と正解を JSON として読み、値が等しい（キーの順と空白は問わない） | equals と同じ |
| `exists` | 機械 | `target` | — | target に書いたファイル（file:<sandbox からの相対パス>）がある | 使わない |
| `command` | 機械 | `run` | — | sandbox でシェルのコマンド run を実行し、終了コードが 0 になる（300秒で打ち切り） | 使わない |
| `judge` | 採点役 | `criterion` | `use_expected` | 採点役が criterion の文を満たすかを判定する。2人の採点役が同じ判定をできる1文で書く | use_expected が true なら、ケースの expected と expected/ のファイルを採点役に見せる |

## 例

- `contains`: `{"id": "K1", "kind": "contains", "severity": "must", "value": "2026-01-05"}`
- `not_contains`: `{"id": "K2", "kind": "not_contains", "severity": "must", "value": "TODO"}`
- `regex`: `{"id": "K3", "kind": "regex", "severity": "should", "pattern": "^## 概要$"}`
- `equals`: `{"id": "K4", "kind": "equals", "severity": "must", "target": "file:out/result.txt"}`
- `json_equals`: `{"id": "K5", "kind": "json_equals", "severity": "must", "target": "file:out/data.json"}`
- `exists`: `{"id": "K6", "kind": "exists", "severity": "must", "target": "file:docs/summary.md"}`
- `command`: `{"id": "K7", "kind": "command", "severity": "must", "run": "python3 -m unittest"}`
- `judge`: `{"id": "Q1", "kind": "judge", "severity": "must", "criterion": "依頼の日付を全部変換している"}`
