# plan.json と cases.json の形

`.tune/targets/<target-id>/plan.json` と `.tune/targets/<target-id>/dataset/cases.json` の項目を説明する。`init` がひな形を作り、`check-plan` が検査する。形の版は `schema_version`（今は 1）で、版が違う計画は検査で落ちる。

## plan.json

```json
{
  "schema_version": 1,
  "target": {"id": "date-format", "skill_path": ".claude/skills/date-format"},
  "goal": "日付の表記を ISO 8601 にそろえる手順を、どんな文書でも抜けなく実行できる",
  "mode": "reference",
  "sandbox": "case",
  "split": {"seed": "skill-tune", "ratios": {"train": 0.6, "val": 0.2, "test": 0.2}},
  "checks": [
    {"id": "Q1", "kind": "judge", "severity": "should", "criterion": "変換しなかった日付があれば、その理由を返答に書いている"}
  ],
  "budget": {"runs_per_case": 1, "max_rounds": 3, "patience": 2, "parallel": 4}
}
```

| 項目 | 値 | 決め方 |
|---|---|---|
| `target.id` | `--target` と同じ ID | `init` が書く |
| `target.skill_path` | 対象スキルのディレクトリ（リポジトリのルートからの相対パス） | `init` が書く |
| `goal` | スキルが達成すべきことを1文で | 人と決める。学習役と監査役がこの文で判断する |
| `mode` | `reference` か `criteria` | 正解データがある・作れるなら `reference`、無ければ `criteria` |
| `sandbox` | `case` か `repo` | 依頼が空のディレクトリで足りるなら `case`。リポジトリのファイルを読む・変えるスキルなら `repo`（リポジトリの写しの中で実行する） |
| `split.seed` | 分割の種の文字列 | 既定のままにする。変えると分割が変わる |
| `split.ratios` | 学習用・検証用・テスト用の割合（合計 1、全部 0 より大きい） | 既定は 0.6 / 0.2 / 0.2 |
| `checks` | 全ケースに当てる検査の配列 | 検査の形は下の「検査」。`groups` を書くと、その group のケースだけに当てる |
| `budget.runs_per_case` | 1ケースを解く回数（1〜5） | 返答が揺れるスキルなら 2〜3 にする。回数に比例して起動回数が増える |
| `budget.max_rounds` | ラウンドの上限（1〜10） | 既定 3 |
| `budget.patience` | 続けて不採用ならやめる回数（1〜10、max_rounds 以下） | 既定 2 |
| `budget.parallel` | 一度に起動するサブエージェントの数（1〜10） | 既定 4 |

## cases.json

```json
{
  "cases": [
    {
      "id": "memo-slash",
      "group": "memo",
      "prompt": "files/memo.txt の日付を ISO 8601 にそろえてください",
      "expected": "2026-01-05 に打ち合わせ。次回は 2026-02-10。",
      "checks": [
        {"id": "K1", "kind": "equals", "severity": "must", "target": "file:memo.txt"}
      ],
      "note": "スラッシュ区切りの日付"
    }
  ]
}
```

| 項目 | 値 | 決め方 |
|---|---|---|
| `id` | 小文字の英数字とハイフン（64文字以内）。全ケースで重ならない | 内容が分かる短い名前 |
| `group` | ケースの種類の名前（省くと `default`） | 分割はグループごとに割合を保つ。似たケースを同じグループにする |
| `split` | 空か `train`・`val`・`test` | 省くと自動で分ける。特定のケースを必ずテスト用にしたいときだけ書く |
| `prompt` | 実行役に渡す依頼の文 | 利用者がスキルに頼むときの文で書く |
| `expected` | 正解の文字列か `null` | `reference` モードでは必須（正解がファイルだけなら空文字にして `files/<id>/expected/` に置く）。`criteria` モードでは `null` |
| `checks` | このケースだけに当てる検査の配列 | 計画の検査と ID を重ねない。`groups` は書けない |
| `note` | 人向けのメモ | 実行役と採点役には見せない |

ケースの入力ファイルは `dataset/files/<ケースの id>/input/` に置く。実行の前に作業場所（sandbox）の直下へ写る。正解のファイルは `dataset/files/<ケースの id>/expected/` に置き、検査の `expected_file` で名前を指す。

## 検査

| 項目 | 値 |
|---|---|
| `id` | 英字で始まる英数字・`_`・`-`（32文字以内）。1ケースに当たる検査の中で重ならない |
| `kind` | 検査の種類。一覧と必須の項目は [check-kinds.md](check-kinds.md) |
| `severity` | `must`（不合格ならケースが不合格）か `should`（検査の通過率にだけ数える） |
| `target` | `response`（返答。省いたときの既定）か `file:<sandbox からの相対パス>` |
| `groups` | 計画の検査だけ。当てる group の配列。省くと全ケース |

各ケースには、当たる検査のうち `must` が1つ以上要る。

## 計画を変えたとき

承認の後に plan.json か dataset/ を変えると、評価の段は止まる。`check-plan` から承認をやり直すと、内容が変わったケースの結果だけが古くなり、評価し直す。テスト用のケースが変わったことは承認の記録に残り、報告に載る。
