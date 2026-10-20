# charter の形

charter は `.forge/targets/<target.id>/charter.json` に置く JSON である。キーは snake_case で、知らないキーは検査で落ちる。下の例は、テストで実際に検査を通している。

## 目次

- 項目の一覧
- 項目どうしの決まり
- 例

## 項目の一覧

| キー | 形 | 決まり |
|---|---|---|
| `schema_version` | 整数 | `1` |
| `target.id` | 文字列 | kebab-case。`--target` に渡す値で、スキル名と同じにする |
| `target.skill_name` | 文字列 | 作る・直すスキルの名前。kebab-case で、`forge-` で始めない。サブエージェントは `<スキル名>-<役>` の名前になる |
| `purpose` | 文字列 | 人が書いた目的の文をそのまま入れる |
| `goals[]` | `{id, statement, metrics}` | `id` は `G<番号>`。`statement` は人が書いた文。`metrics` は結び付ける指標の id |
| `metrics[]` | `{id, threshold, priority, criterion?}` | `priority` は `must` か `should`。`criterion` は独自の指標 `custom_<番号>` だけに書く |
| `environment.check_command` | 文字列 | 評価用のコピーのルートで実行する検査。使わなければ空文字 |
| `environment.check_timeout_sec` | 整数 | 10〜7200 |
| `environment.protected_paths` | 文字列の配列 | 変えてはいけないパスの glob |
| `environment.skip_dirs` | 文字列の配列 | コピーで除く名前。`/` で始めるとルート直下だけ |
| `environment.link_dirs` | 文字列の配列 | コピーせずリンクにする名前 |
| `executor.model` | 文字列 | 実行役のモデル。空なら Claude Code の既定 |
| `executor.allowed_tools` | 文字列の配列 | 実行役に確認なしで許す道具（`Bash(make check)` の形）。ファイルの編集は既に許してある |
| `executor.max_budget_usd` | 数 | 1回の実行の費用の上限（ドル）。0 より大きく 100 以下 |
| `executor.timeout_sec` | 整数 | 1回の実行の時間の上限（秒）。60〜7200 |
| `executor.parallel` | 整数 | 同時に動かす実行役の数。1〜20 |
| `tasks[]` | `{id, prompt, acceptance}` | `id` は `T<番号>` か `H<番号>`（ホールドアウト）。`prompt` と `acceptance` は人が書いた文 |
| `budget.agents` | 整数 | 1課題あたりの実行の回数。1〜10 |
| `budget.max_rounds` | 整数 | 改善のラウンドの上限。1〜10 |
| `approval` | `null` か `{sha256, approved_on}` | `charter-approve` だけが書く。手で書かない |

## 項目どうしの決まり

| 条件 | 要るもの |
|---|---|
| いつも | `T<番号>` の課題が1件以上、`must` の指標が1件以上、全部の指標がどれかのゴールに結び付いている |
| `check_pass` を使う | `environment.check_command` |
| `protected_untouched` を使う | `environment.protected_paths` が1件以上 |
| `acceptance` を使う | 全部の課題に `acceptance` が1件以上 |
| `files_agreement` を使う | `budget.agents` が2以上 |

## 例

```json
{
  "schema_version": 1,
  "target": {"id": "dev-orch", "skill_name": "dev-orch"},
  "purpose": "機能の追加の依頼を、実装役とレビュー役のサブエージェントに分けて進め、検査を通してから報告するようにしたい",
  "goals": [
    {"id": "G1", "statement": "依頼を満たし、検査を通して終える", "metrics": ["check_pass", "acceptance", "completion"]},
    {"id": "G2", "statement": "実装はサブエージェントに任せ、決めた手順どおりに進める", "metrics": ["delegation", "flow_conformance"]},
    {"id": "G3", "statement": "検査の設定を変えずに、決まった形で報告する", "metrics": ["protected_untouched", "report_format"]},
    {"id": "G4", "statement": "1回の依頼の費用を抑える", "metrics": ["cost_usd"]}
  ],
  "metrics": [
    {"id": "check_pass", "threshold": 1.0, "priority": "must"},
    {"id": "acceptance", "threshold": 1.0, "priority": "must"},
    {"id": "completion", "threshold": 1.0, "priority": "must"},
    {"id": "delegation", "threshold": 0.8, "priority": "must"},
    {"id": "flow_conformance", "threshold": 0.9, "priority": "should"},
    {"id": "protected_untouched", "threshold": 1.0, "priority": "must"},
    {"id": "report_format", "threshold": 1.0, "priority": "should"},
    {"id": "cost_usd", "threshold": 2.0, "priority": "should"}
  ],
  "environment": {
    "check_command": "python3 check.py",
    "check_timeout_sec": 600,
    "protected_paths": ["check.py"],
    "skip_dirs": [],
    "link_dirs": []
  },
  "executor": {
    "model": "",
    "allowed_tools": ["Bash(python3 check.py)"],
    "max_budget_usd": 3.0,
    "timeout_sec": 1800,
    "parallel": 3
  },
  "tasks": [
    {
      "id": "T1",
      "prompt": "在庫から数を減らす関数を足して。在庫より多くは減らせないようにして",
      "acceptance": ["在庫より多く減らそうとすると例外になる", "新しい関数にテストが1件以上ある"]
    },
    {
      "id": "T2",
      "prompt": "在庫が一定の数より少ない商品の一覧を返す関数を足して",
      "acceptance": ["境目の数ちょうどの商品は一覧に入らない"]
    },
    {
      "id": "H1",
      "prompt": "商品の名前を変える関数を足して。空の名前にはできないようにして",
      "acceptance": ["空の名前を渡すと例外になる"]
    }
  ],
  "budget": {"agents": 3, "max_rounds": 3},
  "approval": null
}
```
