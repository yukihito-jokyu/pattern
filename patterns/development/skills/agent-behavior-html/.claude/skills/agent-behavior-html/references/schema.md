# イベントschema_version=1 / 2

1行1イベントのUTF-8 JSONL。新しい収集器はv2を書き、分析器はv1とv2の混在を読める。v1には操作内容・目的を後付けしない。正本は`scripts/event_model.py`の`EVENT_FIELDS`、`DETAIL_FIELDS`、`validate_event`。各versionで定義外のキーを拒否する。

| キー | 型 | 意味 |
|---|---|---|
| schema_version | int、1 / 2 | 互換性の境界 |
| event_id | string | UUID。分析時の重複排除に使う |
| observed_at | string | UTCのISO8601。hook入力を受けた後の収集時刻 |
| source | claude / codex | 入力元の製品 |
| event | string | 製品別一覧にあるhook名 |
| session_id | string | 製品のセッションID。安全な文字以外はハッシュ化 |
| turn_id | string / null | 製品が渡した場合のみ保存 |
| agent_id | string / null | 製品が渡した場合のみ保存。無い値をmainで埋めない |
| tool_use_id | string / null | ツール呼び出しID。無ければ前後の結合対象外 |
| tool_name | string / null | ツールイベントでは必須 |
| status | string | observed / started / completed / success / error |
| exit_code | int / null | PostToolUseの構造化応答が明示した場合のみ保存 |
| input_fingerprint | string / null | source＋tool_name＋正規化tool_inputのHMAC-SHA256。v2は説明用のdescriptionを除外 |
| input_bytes | int / null | 指紋対象の入力JSONのUTF-8バイト数。8MiB以下 |

v2だけに次のキーを追加する。文字列上限はUTF-8バイト数で、超過は末尾を省略する。

| キー | 型・上限 | 意味 |
|---|---|---|
| action | string / null、160byte | ツール名に対応した操作の種類 |
| target | string / null、2048byte | ファイルパス、コマンド、URL、検索条件。パッチは対象ファイルのヘッダーだけ |
| purpose | string / null、1024byte | 明示された短い目的・説明 |
| purpose_source | missing / tool_description / agent_intent | 未記録、ツール入力のdescription、操作前の申告 |
| expected | string / null、512byte | ActionIntentで申告した期待結果 |
| result_summary | string / null、2048byte | 観測された成否、終了コード、Bashの結果抜粋、明示失敗のエラー抜粋 |

ActionIntentは製品固有のhookではなく、`record.py --intent`が生成する目的の申告イベント。tool_name・tool_input・purposeが必須。tool_input自体は保存せず指紋へ変換する。tool_use_idはnullとする。

目的の対応条件はsource・session_id・turn_id・agent_id・tool_name・input_fingerprintの全一致。申告後5分以内の次のPreToolUseに1回だけ対応する。description以外の入力を一致させる。同時に候補が複数あれば特定せずambiguous、候補0ならツール入力のdescriptionを使い、それもなければ未記録とする。申告より前の操作や別セッションに遡って付与しない。

成否の決定順序は、PreToolUse→started、PostToolUseFailure→error、PostToolUseの`isError=true`または`is_error=true`→error、PostToolUseの整数`exit_code`→0ならsuccess・それ以外error、残るPostToolUse→completed、ツール以外→observedとする。テキストの単語から成否を決めない。Bashの非ゼロ終了は、応答が自由文だけならcompletedになる。

`.agent-logs/.fingerprint-key`は32byteのランダム鍵で、ログと同じ場所に600権限で保存する。鍵をHTML/JSONへ含めない。同じ導入先の同じ製品・ツール・入力を本文なしに比較できる。別プロジェクト・別鍵の指紋は比較できない。鍵変更で同一入力の集計が分かれる。鍵を失っても既存ログの分析はできる。

プロンプト、Read/Write/Editのファイル本文、会話履歴、作業ディレクトリ、transcript_pathを保存しない。transcript_pathを開く処理もない。コマンド、対象パス、短い説明、結果抜粋はv2で保存する。既知のtoken/password/API key/Authorization形式をマスクするが、任意の機密文字列を完全に検出するものではない。コマンドや出力へ直接書かれた内容は抜粋に含まれ得る。入力上限は8MiB、ログ1行上限は16KiB。記録失敗時は固定stderrと終了0で実行を継続する。

保存先は`<source>-<UTC日付>-<session_idのSHA256先頭32文字>.jsonl`。日をまたぐセッションは複数ファイルになる。分析時に同じsession_idで合流する。前後の対応キーはsource・session_id・tool_use_idで、agent_idが欠けた製品でも使える。複数の前イベント、複数の後イベント、ツール名の不一致はambiguousとする。
