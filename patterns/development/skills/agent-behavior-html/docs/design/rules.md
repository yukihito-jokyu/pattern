# claude-codex-cli のルール

この文書が決定の正本である。

## 用語

| 用語 | 意味 |
|---|---|
| イベント | hookが起動した観測記録1件 |
| 呼び出し | tool_use_idで識別できる実行 |
| completed | 後イベントはあるが成否の明示がない状態 |
| 欠落 | 前後の一方しか見つからない状態 |

## 追加した軸

| 軸 | 内容 | 置く節 |
|---|---|---|
| X1 | 終了コードと出力の形式 | OPS |
| X2 | 公開APIの互換性 | PROC |
| X3 | 製品ごとの観測範囲と未知値 | OPS |

## STR 配置と構造

### STR-01 qualityの配置検査

- 軸: A1〜A7
- 決定: 実行コードを配布スキルのscripts、HTMLをassets、テストをtests、検査をscriptsへ配置し、Codexの入口は.agents/skillsの相対リンクにする。
- 理由: qualityの配置検査で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — qualityの配置検査
- probe: STR-01-a
- 良い例: `scripts/record.pyを配布スキル内に置く`
- 悪い例: `同じ収集器を別のsrc/にも置く`

## DEP 境界と依存

### DEP-01 ASTのimport検査

- 軸: B1〜B6
- 決定: エントリポイントは標準ライブラリとevent_modelだけをimportし、event_modelは標準ライブラリだけに依存する。
- 理由: ASTのimport検査で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — ASTのimport検査
- probe: DEP-01-a
- 良い例: `from event_model import normalize`
- 悪い例: `import requests`

## NAM 命名

### NAM-01 AST命名検査と入口一覧

- 軸: C1〜C7
- 決定: Pythonの関数・引数・変数とJSONキーはsnake_case、定数はUPPER_SNAKE_CASE、JavaScript関数はcamelCase、CLI動詞はrecord・analyze・installに固定する。
- 理由: AST命名検査と入口一覧で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — AST命名検査と入口一覧
- probe: NAM-01-a
- 良い例: `tool_use_id / build_calls`
- 悪い例: `toolUseId / BuildCalls`

## CODE 書き方

### CODE-01 ASTの関数注釈と大きさ検査

- 軸: D1〜D8
- 決定: 公開処理を型注釈付き関数で定義し、関数を160行以内、引数を8個以内とし、境界値を大文字の定数へ置く。
- 理由: ASTの関数注釈と大きさ検査で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — ASTの関数注釈と大きさ検査
- probe: CODE-01-a
- 良い例: `def parse_time(value: str) -> datetime:`
- 悪い例: `def parse_time(value):`

## ERR エラーと入力検証

### ERR-01 CLI終了とstdout契約

- 軸: E1
- 決定: hookは記録失敗を固定stderrだけで通知して終了0、分析と導入は入力不正をstderrと終了1、引数誤りを終了2で返す。
- 理由: CLI終了とstdout契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — CLI終了とstdout契約
- probe: ERR-01-a
- 良い例: `収集失敗は固定stderrとexit0`
- 悪い例: `ログ保存失敗でexit2を返す`

### ERR-02 入力境界と重複排除契約

- 軸: E2
- 決定: stdinを8MiB以下のJSONオブジェクトに制限し、分析時にversion別の閉じたv1/v2スキーマを検証し、不正行と重複event_idを集計する。
- 理由: 入力境界と重複排除契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 入力境界と重複排除契約
- probe: ERR-02-a
- 良い例: `未知versionを不正行として数える`
- 悪い例: `未知versionを無検証で集計する`

## STATE 状態とデータの流れ

### STATE-01 保存先とsession分離契約

- 軸: E3
- 決定: 明示プロジェクトの.agent-logsへsourceとsession_idのハッシュで分けたJSONLを追記し、既存ログを上書きしない。
- 理由: 保存先とsession分離契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 保存先とsession分離契約
- probe: STATE-01-a
- 良い例: `sourceとsessionのハッシュごとに追記`
- 悪い例: `session_idをファイル名へ直接連結する`

## ASYNC 非同期と並行

### ASYNC-01 並行・前後欠落・逆順契約

