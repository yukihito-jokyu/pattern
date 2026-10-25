# learning-deck-kit の構造

対象技術の学び方を専用スキルに保存し、学習順序に沿ったHTML教材を作る。runtimeはNodeとWeb標準API、スライド生成だけhtml-deckを使う。

## 配置

```text
.claude/skills/learning-setup/
  SKILL.md
  references/authoring.md
  scripts/{types.d.ts,model.mjs,render.mjs,learning.mjs}
  assets/web/{learning.css,learning.mjs}
  vendor/html-deck/
courses/go/profile.json
courses/go/lessons/<lesson-id>/lesson.json
courses/go/lessons/<lesson-id>/deck/{deck.md,theme.css,index.html,slides/*.html}
tools/{check,structure,serve,verify-ci,verify-decks}.mjs
tests/{model,cli}.test.mjs
tests/browser/learning.spec.mjs
build/site/                     生成物・コミットしない
```

learning-setup全体を.agents/skillsまたは.claude/skillsへコピーして使う。配布先はZIPのみで、npm公開は行わない。impl/reviewはキットの保守用である。

## データ契約 schemaVersion=1

profileのキー: schemaVersion,id,title,technology,version,goal,audience,officialHosts,sources,curriculum。
source: {id,title,url,version,checkedAt}。日付はYYYY-MM-DD、urlはofficialHostsに属するHTTPS。latest/未確認をversionに使わない。
curriculum: {id,title,goal,dependsOn}の配列。dependsOnは先行項目のIDだけを許す。
lessonのキー: schemaVersion,id,title,goal,prerequisites,explanation,exercise,sources,slides。
explanation: {title,body,code,output}の配列。code/outputは空文字可。
exercise: {prompt,answer}。prerequisitesは前提知識の非空文字列配列。
sourcesはprofileの出典IDの非空配列。
slides: {file,title,notes}の配列。fileはdeck/slidesからのHTMLファイル名でサブディレクトリとURLと../は禁止。
notes: {id,target,side,title,body}の配列。sideはleft/right。targetはスライドのdata-learning-target値。1枚内でidとtargetは重複不可。
IDは英字始まりkebab-case。title/goalはcurriculumとlessonで同じにする。全JSONは未知キーを拒否する。

## 依存許可表と公開面

| 読込元                  | 許可するローカルimport   | 外部依存                        |
| ----------------------- | ------------------------ | ------------------------------- |
| scripts/model.mjs       | なし                     | node:fs/promises,node:path      |
| scripts/render.mjs      | なし                     | なし                            |
| scripts/learning.mjs    | ./model.mjs,./render.mjs | Node組込                        |
| assets/web/learning.mjs | なし                     | なし                            |
| tools/                  | scripts/、tools/         | Node組込、検査用devDependencies |
| tests/                  | scripts/、tests/         | Node組込、検査用devDependencies |

JSDoc型importはscripts/types.d.tsを許す。
model公開関数: parseProfile(value)、parseLesson(value,profile,curriculumId)、readCourse(courseDir)。
readCourseの返値は{profile,lessons:[{lesson,deckDir}]}。
render公開関数: renderCourse(profile)、renderLesson(profile,lesson)、renderSkill(profile)、renderSources(profile)、renderWorkflow(profile)。
JSはJSDoc付きでstrict/checkJs型検査する。

## HTMLとブラウザの接点

renderLessonは#learning-dataのapplication/jsonへ{slides:[{file,title,notes}]}を安全に格納する。
fileはページからのdeck/slides/*.html相対パス。
ページは../assets/learning.mjs、../assets/learning.cssを読み、トップはassetsを参照する。
固定要素ID: lesson-workspace、slide-stage、slide-frame、annotation-overlay、notes-left、notes-right、annotation-toggle、slide-previous、slide-next、slide-status、slide-error。
iframeは1600×900、border0、sandbox=allow-same-origin。
注目説明はdata-note-id付きカード、SVGはdata-note-id付きg内のellipseとpath。
トップはカリキュラム順のリンク、lessonは左右の注目説明・中央スライド・下の前提/流れ/例/練習/出典。
現在枚は#slide-1形式、前後は端でdisabled。OFFでは左右カードとSVGを隠し本文と現在枚を維持する。
狭幅ではカードをスライド下へ配置する。枠は対象DOMRect×iframe倍率をSVG座標へ変換し、load/resize/fonts/animationend/transitionend/ON復帰で更新。欠損はslide-errorに表示。古いload結果を捨てる。

## CLI 引数は位置引数

| コマンド                                       | 操作                                                                                                                      |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| setup <profile.json> <course-dir> <skills-dir> | profile、learn-idスキル、learning-setupの自己完結コピーを新規生成。衝突は書込前に検査。教材本文は未作成と表示             |
| sync-skill <course-dir> <skills-dir>           | profileからlearn-id/{SKILL.md,references/profile.json,sources.md,workflow.md}を更新。所有マーカーが一致する生成物だけ更新 |
| check <course-dir>                             | 全lesson/deck/出典/注目対象を検査                                                                                         |
| build <course-dir> <output-dir>                | index.html、assets、lesson-id/index.htmlとdeckを生成。専用所有マーカーがある出力だけ再生成可                              |
| sources <course-dir>                           | URL/版/確認日を表示。ネットワーク取得済みとは主張しない                                                                   |
| format-file <json>                             | JSONを2空白・末尾改行で整形                                                                                               |

所有マーカーはschemaVersionとcourse id。無関係ファイルを削除しない。自分自身へlearning-setupをコピーしない。
serveはnode tools/serve.mjs <site-dir> [port]、127.0.0.1だけで配信してトラバーサル拒否。

## 変更シナリオ

| 変更       | 触るファイル                                                                  |
| ---------- | ----------------------------------------------------------------------------- |
| 学習追加   | profile.curriculum、lesson.json、deck。生成スキルはbuild/skillsへ確認用に生成 |
| 説明改善   | lesson.json                                                                   |
| 注目点変更 | slides/*.html、lesson.slides.notes                                            |
| 版変更     | profile.version/sources、影響lesson/deck、実行結果、生成スキル                |
| 表示変更   | assets/web/learning.css、ブラウザ検査                                         |
| CLI追加    | learning.mjs、README、CLIテスト、ADR                                          |
| schema変更 | types/model/render、見本、テスト、schemaVersionとADR                          |

教材データだけの変更は上記の正本へ閉じる。README/AGENTSは構造・環境・操作の契約が変わる場合に更新する。初期の実測表は当時の記録であり、新しい例の期待出力はlesson.jsonと実行検証を正本とする。ブラウザ検査はprofileから全項目を列挙するため、学習追加で検査コードを変更しない。ページの生成先はbuild/site、確認用スキルはbuild/skills、一時領域はbuild/temporary、保持する証跡はbuild/verificationへ統一する。test-resultsはPlaywrightが初期化する自動出力だけに使う。

## 既定値と採用理由

日本語、同一origin HTTP、Chromium/Chrome、初期注目ONとする。UIフレームワークとruntime依存を足さず、データ追加だけで教材が増える構造にした。Goは参照例でありエンジンに埋め込まない。Go1.27の新規runtimeを利用アプリへ要求せず、既存基本構文のコード例を利用可能な1.27.3で検証する。
