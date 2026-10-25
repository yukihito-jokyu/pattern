<!-- このファイルは rules_check.py が rules.md と probes.json から生成する。手で編集しない。 -->

# 強制の対応表

ルールごとに、どの仕組みで守らせているかを示す。段の強さは type > format > lint・structure・test > generator > review > doc の順である。
probe が実際に検査で落ちるかの結果は `.foundation/probe-results.json` にある（`violation_probe.py` が書く）。

## 集計（各ルールの最も強い段で数える）

| 段 | 件数 |
|---|---|
| type | 1 |
| format | 1 |
| lint | 1 |
| structure | 8 |
| test | 5 |
| generator | 0 |
| review | 6 |
| doc | 3 |

## ルールごとの対応

| ルールID | 題名 | 強制 | 仕組み | probe |
|---|---|---|---|---|
| STR-01 | 学習単位の配置 | structure, generator | ERR-01 と同じモデル検査に加えて tools/structure.mjs が必須ファイルを確認する。 | STR-01-a |
| STR-02 | 責務の分割 | review | 差分の責務と参照実装を照合する。 | — |
| DEP-01 | 依存の向き | structure | tools/structure.mjs の許可表で検査する。 | DEP-01-a |
| DEP-02 | 依存と保護面の変更 | review | manifest.protected と差分・ADRを照合する。 | — |
| NAM-01 | 学習識別子と参照 | structure | モデルとブラウザ検査でIDと参照先を照合する。 | NAM-01-a |
| NAM-02 | 意味を示す名前 | review | 新しい識別子の役割と用語表を照合する。 | — |
| CODE-01 | JSの宣言と制御 | lint | ESLint の func-style/no-param-reassign/no-unused-vars/no-var/eqeqeq/max-depth/max-params/max-lines-per-function と ExportDefaultDeclaration 禁止を使う。 | CODE-01-a |
| CODE-02 | JSの型検査 | type | tsconfigでNode用とブラウザ用を検査する。 | CODE-02-a |
| CODE-03 | コメントと数値 | review | 公開関数のJSDocと新しい数値の意味を確認する。 | — |
| CODE-04 | スタイルの所有者 | structure | renderの外部CSS参照とテンプレート構造を検査する。 | CODE-04-a |
| ERR-01 | 閉じた教材データ | structure | model.mjs が境界で未知のJSONを検証する。 | ERR-01-a |
| ERR-02 | 失敗の通知 | test | CLIの不正入力・衝突・再実行をテストする。 | ERR-02-a |
| STATE-01 | 現在枚と注目表示 | test | ブラウザでスライド移動・履歴・表示切替を操作する。 | STATE-01-a |
| ASYNC-01 | 位置の再計測 | test | 通常motionと縮小と連続切替で対象の矩形とSVGを比較する。 | ASYNC-01-a |
| OPS-01 | 対象版と出典 | structure, review | モデルがURLと日付と版を検査し、レビューで実際の取得内容と説明を照合する。 | OPS-01-a |
| OPS-02 | 文書とパスの境界 | test | HTML文字列とパストラバーサルをテストする。 | OPS-02-a |
| OPS-03 | 操作と説明の対応 | test | キーボードと狭幅の操作、全枚・3幅で実文字と番号の矩形をブラウザで検査する。 | OPS-03-a、OPS-03-b |
| TEST-01 | 意味のある検証 | review | 検査の対象とassertと書込先を確認する。 | — |
| PROC-01 | 教材を作る順序 | doc | 実装用とlearning-setupの手順に明記する。 | — |
| PROC-02 | 教材変更の波及 | review | 変更シナリオ表の両側を開いて内容を照合する。 | — |
| PROC-03 | 変更と完了の根拠 | doc | AGENTS.md と完了報告で状態を明記する。 | — |
| TOOL-01 | 整形 | format | Prettier --checkで読み取り検査する。 | TOOL-01-a |
| TOOL-02 | 検査の迂回禁止 | structure | guard.py がルールID付きで検出する。 | TOOL-02-a |
| TOOL-03 | 実行環境と上流固定 | structure | lockとvendor hashをtools/structure.mjsが検査する。 | TOOL-03-a |
| TOOL-04 | 検査の入口 | doc | hooksとci.jsonとAGENTSの同じコマンドから呼ぶ。 | — |

## 機械で縛っていないルール

| ルールID | 題名 | 強制 | 機械化しない理由 |
|---|---|---|---|
| STR-02 | 責務の分割 | review | 関数の意味と責務はimportだけでは判定できない。 |
| DEP-02 | 依存と保護面の変更 | review | 人が許可した変更かは差分だけでは機械判定できない。 |
| NAM-02 | 意味を示す名前 | review | 名前の意味と値の役割の一致には内容の判断が要る。 |
| CODE-03 | コメントと数値 | review | コメントの理由が実装と一致するかは意味の判断が要る。 |
| TEST-01 | 意味のある検証 | review | テストが要求する意味を確認しているかはassertの内容を読む必要がある。 |
| PROC-01 | 教材を作る順序 | doc | 作業の時間順序は最終差分には残らない。 |
| PROC-02 | 教材変更の波及 | review | 教材本文の意味とスライドの主張が一致するかは機械では判定できない。 |
| PROC-03 | 変更と完了の根拠 | doc | 許可と未確認の報告はコード差分に残らない。 |
| TOOL-04 | 検査の入口 | doc | 実際の作業時に呼んだかは差分だけでは確認できない。 |

## 対象外とした軸

| 軸 | 理由 |
|---|---|
