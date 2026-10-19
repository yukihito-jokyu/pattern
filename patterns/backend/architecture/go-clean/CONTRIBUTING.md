# チームでの作業の流れ

このプロジェクトは、人が書いても AI が書いても同じ形のコードになることを目指している。そのため、ルールを 2 か所に置いている。

- 機械で止められるルールは `.golangci.yml` に置き、`make check` で止める
- 機械で止められないルールは `docs/` に書き、人と AI の両方が読んで守る

どちらに何があるかは [docs/lint-rules.html](docs/lint-rules.html) にまとめてある。以下では、この前提で毎日の作業をどう進めるかを順に書く。

## 1. 初回の準備

```sh
make tools                # golangci-lint と migrate を bin/ に固定バージョンで入れる
cp .env.example .env      # ポートが使用中なら DB_PORT / DATABASE_URL / APP_ADDR を変える
make db-up                # PostgreSQL を起動
make migrate-up           # テーブルを作る
make check                # build → vet → test → lint がすべて通ることを確かめる
```

VS Code を使う場合は、推奨拡張（Go と EditorConfig）を入れる。`.vscode/settings.json` により、保存時に次の 2 つが動く。

- `bin/` の golangci-lint で lint する（`make lint` と同じ設定）
- 同じ golangci-lint で整形する（`make fmt` と同じ設定）

グローバルに入っている golangci-lint や migrate は使わない。バージョンが違うと結果が変わるためである。

## 2. 機能を足す・直す

1. 何を足すかに応じて [docs/adding-a-feature.md](docs/adding-a-feature.md) の該当する章を開き、その手順に沿って書く
2. 書き方に迷ったら [docs/coding-rules.md](docs/coding-rules.md) を見る。新しいファイルは、既存の `user` 集約の同じ層のファイルをお手本にする
3. lint の整形の指摘は `make fmt` で直す。それ以外の指摘はコードを直す。**`.golangci.yml` を変えて指摘を黙らせない**
4. `make check` が通ったら、下の「レビューに出す前の確認」をしてからレビューに出す

AI エージェントに書かせる場合も同じ手順になる。

- Claude Code は `CLAUDE.md` を、それ以外のエージェントは `AGENTS.md` を最初に読む。どちらも同じルールを指している
- `.claude/settings.json` で、`make check` などの検証コマンドは確認なしで実行でき、グローバルの golangci-lint は実行できないように設定している
- 個人用の権限は `.claude/settings.local.json` に書く（git に含めない）
- 実装は `/go-clean-implement`、レビューは `/go-clean-review` のスキルで頼める（`.claude/skills/` にある。Claude Code 以外のエージェントには、その `SKILL.md` を読ませる）

## 3. コミット

コミットメッセージは `{チケット ID} {日本語の説明}` の形にする。

```
PROJ-123 注文の作成 API を追加
```

1 つのコミットには、1 つのチケットの変更だけを入れる。

## 4. レビューに出す前の確認

`AGENTS.md` の完了前チェックリストと同じ内容である。

- [ ] `make check` が通る
- [ ] ドメインエラーを足したら、`handler/error.go` の `errorMappings` に足した
- [ ] API を変えたら、`api/openapi.yaml` を更新した
- [ ] スキーマを変えたら、`db/migrations/` に up と down の両方を足した
- [ ] 集約を足したら、`.golangci.yml` に「他の集約は ID だけで参照する」のパターンと除外を足した

レビューする側は、lint が止めない項目（[docs/lint-rules.html](docs/lint-rules.html) の「lint にできないもの」）を重点的に見る。ファイルをまたぐ整合性（ドメインエラーと `errorMappings`、router.go と openapi.yaml、マイグレーションと domain の制約など）は、次の機械検査で確かめられる。

```sh
go -C .claude/skills/go-clean-review/checker run . -root "$PWD"
```

## 5. ルールを変える

ルールを変えたくなったら、まずチームで合意する。合意したら、同じ変更の中で次をそろえる。

| 変えるもの | 一緒に直すもの |
|---|---|
| lint のルール | `.golangci.yml`、`docs/lint-rules.html` |
| 書き方のルール | `docs/coding-rules.md`、必要なら `docs/adding-a-feature.md`、お手本の `user` 集約のコード |
| AI への指示 | `AGENTS.md`（`CLAUDE.md` は `AGENTS.md` を読み込むだけなので触らない） |

ルールとお手本のコードが食い違うと、AI はお手本のほうを真似する。ルールを変えたら、お手本のコードも同じ変更で直す。

## 6. ツールのバージョンを上げる

| ツール | 固定している場所 |
|---|---|
| Go | `go.mod` の `go` ディレクティブ |
| golangci-lint | `Makefile` の `GOLANGCI_LINT_VERSION` |
| golang-migrate | `Makefile` の `MIGRATE_VERSION` |

Go を上げるときは、golangci-lint がその Go 以上でビルドされていることを `bin/golangci-lint-<version> version` で確かめ、両方を同じ変更で上げる。上げたら全員が `make tools` を実行し直す。古いバージョンは `bin/` に残るが、使われないので消してよい。
