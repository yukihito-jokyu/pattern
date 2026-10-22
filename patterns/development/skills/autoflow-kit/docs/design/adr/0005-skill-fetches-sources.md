# 0005 依頼の本文はスキルが取り、補助 CLI はネットワークに触れない

- 状態：採用
- 関係するルール：OPS-02、DEP-03

## 背景

入力元は文章、Backlog の課題、Redmine のチケット、GitLab・GitHub の Issue である。Backlog と Redmine はこの環境では MCP のツールで取れ、GitLab と GitHub は glab・gh で取れる（[research.md](../research.md) の「課題の取得元」）。MCP のツールは Python から呼べない。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 補助 CLI が glab・gh を呼び、MCP の分はスキルが取る | GitLab・GitHub は決まった形で取れる | 取得の経路が2つになり、認証の失敗の扱いが CLI とスキルに分かれる |
| 全部スキルが取り、本文をファイルに書いて `start --body-file` に渡す | 経路が1つ。CLI はネットワークと認証に触れない | 取り方はスキルの表（`references/sources.md`）に頼る |

## 決定

2つ目を採る。スキルは取得元の表で本文とコメントを取り、`.autoflow/runs/intake.md` に書き、`start --source <種類> --ref <番号> --url <URL> --title <題名> --body-file .autoflow/runs/intake.md` を実行する。取得元の種類は `layout.SOURCES` の表で決める。

## 理由

補助 CLI をネットワークから切り離すと、テストが本物の git とファイルだけで書ける（TEST-02）。

## 影響

取得元を足すときは、`layout.SOURCES` と `sources.md` の表を一緒に変える（PROC-02）。ref はコミットの件名の先頭に付ける値になる（リポジトリの履歴が課題の番号で始まる書き方のとき）。
