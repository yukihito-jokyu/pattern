# learning-deck-kit のルール

規則の正本。検査とレビューはルールIDを参照する。

## 用語

| 用語    | 意味                            |
| ------- | ------------------------------- |
| profile | 対象技術・資料・学習順序の正本  |
| lesson  | 1つの到達目標を扱う学習項目     |
| deck    | html-deckの1600×900スライド一式 |
| note    | 補足説明と注目対象の対応        |

## 追加した軸

| 軸  | 内容                   | 置く節 |
| --- | ---------------------- | ------ |
| X1  | ルートファイルの書き方 | STR    |
| X2  | スタイルの書き方       | CODE   |
| X3  | アクセシビリティの定型 | OPS    |
| X4  | 終了コードと出力の形式 | OPS    |
| X5  | 公開APIの互換性        | PROC   |

### STR-01 学習単位の配置

- 軸: A1,A2,A5,A6,A7,X1
- 決定: プロフィールは `courses/<id>/profile.json`、各学習項目は `lessons/<id>/lesson.json` と `deck/` に置き、ページは `site/<lesson-id>/index.html` に生成する。
- 理由: 追加時の置き場と公開URLを固定する。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure, generator — ERR-01 と同じモデル検査に加えて tools/structure.mjs が必須ファイルを確認する。
- probe: STR-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で学習単位の配置を実装し、対応する検査や説明を更新しない。

### STR-02 責務の分割

- 軸: A3,A4
- 決定: データ検証は `model.mjs`、HTML構成は `render.mjs`、ファイル操作とCLIは `learning.mjs`、ブラウザ操作は `assets/web/learning.mjs` に置く。
- 理由: 教材を追加するときに表示エンジンの変更を不要にする。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — 差分の責務と参照実装を照合する。
- 機械化しない理由: 関数の意味と責務はimportだけでは判定できない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で責務の分割を実装し、対応する検査や説明を更新しない。

### DEP-01 依存の向き

- 軸: B1,B2,B3,B4,B5
- 決定: 許可表にないローカルimport、外部パッケージのruntime import、ブラウザからNode組込モジュールへのimportを禁止する。
- 理由: スキル単独コピーとブラウザ閲覧を依存導入から独立させる。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — tools/structure.mjs の許可表で検査する。
- probe: DEP-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で依存の向きを実装し、対応する検査や説明を更新しない。

### DEP-02 依存と保護面の変更

- 軸: B6,G3
- 決定: 依存追加、保護ファイルの変更、検査の緩和は理由と影響をADRに記録し、明示された変更範囲と照合する。
- 理由: 検査を通すための設定変更を成果物修正と区別する。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — manifest.protected と差分・ADRを照合する。
- 機械化しない理由: 人が許可した変更かは差分だけでは機械判定できない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  検査エラーを消すためprotectedから設定を外す。

### NAM-01 学習識別子と参照

- 軸: C1,C7
- 決定: コース・学習項目・出典・注目対象のIDは英字始まりのkebab-caseにし、参照を一意に解決する。
- 理由: ファイル名とURL、資料と注目枠の対応を切らさない。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — モデルとブラウザ検査でIDと参照先を照合する。
- probe: NAM-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で学習識別子と参照を実装し、対応する検査や説明を更新しない。

### NAM-02 意味を示す名前

- 軸: C2,C3,C4,C5,C6
- 決定: JS識別子はcamelCase、クラスと型はPascalCaseとし、真偽値はis/has、配列は複数形、時間値はMsで終える。
- 理由: 同じ役割の名前が作者ごとに分かれることを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — 新しい識別子の役割と用語表を照合する。
- 機械化しない理由: 名前の意味と値の役割の一致には内容の判断が要る。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で意味を示す名前を実装し、対応する検査や説明を更新しない。

### CODE-01 JSの宣言と制御

- 軸: D1,D2,D4,D5,D6
- 決定: named exportと関数宣言を使い、引数の変更、未使用変数、var、緩い比較を禁止し、ネストは4段・引数は4個・関数は120行を上限にする。
- 理由: 読み書きの形をそろえて局所修正を保つ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: lint — ESLint の func-style/no-param-reassign/no-unused-vars/no-var/eqeqeq/max-depth/max-params/max-lines-per-function と ExportDefaultDeclaration 禁止を使う。
- probe: CODE-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形でJSの宣言と制御を実装し、対応する検査や説明を更新しない。

### CODE-02 JSの型検査

