# 変更のパターン

## 1. 学習項目を追加する

見本はcourses/go/lessons/functions。profile.curriculumへ追加し、lessons/id/lesson.jsonとdeck一式を作る。先行dependsOnを明記し、title/goalを一致させる。
作る順は公式資料→profile→html-deck initと制作→lesson.json→注目target→check/build→sync-skill。
本文は前提→流れ→実行例→結果→練習へつなぐ。新しい項目の追加のためにruntimeを変えない。

教材データだけの追加・変更はprofile/lesson/deckを正本として変更する。READMEとAGENTSは操作・環境・構造の説明であり、データだけの変更では編集しない。現在の一覧と期待出力はprofileとlessonから生成する。検証済みの日付を新しい実行例へ流用せず、変更した例を実行した当日を本文とdeck.mdへ記録する。資料の確認日は本文を再取得した出典だけ更新する。

確認用の生成先はページがbuild/site、専用スキルがbuild/skillsである。node tools/learning.mjs sync-skill courses/go build/skillsを使い、保守作業の生成先に.claude/skillsや.agents/skillsを使わない。生成物も所有台帳も手編集しない。一時作業・スクリーンショット・検査ログはbuild/verificationへ置く。TMPDIRを指定するときは先にbuild/temporaryを作り、その絶対パスを使う。test-resultsはPlaywrightが初期化するため、TMPDIRや保持したい証跡を置かない。build/とtest-results/は差分・ZIPの正本から除く。

ブラウザ検査はprofileの全学習項目を自動で列挙する。学習追加のために検査の配列や基盤コードを変更する必要はない。course JSONもPrettierで整形し、最後にnpm run checkを実行する。

## 2. 本文・注目・資料を変更する

見本はcourses/go/profile.jsonとvariables/lesson.jsonとdeck/slides/01.html。
本文だけならlesson.json、注目対象変更ならslideとnotesの両方、対象版変更ならprofile.sourcesと全影響項目を変更する。コードの値と説明と期待出力の対応を確認する。資料の確認日を再取得なしに更新しない。

## 3. 共通機能を変更する

architectureの依存許可表に従いmodel→render→CLIまたは画面→テストの順に変更する。データ形式と公開CLIの破壊的変更ではschemaVersionとADRを更新する。変更を認められた保護面だけを変更し、probeと全検査を回す。
