# 0008 方法のモジュールから事後の検査の記録を機械で遮る

- 状態：採用
- 関係するルール：STATE-04

## 背景

harness2 は、採点（judge）を選択が確定した後だけに動かし、方法のどのモジュールも judge を import しない。この基盤も同じ形にし、STATE-04 で `judging` を方法のモジュールから import できないようにし、`checks.json` に触れるモジュールを `judging` と `planning` に限った。

ところが、事後の検査の結果を書いたファイル（`judged.json`）は、`Layout.judged_path` と `layout.JUDGED_FILE` を通せばどのモジュールからでも読めた。収束テストのラウンド1で「show に judge の結果を出す」課題を解いた独立エージェント3人のうち2人が、この穴を指摘した。show のために `workspace` に読み込みの関数を足すと、方法のモジュール（`recursion` など）もその関数を呼べるようになる。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 許す側の表（`METHOD_LIMITS`）に `judged_path` を足し、読んでよいモジュールを列挙する | 今の `checks_path` と同じ書き方 | 読み込みの関数の名前が決まる前に表を書けない。`results` に表示を足すたびに保護ファイルの変更が要る |
| 方法のモジュールを列挙し、名前に `judg` を含む属性の参照を落とす | 読み込みの関数がどんな名前でも、`judg` を含めば落ちる。表示の側（`results`）に足すときは保護ファイルを変えずに済む | `judg` を含まない名前の関数で包めば抜けられる（レビューで確かめる） |
| 文書だけで禁じる | 何も変えない | harness2 が機械で守っている性質を、この基盤では読み飛ばせる |

## 決定

2つ目を採る。`scripts/structure_check.py` に方法のモジュールの表（`METHOD_MODULES`）を置き、そこに入るモジュールが名前に `judg` を含む属性（`judged_path`、`JUDGED_FILE`、`load_judged` など）を参照したら STATE-04 で落とす。方法のモジュールは `execution`、`recursion`、`selection`、`reflection`、`context`、`rollout`、`library`、`prompts`、`runner`、`sandbox` である。

あわせて、`judged.json` の配列を包むキー `results` を `WRAPPER_KEYS` に登録する。`judged.json` は `judging` が既に書いているファイルで、その包むキーが登録から漏れていたため、読み込みを足した独立エージェントが全員、保護ファイルの前で止まった。

## 理由

harness2 の「方法は答えを見ない」は、文ではなく構造で守られている（research.md の「正解に合わせた改善を防ぐ」）。この基盤でも、事後の検査の記録への道を構造で断つ。名前の部分一致にしたのは、これから足される読み込みの関数の名前を先に決められないからである。

## 影響

- 表示の側（`results`、`judging`、`workspace`）は、`judged.json` を自由に読める
- 方法のモジュールを足したら `METHOD_MODULES` にも足す（保護ファイルの変更なので、承認を得て行う）
- probe STATE-04-c が、`recursion.py` から `judged_path` を参照すると構造検査が落ちることを確かめる
