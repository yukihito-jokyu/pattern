# learning-deck-kit

任意技術の学習スキルと、html-deckを埋め込む学習項目別のHTMLページを作る基盤。Go教材が参照実装である。

## 作業の入口

| やること               | 使うもの                               |
| ---------------------- | -------------------------------------- |
| 実装・変更・追加・修正 | .claude/skills/impl/SKILL.md           |
| レビュー               | .claude/skills/review/SKILL.md         |
| 技術別学習スキルの生成 | .claude/skills/learning-setup/SKILL.md |
| 規則と構造             | docs/design/rules.md、architecture.md  |

Skillが使えなければ該当ファイルを直接読む。このキットのディレクトリでエージェントを起動する。

## コマンド

| 目的         | コマンド                                            |
| ------------ | --------------------------------------------------- |
| 固定依存導入 | npm ci                                              |
| 全検査       | npm run check                                       |
| 自動修正     | npm run fix                                         |
| コース検査   | node tools/learning.mjs check courses/go            |
| ページ生成   | npm run build                                       |
| 閲覧         | npm run serve                                       |
| 違反検出証明 | python3 .foundation/bin/violation_probe.py --root . |

Node22を使う。収束コピー内では依存の追加・削除・再導入をしない。OS一時領域の作業コピーは親が準備する。

## ディレクトリ構造

- courses/id：プロフィールと学習項目とdeckの正本。
- .claude/skills/learning-setup：自己完結する生成器・ビューア・html-deck。
- tools/とtests/：このキット専用の保守・検査。
- docs/design/：根拠・規則・測定結果。
- build/：生成ページと確認用スキル。編集・コミットしない。
- build/temporary・build/verification：一時領域と保持する画像・ログ。
- test-results/：Playwrightが初期化する自動出力。TMPDIRや保持する証跡を置かない。

## 守ること

全文と理由はrules.mdにある。

- STR-01：コースはprofile、学習項目はlesson.jsonとdeckへ置く。
- DEP-01：学習追加でruntimeへ固有技術の分岐を書かない。
- NAM-01：IDと参照先を一意にし、見本の命名を使う。
- CODE-02：未知JSONとDOM欠損を型で扱い、型を無視しない。
- ERR-01：キーと対象版と前提順序を検査する。
- ERR-02：衝突した既存ファイルを上書きしない。
- ASYNC-01：注目枠はアニメと縮小後も再計測する。
- OPS-01：取得した公式本文と対象版を照合し、URLだけで確認済みにしない。
- OPS-03：表示OFFでも下部の本文と学習位置を維持する。
- PROC-01：資料取得→profile→deck→外側本文→注目対応→検証で作る。
- PROC-02：例と本文と出力、注目対象を一緒に見直す。
- PROC-02：データだけの変更ではREADME/AGENTSを変えず、生成スキルはbuild/skillsへ確認用に生成する。所有台帳を手編集しない。
- PROC-03：検証の成功・失敗・未実施と人間確認待ちを分ける。
- TOOL-02：抑止コメントとskip/onlyを足さない。
- TOOL-03：上流ソースと固定依存を保持する。
- TOOL-04：編集後は対象整形/lint、完了前は全検査を実行する。

## してはいけないこと

検査を通すために保護ファイル（manifest.protected）を変える、検査やテストを消す、未依頼の依存を足す、生成物を正本として直す、見本にない構造をその場で発明する行為を禁止する。必要な変更は理由と影響を報告する。vendorは改変しない。

## 完了の条件

1. npm run checkが通る。
2. implのチェックリストを満たす。
3. 対象版、決めた既定値、検証、人間の未確認範囲を報告する。

## ルールを変えたいとき

既に許可された範囲内ならADR→rules→検査とprobe→見本→スキルの順で反映する。範囲を変えるなら理由と影響を示し人の判断を得る。rules_checkとprobeで対応を再検査する。
