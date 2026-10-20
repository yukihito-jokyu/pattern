# design.json の形

design.json は、対象のオーケストレーションスキルの形（役・手順・人に確かめる場面・報告の項目）を書く JSON である。設計役が `.forge/targets/<target.id>/build/design.json` に書き、補助 CLI の `design-check` が検査する。キーは snake_case で、知らないキーは検査で落ちる。下の例は、テストで実際に検査を通している。

承認された設計から、補助 CLI が下書きの骨組みを書く。骨組みの形は次のとおりで、構築役が骨組みを埋める。

| 設計の項目 | 骨組みのどこになるか |
|---|---|
| `summary` | SKILL.md の frontmatter の `description` |
| `roles` | SKILL.md の `## 役割` の表と、役ごとのサブエージェント `agents/<スキル名>-<役>.md`（`tools` は役の `tools`） |
| `steps` | SKILL.md の `## 手順` の番号付きの一覧 |
| `checkpoints` | SKILL.md の `## 人に確かめること` の一覧（`既定:` の後に `default`） |
| `report` | SKILL.md の `## 報告` の一覧 |

## 項目の一覧

| キー | 形 | 決まり |
|---|---|---|
| `schema_version` | 整数 | `1` |
| `skill_name` | 文字列 | charter の `target.skill_name` と同じ |
| `summary` | 文字列 | スキルが何をするかの1行。改行を入れない |
| `roles[]` | `{role, purpose, tools, input, output}` | 1〜6個。`role` は kebab-case で重ねない。`tools` は `Read`、`Write`、`Edit`、`Glob`、`Grep`、`Bash` から1つ以上。`Bash` と `Glob`・`Grep` を一緒に入れない（macOS・Linux では、Bash のあるセッションに Glob・Grep が無い） |
| `roles[].input` | 文字列 | 起動するときにプロンプトで渡すもの |
| `roles[].output` | 文字列 | 返してもらう形（ファイルか、返答の形） |
| `steps[]` | `{id, actor, action, parallel}` | 2〜12個。`id` は `S1` から順に振る。`actor` は `orchestrator`（メインのセッション）か `roles` の `role` |
| `steps[].parallel` | 真偽値 | `true` の手順が続くとき、メインのセッションはそれらのサブエージェントを1つのメッセージで同時に起動する。互いの結果を使わない手順だけを `true` にする |
| `checkpoints[]` | `{step, question, default}` | 人に確かめる場面。`step` は `actor` が `orchestrator` の手順の id。`default` は人が答えられないときの答え。無ければ空の配列 |
| `report[]` | 文字列の配列 | 最後の返答に書く項目。1〜12個 |

- 全部の役が、どれかの手順の担い手になっている

## 例

```json
{
  "schema_version": 1,
  "skill_name": "dev-orch",
  "summary": "機能の追加の依頼を、調べる役・実装役・レビュー役に分けて進め、検査を通してから報告する",
  "roles": [
    {
      "role": "explorer",
      "purpose": "依頼に関わるファイルと、従うべき決まりを調べる",
      "tools": ["Read", "Glob", "Grep"],
      "input": "依頼の文",
      "output": "関わるファイルの一覧と、従う決まりの要約を返答で返す"
    },
    {
      "role": "implementer",
      "purpose": "調べた結果に沿って変更を加え、検査を通す",
      "tools": ["Read", "Write", "Edit", "Bash"],
      "input": "依頼の文、調べた結果、検査のコマンド",
      "output": "変えたファイルの一覧と、検査の結果の末尾を返答で返す"
    },
    {
      "role": "reviewer",
      "purpose": "変更が依頼と決まりを満たすかを確かめる",
      "tools": ["Read", "Bash"],
      "input": "依頼の文、変えたファイルの一覧",
      "output": "承認か差し戻しと、差し戻しの理由を返答で返す"
    }
  ],
  "steps": [
    {"id": "S1", "actor": "orchestrator", "action": "依頼を読み、あいまいな点を人に確かめる", "parallel": false},
    {"id": "S2", "actor": "explorer", "action": "関わるファイルと決まりを調べる", "parallel": false},
    {"id": "S3", "actor": "implementer", "action": "変更を加え、検査を通す", "parallel": false},
    {"id": "S4", "actor": "reviewer", "action": "変更を確かめる。差し戻しなら S3 に戻す（2回まで）", "parallel": false},
    {"id": "S5", "actor": "orchestrator", "action": "検査の結果とレビューの結果をまとめて報告する", "parallel": false}
  ],
  "checkpoints": [
    {"step": "S1", "question": "依頼から決まらない点（名前、置き場所）をどうするか", "default": "リポジトリの既存の書き方に合わせる"}
  ],
  "report": ["変えたファイルの一覧", "検査の結果", "レビューの結果", "人に確かめたいこと"]
}
```
