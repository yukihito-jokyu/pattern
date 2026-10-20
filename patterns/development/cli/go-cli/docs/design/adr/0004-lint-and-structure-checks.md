# 0004 golangci-lint の linter を広く有効にし、層の境界と命名の組は Go で書いた構造検査で縛る

- 状態：採用
- 関係するルール：TOOL-01、DEP-01〜DEP-05、STR-01〜STR-08、NAM-01〜NAM-06、CODE-01〜CODE-09、ERR-01〜ERR-04、TEST-01〜TEST-03

## 背景

ルールを機械で縛る（ADR 0001）には、Go のコードの書き方を判定する道具が要る。golangci-lint は多数の linter を1つの設定で動かせるが、次のことは表せない（[research.md「golangci-lint v2.15.0」](../research.md#golangci-lint-v2150formatter-と-linter)）。

- 「`internal/domain/task` から `internal/domain/note` を import しない」のような、同じ層の別のパッケージ同士の禁止（depguard はパスの一覧で許可・禁止を書くため、「同じ層で名詞が違う」という条件を書けない）
- ディレクトリごとのファイル名の組、`<verb>.go` の宣言の順、エンティティと保存形式とビューの項目の一致
- `docs/cli.md` がコードと一致していること

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| golangci-lint の既定（standard）だけ | 指摘が少なく導入が楽 | 書き方の揺れの多くが残る |
| golangci-lint の linter を広く有効にし、境界は depguard で書く | 道具が1つで済む | 同じ層の別の名詞の禁止を表せない。ファイル名の組や宣言の順は縛れない |
| golangci-lint の linter を広く有効にし、境界と組は Go で書いた構造検査（`tools/archcheck`）で縛る | 判定したいことをそのまま書ける。標準ライブラリの `go/parser` と `go/ast` だけで書け、外部の依存が要らない | 構造検査のコードを保守する必要がある |

## 決定

- golangci-lint は `linters.default: standard` に加え、揺れを1通りに決める linter を有効にする（一覧は `.golangci.yml`）。各 linter が実際に指摘を出すことは、試作のファイルと probe で確かめる
- `issues.uniq-by-line: false`、`max-issues-per-linter: 0`、`max-same-issues: 0` にし、1行に複数の違反があっても全部を出す
- forbidigo の禁止の説明は、ルールID（`DEP-05`、`OPS-01`、`ERR-01`、`ERR-04`）で始める
- 層の境界（DEP-01〜DEP-05）、配置と命名の組（STR、NAM）、項目の一致（PROC-02）などは `tools/archcheck` で縛る。違反は `<ルールID> <パス>:<行> <説明>` の形で出す
- `docs/cli.md` は `tools/clidoc` で生成し、`-check` で鮮度を確かめる（STR-07）

## 理由

lint で表せるものは lint に載せ、表せないものだけを構造検査に回すと、構造検査のコードを小さく保てる。構造検査を Go で書くのは、検査対象と同じ言語の構文木を標準ライブラリで正確に読めるからであり、外部の依存を足さずに済む（DEP-04）。

## 影響

- 楽になること：違反のほとんどが、ルールID付きのメッセージで `make check` に出る。作者はルールIDで rules.md を引けばよい
- 難しくなること：linter が多いため、参照実装を書くときに指摘への対応が増える。指摘を抑止コメントで黙らせることは TOOL-03 で禁じている
- 変えたくなったとき：PROC-04 の手順で、ADR、rules.md、`.golangci.yml` または `tools/archcheck`、probes.json、参照実装の順に変える