- 軸: E4
- 決定: 追記と鍵作成をロックし、ロック待ちを0.5秒で中止し、時間計測をsource・session_id・tool_use_idの一致する前後hookに限定する。
- 理由: 並行・前後欠落・逆順契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 並行・前後欠落・逆順契約
- probe: ASYNC-01-a
- 良い例: `同じsource・session・tool_use_idを結ぶ`
- 悪い例: `後イベントを直前の前イベントへ結ぶ`

## OPS ログ・設定・セキュリティ・表示

### OPS-01 操作情報の選択とマスク契約

- 軸: E5
- 決定: v2で操作対象・短い目的・期待結果・結果抜粋をバイト上限内へ保存し、既知の資格情報形式をマスクし、prompt・tool_input全体・tool_response全体・transcript・cwd・Read/Write/Editの本文を保存しない。
- 理由: 操作・目的・結果を分析しつつ、選んだ情報以外の入力を保持しない境界を検証する。
- 出典: research.md、adr/0002-operation-purpose-results.md
- 強制: test — 操作情報の選択とマスク契約
- probe: OPS-01-a
- 良い例: `targetとマスク済みのresult_summaryを上限内へ保存`
- 悪い例: `tool_inputをそのまま保存`

### OPS-02 明示パス契約

- 軸: E6
- 決定: 設定をCLI引数から受け、既定のログ先を.agent-logs、HTML先をreports/agent-behavior.htmlとし、環境変数・認証情報・会話履歴を読まない。
- 理由: 明示パス契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 明示パス契約
- probe: OPS-02-a
- 良い例: `--log-dir /project/.agent-logs`
- 悪い例: `transcript_pathを開いて追記する`

### OPS-03 日時と経過時間契約

- 軸: E7
- 決定: 受信日時をUTCのISO8601で保存し、表示をAsia/TokyoまたはUTCから選べるようにし、所要時間をhook受信時刻差のmsで表す。
- 理由: 日時と経過時間契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 日時と経過時間契約
- probe: OPS-03-a
- 良い例: `observed_at: 2026-10-23T00:00:00Z`
- 悪い例: `タイムゾーンのない日時を保存`

### OPS-04 HTML注入契約

- 軸: E8
- 決定: HTMLを外部通信なしに動かし、埋込JSONの山括弧とアンパサンドをUnicodeエスケープし、ログ表示をtextContentで実行する。
- 理由: HTML注入契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — HTML注入契約
- probe: OPS-04-a
- 良い例: `node.textContent = value`
- 悪い例: `node.innerHTML = value`

### OPS-05 出力分離契約

- 軸: X1
- 決定: 通常の記録hookのstdoutを空にし、--contextのUserPromptSubmit/SubagentStartだけはJSONのadditionalContextを返し、分析と導入のstdoutを保存先案内にし、診断をstderrへ出す。
- 理由: 出力分離契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 出力分離契約
- probe: OPS-05-a
- 良い例: `hookのstdoutは空`
- 悪い例: `stdoutへログのJSONを出す`

### OPS-06 成否未知と製品別一覧契約

- 軸: X3
- 決定: 製品別にイベント一覧を固定し、成否が明示されないPostToolUseをcompletedとし、観測不能な操作・推論・料金・トークン数を補完しない。
- 理由: 成否未知と製品別一覧契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: test — 成否未知と製品別一覧契約
- probe: OPS-06-a
- 良い例: `自由文の結果はcompleted`
- 悪い例: `結果にerrorがあれば失敗とする`

### OPS-07 明示された目的と対応の契約

- 軸: X3
- 決定: 目的はツール入力のdescriptionまたはActionIntentだけを使い、申告はsource・session・turn・agent・tool・入力指紋が全一致する5分以内の次の1操作へ対応させ、複数候補は対応不明、理由がない操作は未記録にする。
- 理由: 別操作の理由や後付けの推測を事実として表示しない。
- 出典: adr/0002-operation-purpose-results.md
- 強制: test — 目的のscope・一回性・期限・曖昧さの契約
- probe: OPS-07-a
- 良い例: `purpose_sourceとpurpose_evidenceを表示`
- 悪い例: `直前の文章から理由を推測して埋める`

## TEST テスト

### TEST-01 必須テストとguard