- 軸: D3
- 決定: 自作JSはJSDocと `strict`・`checkJs`・`noUncheckedIndexedAccess` を有効にしたTypeScriptで検査し、型無視を使わない。
- 理由: JSON境界とDOMの欠損をコード上で扱う。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: type — tsconfigでNode用とブラウザ用を検査する。
- probe: CODE-02-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形でJSの型検査を実装し、対応する検査や説明を更新しない。

### CODE-03 コメントと数値

- 軸: D7,D8
- 決定: 公開関数に入出力のJSDocを書き、コメントは採用理由を説明し、キャンバス寸法は1600と900の定数から参照する。
- 理由: 型の入口と座標変換の前提を共有する。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — 公開関数のJSDocと新しい数値の意味を確認する。
- 機械化しない理由: コメントの理由が実装と一致するかは意味の判断が要る。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形でコメントと数値を実装し、対応する検査や説明を更新しない。

### CODE-04 スタイルの所有者

- 軸: X2
- 決定: 学習ページのスタイルは `assets/web/learning.css`、スライドのスタイルは各 `deck/theme.css` に置き、相互にコピーしない。
- 理由: iframeの独立したデザインと外側の説明を保つ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — renderの外部CSS参照とテンプレート構造を検査する。
- probe: CODE-04-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形でスタイルの所有者を実装し、対応する検査や説明を更新しない。

### ERR-01 閉じた教材データ

- 軸: E2
- 決定: プロフィールと学習項目はschemaVersion=1の閉じたキー集合で検証し、空の必須項目、未知キー、未登録出典、順序が逆の前提を拒否する。
- 理由: 不完全な教材を読者へ渡さない。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — model.mjs が境界で未知のJSONを検証する。
- probe: ERR-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で閉じた教材データを実装し、対応する検査や説明を更新しない。

### ERR-02 失敗の通知

- 軸: E1,X4
- 決定: CLIは成功時に標準出力と終了0、失敗時に理由を標準エラーと終了1へ出し、既存の利用者ファイルを無断上書きしない。
- 理由: 失敗を成功と誤認せず既存教材を保護する。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: test — CLIの不正入力・衝突・再実行をテストする。
- probe: ERR-02-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で失敗の通知を実装し、対応する検査や説明を更新しない。

### STATE-01 現在枚と注目表示

- 軸: E3
- 決定: 現在枚はURLのhashで表し、注目表示のオン・オフは同じページ内の状態で管理し、切替後も本文と現在枚を維持する。
- 理由: 学習の位置を保ったまま補足を出し入れできるようにする。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: test — ブラウザでスライド移動・履歴・表示切替を操作する。
- probe: STATE-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で現在枚と注目表示を実装し、対応する検査や説明を更新しない。

### ASYNC-01 位置の再計測

- 軸: E4
- 決定: load、親領域resize、スライド切替、注目表示のON復帰、内部fonts.ready、animationend、transitionendで対象位置を再計測し、旧スライドの結果を描かない。
- 理由: 縮小・遅い読込・入場演出で注目枠がずれることを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: test — 通常motionと縮小と連続切替で対象の矩形とSVGを比較する。
- probe: ASYNC-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で位置の再計測を実装し、対応する検査や説明を更新しない。

### OPS-01 対象版と出典

- 軸: E5,E6,E7
- 決定: 各出典に公式HTTPS URL・対象版・確認日を記録し、setup時に対象技術・目標・前提知識・対象版を確定する。
- 理由: URLだけを持つスキルや取得していない資料の確認済み扱いを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure, review — モデルがURLと日付と版を検査し、レビューで実際の取得内容と説明を照合する。
- probe: OPS-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  取得していない資料を確認済みと書く。

### OPS-02 文書とパスの境界

- 軸: E8
- 決定: 教材の文字列をHTMLでエスケープし、スライド参照は `deck/slides/` 内のHTML、資料参照は登録された公式hostのHTTPSへ限定する。
- 理由: 教材入力からスクリプトや外部ファイルの読み取りが混入するのを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: test — HTML文字列とパストラバーサルをテストする。
- probe: OPS-02-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で文書とパスの境界を実装し、対応する検査や説明を更新しない。

### OPS-03 操作と説明の対応

- 軸: X3
- 決定: 切替は名前付きbuttonとaria-pressed、ページ移動はaを使い、SVGをaria-hiddenとpointer-events:noneにし、狭い画面でも番号付き説明を読めるようにする。注目番号は白い縁を含めてスライド内へ収め、実際の文字と他の番号へ重ねない。
- 理由: 注目枠が操作を塞がず、色や矢印だけに意味を依存させない。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: test — キーボードと狭幅の操作、全枚・3幅で実文字と番号の矩形をブラウザで検査する。
- probe: OPS-03-a, OPS-03-b
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で操作と説明の対応を実装し、対応する検査や説明を更新しない。

