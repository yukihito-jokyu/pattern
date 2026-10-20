# 0003 検査ツールを Python 3.14 で書き、uv で起動する

- 状態：採用
- 関係するルール：TOOL-04、PROC-03

## 背景

`tools/clispec` は、作者が Go・Python・Node.js・Rust のどれで実装するかに関係なく、同じ結果を出す必要がある。手元の macOS の `python3` は 3.9.6（2025-10-31 に EOL）であり、それをそのまま使うと、人によって動く版が変わる（research.md「Python 3.14.8」）。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| OS の `python3` をそのまま使う | 準備が要らない | 版が人ごとに違い、macOS では EOL の 3.9 が動く |
| Go で書いて単一のバイナリにする | 版の問題が無い | 作者がツールを変えるたびにビルドが要り、基盤のスクリプト（`.foundation/bin/`、Python）と言語が分かれる |
| Python 3.14 を `.python-version` で固定し、uv で起動する | 版を1か所で固定でき、標準ライブラリだけで書ける | uv の導入が要る |

## 決定

`.python-version` に `3.14` を書き、`Makefile` の `PYTHON := uv run --no-project --quiet python` から起動する。`make check` の先頭の `version` ターゲットが、uv から起動したこと（環境変数 `UV`）と、版が `.python-version` と同じ系列であることを確かめる。

## 理由

- 3.15.0 は 2026-10-09 の公開で90日未満のため、1つ前の 3.14 系にした（research.md）
- 検査ツールは標準ライブラリだけで書くので、仮想環境と依存の一覧が要らない（`--no-project`）

## 影響

- 版を上げるときは PROC-03 の順（research.md → `.python-version` → `make check` と probe → この ADR に追記）で変える
- 記録：2026-10-20 に 3.14（手元 3.14.5、最新 3.14.8）、uv 0.11.14（最新 0.13.3）で確認した
