<!-- 生成物。scripts/gen_docs.py が bundle.py の RULES から作る。手で編集しない（make docs で作り直す） -->

# バンドルの決まり

バンドルとは、対象のスキル（`skills/<スキル名>/`）と、そのサブエージェント（`agents/<スキル名>-<役>.md`）の組である。下書き・候補・リポジトリの `.claude/` のバンドルは、全部の決まりを満たす。補助 CLI の `bundle-check`、`prepare`、`propose` がこの決まりで検査し、満たさないと先へ進まない。

| id | 決まり |
|---|---|
| B01 | スキルは `skills/<スキル名>/SKILL.md` に置き、frontmatter の `name` をスキル名と同じにする。 |
| B02 | frontmatter に `description` を1行で書き、`description` と `when_to_use` の合計を 1536 文字以内にする。 |
| B03 | frontmatter に `disable-model-invocation: true` を書き、`context` を書かない（人が `/<スキル名>` で呼び、メインのセッションで動かす）。 |
| B04 | SKILL.md は 500 行以内にする。SKILL.md 以外のファイルは `references/<ファイル>` の1階層に置き、全部を SKILL.md から `[…](references/<ファイル>)` で参照する。 |
| B05 | SKILL.md に `## 役割`、`## 手順`、`## 人に確かめること`、`## 報告`、`## してはいけないこと` をこの順に置く。`## 手順` は番号付きの一覧で 2〜12 項目にする。`## 人に確かめること` の各項目（`- ` の行）に、人が答えられないときの答えを `既定:` で書く。無ければ `- なし` と書く。 |
| B06 | サブエージェントは `agents/<スキル名>-<役>.md` に 1〜6 個置く。役は kebab-case にし、frontmatter の `name` を `<スキル名>-<役>` にする。 |
| B07 | サブエージェントの frontmatter のキーは `name`, `description`, `tools`, `model`, `effort`, `maxTurns`, `omitClaudeMd`, `color` だけにし、`description` と `tools` を必ず書く（`permissionMode` で権限を広げない）。 |
| B08 | サブエージェントの `tools` は `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash` の中から列挙する（`Agent` を入れないので、サブエージェントはさらにサブエージェントを起動しない）。 |
| B09 | SKILL.md の本文に、全サブエージェントの名前（`<スキル名>-<役>`）を書き、バンドルに無い `<スキル名>-` の名前を書かない。 |
| B10 | `TODO(forge)` を残さない。 |
| B11 | 構築のときは、サブエージェントの役と `tools` を、承認した設計（design.json の roles）と同じにする。 |
| B12 | 評価課題の文（課題文と受け入れ条件の、20 字以上の行）をそのまま写さない。 |
| B13 | スキルのファイルに `Glob`・`Grep` を書かず、ファイルは Bash の `find`・`grep` で探すと書く。`Bash` を持つサブエージェントの `tools` と本文にも `Glob`・`Grep` を書かない（macOS・Linux では、Bash のあるセッションに Glob・Grep が無い）。 |
