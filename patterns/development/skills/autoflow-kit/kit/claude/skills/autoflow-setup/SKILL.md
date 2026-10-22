---
name: autoflow-setup
description: リポジトリに autoflow のプロファイル（検査コマンド、常に人が見るパス、リスクのパス、上限）を作り、人の承認を記録する（H0）。リポジトリごとに1回と、プロファイルを変えたときに使う。人が /autoflow-setup で呼ぶ。
argument-hint: "[作り直すなら --force]"
disable-model-invocation: true
allowed-tools: Bash(python3 .autoflow/autoflow.py *)
---

# autoflow-setup

autoflow が自走するときの条件（どの検査が通れば証拠になるか、どのパスを常に人が見るか、何回で止まるか）を、人と決める。ここで決めた条件は、実行の開始時に写され、実行の途中では変わらない。

## 手順

1. `python3 .autoflow/autoflow.py setup-new` を実行する（引数に `--force` があれば付ける）。「既にあります」で落ちたら、`setup-check` へ進む
2. 案を整える。`.autoflow/profile.json` を Read で読み、次を確かめて Edit で直す。項目の意味と既定値は [references/profile-schema.md](references/profile-schema.md) にある
   - `verify.commands`：検査コマンドが実在するか（Makefile、package.json、CI の設定を Read で確かめる）。CI が回すテスト・lint・型検査・ビルドを入れる。ファイルを書き換えるコマンド（自動修正、整形）は入れない
   - `risk.always_human`：リポジトリに固有の繊細なパス（課金、認証、インフラ、公開の API の定義）を足す
   - `risk.high`・`risk.low`・`paths.tests`：リポジトリの構成に合わせる
   - `review.guide_files`：レビューの指示のファイル（REVIEW.md など）があれば入れる
3. `python3 .autoflow/autoflow.py setup-check` を実行する。`エラー:` なら直して、やり直す
4. 「人に確かめること」に従って承認を得る
5. 人の回答の原文で `python3 .autoflow/autoflow.py setup-approve --answer '<人の回答の原文>'` を実行する。検査コマンドを確認なしで実行してよいと人が答えたら `--allow` を付ける
6. 人に、`.autoflow/` と `.gitignore` の変更をコミットしてもらう。autoflow の `start` は、作業ツリーがきれいなときだけ動く

## 人に確かめること

H0（準備の承認）である。

1. setup-check の出力（検査コマンド、常に人が見るパス、上限）を人に示す。2で直した点と、その理由も示す
2. AskUserQuestion で「承認する」「直してほしいことを伝える」を選んでもらう。直してほしいことは補足の文章で受け取る
3. 同じ AskUserQuestion で、検査コマンドを確認なしで実行してよいか（`--allow`）も聞く
4. 「直してほしい」なら、2の手順で直して setup-check からやり直す

回答が無い・空・自動で閉じた質問は、承認にも選択にもしない。関所のファイルの場所を報告して止まる。

## してはいけないこと

- 人の承認の前に setup-approve を実行する
- 承認の後に profile.json を変える（変えたら、この手順をやり直す）
- 検査を通しやすくするために、検査コマンドを外す・緩める
