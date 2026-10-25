# learning-deck-kit

任意の言語・フレームワーク・ライブラリについて、公式資料と学習順序を専用スキルに保存し、学習項目ごとのHTML教材を作るキットです。各ページはhtml-deckのスライド、左右の注目説明と丸枠・矢印、前提から実行例へつながる本文、練習と解説で構成します。注目表示は閲覧中に切り替えられます。

`courses/go/`にGoの参照教材を収録しています。初期参照教材は変数と型、制御構文、関数の3項目で、各項目に2枚のスライドがあります。現在の一覧と到達点はprofile.jsonのcurriculum、期待出力は各lesson.jsonを正本とします。対象技術の調査・執筆はスキルが案内し、CLIは確定したJSONからスキルとHTMLを生成します。`setup`だけで教材本文や資料の取得が完了するものではありません。

## 環境と導入

ZIPを展開し、以降のコマンドは展開された`learning-deck-kit/`を作業ディレクトリとして実行します。このキットは掲載サイトのコードや依存関係を使いません。

| 用途                                 | 必要な環境                 | 準備と確認                                                                                                                                                                          |
| ------------------------------------ | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 教材・専用スキルの生成、キットの検査 | Node.js 22.23.4と付属のnpm | [Node.js公式](https://nodejs.org/en/download)から22.23.4を選ぶか、利用中の版管理ツールで`.nvmrc`を読み込みます。`package.json`の許容範囲は`>=22.13.0 <23`です。                     |
| 規則検査とhtml-deck                  | Python 3.14系              | [Python公式](https://www.python.org/downloads/)などから導入し、`python3`と`python3.14`で使えるようにします。実測環境は3.14.9です。                                                  |
| html-deckの固定依存導入              | uv 0.13.5                  | [uvの公式手順](https://docs.astral.sh/uv/getting-started/installation/)で導入します。Python依存は同梱`uv.lock`で固定します。                                                        |
| スライドの実測                       | システムのGoogle Chrome    | [Chrome公式](https://www.google.com/chrome/)から導入します。macOSは`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`、Linuxは`/opt/google/chrome/chrome`を検査します。 |
| 学習ページのブラウザ検査             | Playwright管理のChromium   | npm依存導入後、以下のコマンドで追加します。システムChromeとは別に使います。                                                                                                         |
| Go参照例の出力確認                   | Go 1.27系                  | [Go公式](https://go.dev/dl/)から導入します。`go.mod`は`go 1.27.0`、実測環境は1.27.3です。                                                                                           |

準備した環境を確認してから、固定依存を導入します。バージョンが合わない場合や導入に失敗した場合は、後続の検査を進めず準備を直します。

```sh
node --version
npm --version
python3 --version
python3.14 --version
uv --version
go version
npm ci
npx playwright install chromium
```

LinuxでブラウザのOS依存も導入する場合は、最後のコマンドを`npx playwright install --with-deps chromium`にします。OSパッケージの導入権限が必要です。html-deck検査は既存のブラウザを入れ替えず、上のパスにChromeがなければ準備不足として停止します。Windowsの検証手順は用意していません。

開発依存は`package-lock.json`に固定しています。Prettier 3.9.10、ESLint 10.13.0、TypeScript 7.0.2、Playwright 1.64.1、Node型定義22.20.5を使います。教材を生成するCLI自体はNode標準ライブラリだけで動き、生成済み教材の閲覧に必要なのはブラウザとHTTP配信だけです。

## Go参照教材を開く

```sh
npm run build
npm run serve
```

`http://127.0.0.1:4187/`を開きます。学習一覧から各項目へ進み、前後ボタンまたは左右キーでスライドを移動します。Home・Endで先頭・末尾へ移動できます。URLの`#slide-1`などに現在枚を保存するため、ブラウザの戻る操作でもその位置へ戻れます。

「注目説明」ボタンを操作すると、左右の説明・丸枠・矢印が切り替わります。非表示でも現在枚と下部の本文は維持します。下へ進むと、前提、処理の流れ、完全なコードと期待結果、練習、開閉できる解説を読めます。サーバーはCtrl-Cで終了します。

`build`の入力は`courses/go/`、出力は`build/site/`です。`serve`はその出力を`127.0.0.1`で配信します。注目箇所はiframe内の要素を計測するため、親ページとスライドを同じHTTPサーバーから配信します。HTMLを`file://`で直接開く方法は対応条件に含めていません。

## 利用先へ専用スキルを作る

次は、Go参照profileを使い、キット内の新しい`learning/go/`へコースを用意する例です。Codex用の生成先を`.agents/skills/`にしています。

```sh
node tools/learning.mjs setup courses/go/profile.json learning/go .agents/skills
```

生成されるのは次のファイルです。

```text
learning/go/profile.json
.agents/skills/
  learn-go/
    SKILL.md
    references/profile.json
    references/sources.md
    references/workflow.md
    .learning-generated.json
  learning-setup/
    SKILL.md
    references/authoring.md
    scripts/
    assets/
    vendor/html-deck/
```

`learn-go`には目的・対象版・資料一覧と取得・更新手順、兄弟の`learning-setup`には共通の生成器と固定版html-deckを置きます。`learning/go/`にはprofileだけがあり、`lessons/`や教材本文はまだありません。`setup`はネットワーク取得も行いません。Codexでは利用先で`$learn-go`を使います。Claude Codeで使う場合は、生成先を`.claude/skills/`に変更します。

参照教材をそのまま試す場合は、上の新規生成後に学習項目をコピーします。

```sh
cp -R courses/go/lessons learning/go/lessons
node tools/learning.mjs check learning/go
node tools/learning.mjs build learning/go learning-site/go
node tools/serve.mjs learning-site/go 4188
```

`http://127.0.0.1:4188/`で、コピー先のGo教材を開けます。別のプロジェクトへ導入する場合は、コースと生成された2つのスキルをそのプロジェクトに置きます。キットの`tools/learning.mjs`を持ち込まず、共通スキル内の`scripts/learning.mjs`を直接呼ぶこともできます。

## 新しい技術の教材を作る

最初に`.claude/skills/learning-setup/SKILL.md`と`references/authoring.md`を読みます。公式サイト・公式リポジトリ・リリース情報を照合し、対象版と読者、到達目標、前提から積み上げる学習順序を決めます。登録したURLの本文を取得し、対象版を確認します。URLを列挙しただけの状態、取得拒否、本文のないJavaScriptの外枠は、資料確認済みとしません。

profileには次を保存します。全キーが必須で、未知のキーは拒否します。

- `schemaVersion`、`id`、`title`、`technology`、`version`、`goal`、`audience`：形式、コースの識別子、表題、技術と対象版、目標と読者。
- `officialHosts`と`sources`：資料を許可するホスト名と、出典の`id`・`title`・`url`・`version`・`checkedAt`。URLは許可したホストのHTTPS、確認日は実際に本文を確認した日です。
- `curriculum`：各項目の`id`・`title`・`goal`・`dependsOn`。配列が学習順となり、前提には先に登場するIDだけを指定できます。

例えばIDを`my-topic`にしたprofileを`profiles/my-topic.json`へ用意した場合は、次のように生成します。profileの固有値は、実際に調べた技術・資料へ置き換えます。

```sh
node tools/learning.mjs setup profiles/my-topic.json learning/my-topic .agents/skills
```

次に専用スキルと共通スキルの制作手順に従い、各項目を`learning/my-topic/lessons/`へ作ります。`lesson.json`にはprofileと一致する`schemaVersion`・`id`・`title`・`goal`、前提を表す`prerequisites`、説明の`explanation`、問いと理由の`exercise`、出典IDの`sources`、スライド一覧の`slides`を保存します。`explanation`の各要素は`title`・`body`・`code`・`output`、`exercise`は`prompt`・`answer`です。コードを実際に実行し、期待結果と照合してから記録します。

スライドは同梱のhtml-deckを使います。制作前に`vendor/html-deck/SKILL.md`と品質契約を読み、`deck.md`へ目的・読者・場面・制約を記録します。例えば最初の項目IDを`first-step`にした場合の初期化は次のとおりです。

```sh
uv run --locked --python 3.14 --project .claude/skills/learning-setup/vendor/html-deck/tools html-deck-init learning/my-topic/lessons/first-step/deck --title "最初の学習項目"
```

`deck/slides/01.html`などへ図や短いコード例を置き、1枚1主張にします。詳しい前提・処理・実行コードは外側の本文へ書きます。注目箇所には`data-learning-target="declaration"`のような安定IDを付け、`slides[].notes`の`target`へ同じ値を書きます。noteは`id`・`target`・`side`・`title`・`body`を持ち、`side`は`left`か`right`です。1枚の中でnoteのIDと対象は重複させず、対象要素は1つだけにします。

丸枠の位置はブラウザが1600×900の座標から表示寸法へ変換します。作者がSVGの座標を手入力する必要はありません。スライドを変えたら対象と説明も更新し、通常表示、縮小後、切替後、注目表示を再びONにした後の位置を確認します。

```sh
node tools/learning.mjs check learning/my-topic
node tools/learning.mjs build learning/my-topic learning-site/my-topic
node tools/learning.mjs sync-skill learning/my-topic .agents/skills
node tools/serve.mjs learning-site/my-topic 4188
```

CLIの全コマンドは次の役割です。いずれも位置引数の順に指定します。

| コマンド      | 引数                                      | 動作                                                 |
| ------------- | ----------------------------------------- | ---------------------------------------------------- |
| `setup`       | profileのJSON、コース生成先、スキル生成先 | profile、専用スキル、共通スキルを新規生成する        |
| `sync-skill`  | コース、スキル生成先                      | 更新済みprofileから専用スキルを再生成する            |
| `check`       | コース                                    | profile、本文、deck、出典と注目対象の対応を検査する  |
| `build`       | コース、ページ生成先                      | 検査後、一覧と項目ページ・表示用資産・deckを生成する |
| `sources`     | コース                                    | 登録URL・資料版・確認日を表示する。取得は行わない    |
| `format-file` | JSONファイル                              | 教材JSONを整形する                                   |

資料の更新では、同じ公式URLと対象版を再確認し、本文、コード、実行結果、注目点を一緒に直します。実際に確認した出典の`checkedAt`を更新し、`check`・`build`・スライド実測をやり直してから`sync-skill`で資料一覧をそろえます。

## 生成物と上流ファイルの扱い

コースの正本は`profile.json`・`lesson.json`・`deck/`です。生成したスキルとページには`.learning-generated.json`という所有台帳を置き、コースID、相対パス、各生成物のSHA-256を保存します。再生成では台帳と現在のファイルを照合し、手編集された生成物や利用者ファイルとの衝突があれば上書きせず停止します。無関係なファイルは残し、不要になった管理対象だけを削除します。入力コースと重なるページ生成先や、出力先のシンボリックリンクも拒否します。

html-deckは[nogikun/skills](https://github.com/nogikun/skills/tree/2d638228f0104fa6ebfad6447bb1652379e1da78/skills/html-deck)のコミット`2d638228f0104fa6ebfad6447bb1652379e1da78`を固定して同梱しています。`vendor-lock.json`と構造検査で各ファイルのハッシュを照合します。上流本体と内包するdraw.ioスキルのMITライセンスをそれぞれ保持しています。検査を通すためにvendorを修正せず、教材側を直します。

## 検証

環境と依存を準備した後、キットのルートで次を順に実行します。

```sh
npm run check
npm run verify:decks
python3 .foundation/bin/violation_probe.py --root .
python3 .foundation/bin/rules_check.py --root . --final
```

`check`は抑止コメント検査、整形、lint、Node・ブラウザ・テストの型、構造、モデル・CLI・ブラウザ検査、Go実行例、規則対応を順に確認します。成功時は`check: passed`です。`verify:decks`は固定版html-deckと各deckをOSの一時ディレクトリへコピーし、実際のChromeで検査します。正本の`index.html`や`.loop/`を検査で書き換えません。blockが0なら通過し、review/infoの件数も表示します。終了0だけで全所見や意味のレビューを完了したとは扱いません。

違反例の検査は一時コピーへ変異を入れ、対応する検査が想定の理由で失敗するかを確かめます。`rules_check.py --final`は、規則・検査・違反検出の対応と最終状態を確認します。個別の内容は`docs/design/rules.md`と`enforcement-matrix.md`にあります。

CIの入口は`ci.json`の`node tools/verify-ci.mjs`です。Node 22、Python 3.14、システムChrome、`go.mod`指定のGoを用意してから実行します。uvが0.13.5ならそのまま使い、不足・版違いなら公式PyPIの固定wheelを一時領域へ導入して、子プロセスだけに渡します。既存のuvやChromeは入れ替えません。ChromeまたはPythonがない場合は準備不足として停止します。この入口は`npm ci`、Playwright Chromium準備、`npm run check`、`npm run verify:decks`を順に実行し、成功時に`ZIP verification: passed (check, examples, original html-deck)`を表示します。上の違反例検査と規則の最終確認は、開発完了時に別途実行します。

実測レポートを保持したい場合は、`CI_ARTIFACTS_DIR`へ保存先の絶対パスを指定して`npm run verify:decks`を実行します。指定がなければ一時コピーは終了時に削除します。`.venv/`、`.loop/`、`node_modules/`、生成した`build/site/`は配布する正本へ含めません。

2026-10-25時点の教材単位の確認では、3つの完全なGo例をGo 1.27.3で実行し、記録した出力と一致しました。資料の確認日は2026-10-24です。

| 項目     | 実測した出力                          | html-deckのblock / review / info |
| -------- | ------------------------------------- | -------------------------------- |
| 変数と型 | `Go: 3 lessons`                       | 0 / 4 / 6                        |
| 制御構文 | `learn 1`、`learn 2`、`review 3`の3行 | 0 / 4 / 6                        |
| 関数     | `remaining 2`                         | 0 / 4 / 6                        |

3deck・6スライドの合計はblock 0、review 12、info 18です。Python 3.14.9とmacOSのシステムChromeを使いました。見出しを60pxへ修正して階層の指摘3件を解消し、残ったreviewは視線の入口候補と意味要素の群化、infoは空白・間隔と図の寸法です。6枚を画像で確認し、文字切れ・重なりは見られませんでした。

統合ブラウザ11件・単体22件・Go例3件と、整形・lint・型・構造・guardが成功しています。別の一時領域へ展開したZIPでも、依存準備から全検査、元のhtml-deck実測、違反例17件とcheckへの組込み7経路、規則の最終確認が成功しました。掲載サイトはカード・文書・画像・ダウンロードを実ブラウザで確認しています。実施方法と出力は[検証記録](docs/design/verification.md)にあります。

独立エージェントの変更範囲・命名・内容の比較と、違反を仕込んだレビューの結果は[収束記録](docs/design/convergence-report.md)にあります。3回の比較で、最終12実装の全検査と、全レビュアーの仕込み8件検出が成功しました。一方、新規教材の注目対象の選択・命名にR1が1件残り、names=0.667で基準0.8に届かないため、完全収束とはしていません。

参照スライドの別モデルによる2回の批評では、変数の2枚目にコード枠の余白の指摘が1件残っています。上流の2回上限に従い、解消済みとはせず[批評と人間確認の範囲](docs/design/reference-review.md)へ記録しました。Safari・Firefox、Windows、実機の読みやすさ、人間による教材内容の最終確認も未確認です。

## キットを変更するとき

このディレクトリでエージェントを起動し、`AGENTS.md`から実装用の`.claude/skills/impl/SKILL.md`またはレビュー用の`.claude/skills/review/SKILL.md`へ進みます。`CLAUDE.md`も同じ入口を参照します。規則を変える場合は、設計判断、規則、検査と違反例、参照教材、スキルの順に整合を取ります。

全体の目的は[docs/design/overview.md](docs/design/overview.md)、構造とデータ形式は[architecture.md](docs/design/architecture.md)、規則の全文は[rules.md](docs/design/rules.md)、規則と検査の対応は[enforcement-matrix.md](docs/design/enforcement-matrix.md)、独立した実装結果の比較は[convergence-report.md](docs/design/convergence-report.md)で確認できます。