- 軸: F1〜F5
- 決定: テストを標準unittestと固定fixtureで実行し、境界・並行・前後対応・本文非保存・導入再実行・HTML注入を契約にし、外部サービスへ接続しない。
- 理由: 必須テストとguardで作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — 必須テストとguard
- probe: TEST-01-a
- 良い例: `一時ディレクトリで導入を検証`
- 悪い例: `本物の会話履歴と設定を書き換えてテスト`

## PROC 作業手順

### PROC-01 implの作業順序

- 軸: G1
- 決定: 該当パターンを読み、スキーマ・実装・テスト・説明の順に変更する。
- 理由: implの作業順序で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: doc — implの作業順序
- 機械化しない理由: 作業順序と報告の正確さは差分から観測できない。
- probe: なし
- 良い例: `スキーマを確認して実装とテストを変更`
- 悪い例: `独自のログ形式を先に作る`

### PROC-02 reviewの波及確認

- 軸: G2
- 決定: イベント変更はevent_model・record・analyze・スキーマ資料・fixtureを、指標変更は集計・HTML・指標定義を同じ差分で照合する。
- 理由: reviewの波及確認で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: review — reviewの波及確認
- 機械化しない理由: 資料をまたぐ変更の意味には差分の解釈が必要になる。
- probe: なし
- 良い例: `集計と画面と指標定義を照合`
- 悪い例: `分母を変えて説明を残す`

### PROC-03 reviewの互換性確認

- 軸: G3,G4,X2
- 決定: 既存キーの意味や型を変える場合はschema_versionを上げ移行方針をADRへ書き、規則を変える場合はADR・rules・検査・probe・見本を同期する。
- 理由: reviewの互換性確認で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: review — reviewの互換性確認
- 機械化しない理由: 資料をまたぐ変更の意味には差分の解釈が必要になる。
- probe: なし
- 良い例: `v2の移行方針をADRへ残す`
- 悪い例: `v1の時刻の意味だけを変える`

### PROC-04 AGENTSの完了条件

- 軸: G5
- 決定: 完了報告にcheck・probe・独立収束試験の実測値または実行不能理由を記載し、実機での確認範囲を明示する。
- 理由: AGENTSの完了条件で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: doc — AGENTSの完了条件
- 機械化しない理由: 作業順序と報告の正確さは差分から観測できない。
- probe: なし
- 良い例: `合成入力と実機確認の範囲を分ける`
- 悪い例: `未実施の収束試験を合格とする`

## TOOL 道具と自動化

### TOOL-01 guard.py

- 軸: H3
- 決定: 検査抑止コメント・テストskip・検査設定の緩和でcheckを通さない。
- 理由: guard.pyで作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — guard.py
- probe: TOOL-01-a
- 良い例: `検査失敗の原因を直す`
- 悪い例: `テストをskipして通す`

### TOOL-02 quality.py --fix

- 軸: H1
- 決定: 手書きファイルをUTF-8・LF・末尾改行1個・行末空白なし、JSONを2空白インデントに固定する。
- 理由: quality.py --fixで作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: format — quality.py --fix
- probe: TOOL-02-a
- 良い例: `LFと末尾改行を1個にする`
- 悪い例: `行末空白とCRLFを混在させる`

### TOOL-03 導入merge契約

- 軸: H2
- 決定: foundationの編集検査を維持し、配布用観測hookは製品別一覧へtimeout=3で設定し、導入再実行で既存hookを削除せず重複させない。ソースプロジェクトの両製品設定もcollectorへ接続し、接続漏れを検査する。
- 理由: 導入merge契約で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md、adr/0003-source-hook-wiring.md
- 強制: test — 導入merge契約
- probe: TOOL-03-a、TOOL-03-b
- 良い例: `既存hookを残して同じ設定を一度だけ足す`
- 悪い例: `settings.json全体を置換する`

### TOOL-04 AST互換構文とimport検査

- 軸: H4
- 決定: 実行依存をPython標準ライブラリ、構文を3.9互換に固定し、実行確認した版とOSを記録し、Windowsとcloudを対象外とする。
- 理由: AST互換構文とimport検査で作者ごとの実装差を検出する。
- 出典: research.md、adr/0001-machine-enforced-rules.md
- 強制: structure — AST互換構文とimport検査
- probe: TOOL-04-a
- 良い例: `標準ライブラリだけを使う`
- 悪い例: `未導入の外部パッケージをimportする`

## 対象外とした軸

| 軸 | 理由 |
|---|---|
