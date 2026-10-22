<!-- 生成物。scripts/gen_docs.py が profile.py の FIELDS と既定値から作る。手で編集しない（make docs で作り直す） -->

# プロファイルの項目

`.autoflow/profile.json` の項目である。形の版は `schema_version` で、今は 1 である。glob の `*` は `/` もまたぎ、`**/` で始まる glob はルートの直下のファイルにも当たる。

| 項目 | 型 | 意味 |
|---|---|---|
| `schema_version` | 整数 | プロファイルの形の版。今は 1 |
| `verify.commands[].id` | 文字列 | 検査の名前（kebab-case）。証拠のログのファイル名になる |
| `verify.commands[].run` | 文字列 | リポジトリのルートで実行するシェルのコマンド。CI=1 を付けて実行する |
| `verify.commands[].timeout_sec` | 整数 | 時間の上限（秒、1〜3600） |
| `paths.tests` | glob の配列 | テストのファイル。不具合の修正で、最初に再現のテストだけを書く範囲 |
| `risk.always_human` | glob の配列 | 常に人が差分を読むパス。計画で触ると H1、変更に含むと H3 で全文を読む |
| `risk.high` | glob の配列 | 変更に含むとリスクの段を high にするパス |
| `risk.low` | glob の配列 | 変更がこれとテストだけなら、リスクの段を low にするパス |
| `review.guide_files` | パスの配列 | 探索役と検証役に渡すレビューの指示（開始時の版を写す） |
| `review.skip` | glob の配列 | レビューで指摘しないパス（生成物、lockfile） |
| `limits.fix_attempts` | 整数 | 検査の失敗がこの回数続いたら H2 |
| `limits.review_rounds` | 整数 | Important が残るレビューがこの回数続いたら H2 |
| `limits.max_scope_files` | 整数 | 計画の範囲がこのファイル数を超えたら H1 |
| `limits.large_diff_lines` | 整数 | 差分の行数がこれを超えたら、リスクの段を少なくとも medium にする |
| `limits.huge_diff_lines` | 整数 | 差分の行数がこれを超えたら、リスクの段を high にする |
| `commit.trailers` | 文字列の配列 | コミットの文の最後に足す行（Co-Authored-By など） |

## 既定値

setup-new は、検出した検査コマンドとレビューの指示のファイルを、次の既定値に足す。

```text
{
  "schema_version": 1,
  "verify": {
    "commands": []
  },
  "paths": {
    "tests": [
      "tests/**",
      "test/**",
      "**/__tests__/**",
      "**/*_test.go",
      "**/*.test.*",
      "**/*.spec.*",
      "**/test_*.py"
    ]
  },
  "risk": {
    "always_human": [
      ".github/workflows/**",
      ".gitlab-ci.yml",
      ".circleci/**",
      "Jenkinsfile",
      "**/auth/**",
      "**/billing/**",
      "**/payment*/**",
      "**/migrations/**",
      "**/.env*",
      "**/*secret*",
      "**/*.pem",
      "**/*.key",
      ".autoflow/**",
      ".claude/**",
      "**/CLAUDE.md",
      "**/AGENTS.md",
      "**/REVIEW.md"
    ],
    "high": [
      "**/package.json",
      "**/package-lock.json",
      "**/pnpm-lock.yaml",
      "**/yarn.lock",
      "**/go.mod",
      "**/go.sum",
      "**/pyproject.toml",
      "**/requirements*.txt",
      "**/poetry.lock",
      "**/uv.lock",
      "**/Cargo.toml",
      "**/Cargo.lock",
      "**/Gemfile*",
      "**/Dockerfile*",
      "**/docker-compose*.yml",
      "**/*.tf"
    ],
    "low": [
      "docs/**",
      "**/*.md"
    ]
  },
  "review": {
    "guide_files": [],
    "skip": [
      "**/*.lock",
      "**/package-lock.json",
      "**/pnpm-lock.yaml",
      "**/dist/**",
      "**/vendor/**",
      "**/*.min.js"
    ]
  },
  "limits": {
    "fix_attempts": 3,
    "review_rounds": 3,
    "max_scope_files": 20,
    "large_diff_lines": 400,
    "huge_diff_lines": 1000
  },
  "commit": {
    "trailers": []
  }
}
```
