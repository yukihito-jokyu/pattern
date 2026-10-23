# 0004 検査の道具を uv のスクリプトの依存1つにまとめ、YAML の formatter を使わない

- 状態：採用
- 関係するルール：TOOL-01、TOOL-05、KIT-06

## 背景

ワークフローの検査には、actionlint（Go）、shellcheck（Haskell）、zizmor（Rust）、yamllint（Python）を使う。配布先で同じ版を同じ設定で動かせないと、同じワークフローへの指摘が作者ごとに変わる。また、YAML の形をどう揃えるか（formatter か lint か）を決める必要があった。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 各道具の公式のインストール方法（Homebrew、バイナリのダウンロード） | 各道具の推奨どおり | 配布先ごとに版がずれる。インストールの手順が4通りになる |
| pre-commit | 版を固定できる | 依存が1つ増え、検査の出力の形を揃えられない |
| uv の PEP 723 スクリプトの依存（PyPI の actionlint-py、shellcheck-py、zizmor、yamllint）とロックファイル | `uv run --locked --script .gha/gha.py` の1コマンドで版が固定される。出力を1つの形（`<ルールID> <パス>:<行> <説明>`）に揃えられる | actionlint-py はインストール時に GitHub からバイナリを取るので、初回だけネットワークが要る |
| YAML の formatter（prettier、yamlfmt） | 自動で直る | コメントと引用の扱いが道具ごとに違い、`@sha # v1` の形を崩すものがある。依存が増える |

## 決定

検査の道具は `.gha/gha.py` の PEP 723 の依存に宣言し、`.gha/gha.py.lock` で固定する。YAML は formatter を使わず、yamllint の厳格な設定（`.gha/yamllint.yml`）で形を1つにする。

## 理由

uv のスクリプトなら、配布先に必要なのは uv だけになり、版はロックファイルが決める。`--locked` は宣言とロックが食い違うと起動しないので、片方だけを変えた状態に気づける。YAML の形は lint で1つに決めれば、手で直すだけで同じ形になる。formatter を足すと、formatter の版と設定がまた揺れる。

## 影響

- 道具の版を上げるときは、`.gha/gha.py` の依存を変え、`uv lock --script .gha/gha.py` を回し、research.md と manifest の `tools` を直す
- PyYAML は `.gha/gha.py` とキットの開発の `pyproject.toml` の両方にある。版の一致を `scripts/structure_check.py` が見る（KIT-06）
- yamllint の指摘は手で直す。`make fix` は YAML を直さない