### TEST-01 意味のある検証

- 軸: F1,F2,F3,F4,F5
- 決定: モデルと生成はNode単体、UIは実ブラウザ、Go例は実行結果で検査し、テスト用の書込みはOS一時ディレクトリへ限定する。
- 理由: 正常な出力と誤りの検出を区別し、本物の教材をテストで変更しない。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — 検査の対象とassertと書込先を確認する。
- 機械化しない理由: テストが要求する意味を確認しているかはassertの内容を読む必要がある。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で意味のある検証を実装し、対応する検査や説明を更新しない。

### PROC-01 教材を作る順序

- 軸: G1
- 決定: 公式資料の取得、プロフィールと学習順序、各スライド、外側の説明、注目対応、全検査の順で作る。
- 理由: 根拠がない説明や前提の飛躍を減らす。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: doc — 実装用とlearning-setupの手順に明記する。
- 機械化しない理由: 作業の時間順序は最終差分には残らない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で教材を作る順序を実装し、対応する検査や説明を更新しない。

### PROC-02 教材変更の波及

- 軸: G2
- 決定: 対象版・学習順序・例・注目対象を変更したら、対応するプロフィール、学習本文、スライド、実行結果、生成スキルを同時に照合する。データだけの変更ではREADME/AGENTSを編集せず、生成スキルをbuild/skillsへ確認用に生成する。生成物と所有台帳は手編集しない。変更したコードの実測日は実行当日へ更新し、資料の確認日は再取得した出典だけ更新する。
- 理由: 片側だけの更新による説明の矛盾を防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: review — 変更シナリオ表の両側を開いて内容を照合する。
- 機械化しない理由: 教材本文の意味とスライドの主張が一致するかは機械では判定できない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  コードの3を4へ変え、説明と期待出力は3のまま残す。

### PROC-03 変更と完了の根拠

- 軸: G4,G5,X5
- 決定: ルール変更はADR、規則、検査とprobe、見本、スキルの順に反映し、検査と人間の確認の状態を分けて報告する。
- 理由: 自動検証の成功を学習内容の人間承認と混同しない。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: doc — AGENTS.md と完了報告で状態を明記する。
- 機械化しない理由: 許可と未確認の報告はコード差分に残らない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で変更と完了の根拠を実装し、対応する検査や説明を更新しない。

### TOOL-01 整形

- 軸: H1
- 決定: 自作JS・JSON・HTML・CSSはPrettierで整形し、生成物・上流vendor・foundationはそのまま保持する。course JSONの編集hookもPrettierを使い、CLIのformat-fileをソースの正規整形に使わない。
- 理由: 書式の選択を作者から切り離す。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: format — Prettier --checkで読み取り検査する。
- probe: TOOL-01-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で整形を実装し、対応する検査や説明を更新しない。

### TOOL-02 検査の迂回禁止

- 軸: H3
- 決定: lintと型の抑止コメント、テストのskipとonlyを追加しない。
- 理由: 検査を消して成功と扱うことを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — guard.py がルールID付きで検出する。
- probe: TOOL-02-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で検査の迂回禁止を実装し、対応する検査や説明を更新しない。

### TOOL-03 実行環境と上流固定

- 軸: H4
- 決定: Node22、Python3.14、固定npm依存とuv.lockを使い、同梱html-deckとライセンスは記録したSHA256と一致させる。
- 理由: 依存解決と上流改変で結果が変わることを防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: structure — lockとvendor hashをtools/structure.mjsが検査する。
- probe: TOOL-03-a
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で実行環境と上流固定を実装し、対応する検査や説明を更新しない。

### TOOL-04 検査の入口

- 軸: H2
- 決定: 編集後は対象ファイルの整形とlint、完了前とCIでは `npm run check` を実行する。
- 理由: 実装だけが更新され検査が呼ばれない状態を防ぐ。
- 出典: [技術調査](./research.md)、[構造](./architecture.md)
- 強制: doc — hooksとci.jsonとAGENTSの同じコマンドから呼ぶ。
- 機械化しない理由: 実際の作業時に呼んだかは差分だけでは確認できない。
- probe: なし
- 良い例:
  見本: `courses/go/`、`.claude/skills/learning-setup/`
- 悪い例:
  見本と異なる形で検査の入口を実装し、対応する検査や説明を更新しない。

## 対象外とした軸

| 軸  | 理由 |
| --- | ---- |

全カタログ軸を上の規則で扱う。X5はschemaVersion=1とCLI引数を対象とし、破壊的変更ではschemaVersionを増やす。
