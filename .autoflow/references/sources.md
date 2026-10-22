# 取得元

依頼の取り方。補助 CLI はネットワークに触れないので、このスキルが取り、`.autoflow/runs/intake.md` に書いてから `start` に渡す。`--source` に書ける種類は、補助 CLI の `layout.SOURCES` と同じである。

| 種類（`--source`） | 引数の例 | 取り方 | `--ref` | `--url` |
|---|---|---|---|---|
| `text` | `$pattern-autoflow ログインの失敗回数を表示して` | 引数の文章をそのまま本文にし、1行目を題名にする | 省く | 省く |
| `backlog` | `$pattern-autoflow backlog PROJ-123` | Backlog の MCP の課題を取るツール（`get_issue`、引数 `issueKey`）と、コメントを取るツール（`get_issue_comments`）。サーバー名が違う環境では、同じ働きのツールを使う | 課題キー（`PROJ-123`） | 課題の URL（分かれば） |
| `redmine` | `$pattern-autoflow redmine 456` | Redmine の MCP のチケットを取るツール（`getIssue`、`include` に `journals`）。サーバー名が違う環境では、同じ働きのツールを使う | チケットの番号 | チケットの URL（分かれば） |
| `gitlab` | `$pattern-autoflow gitlab 78` | `glab issue view 78 --comments -F json` | Issue の番号 | `web_url` |
| `github` | `$pattern-autoflow github 90` | `gh issue view 90 --comments --json number,title,body,comments,url` | Issue の番号 | `url` |

## intake.md の書き方

```markdown
# <題名>

<本文をそのまま>

## コメント

- <書いた人>（<日時>）: <コメントをそのまま>
```

- 本文とコメントは要約しない。計画役が原文から読み取る
- 取れなかった（権限が無い、ツールが無い）ときは、エラーを人に見せて止まる。推測で本文を作らない
