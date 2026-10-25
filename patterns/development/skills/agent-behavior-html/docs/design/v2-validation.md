# 操作・目的・結果の更新の検証

日付: 2026-10-24。変更の判断は[ADR 0002](adr/0002-operation-purpose-results.md)。

デモは42イベント・12操作・2セッションの合成ログ。目的あり8操作、未記録4操作、未対応の申告0件。認証処理の確認、テスト失敗、編集、再テスト成功を両製品の例として並べる。実測ログではない。

契約テストは19件。操作対象の抽出、既知の資格情報形式のマスク、UTF-8上限、ファイル本文の除外、自由文の成否を推測しないこと、目的のscope・一回性・期限・複数候補、目的CLI、開始hookのcontext、v1/v2混在を検証する。導入・ロック・前後対応・HTML注入の既存契約も維持する。

ソースの両製品設定にcollectorへの接続が無かったため、[ADR 0003](adr/0003-source-hook-wiring.md)で実設定を追加した。追加の2テストは設定の接続とin-place導入を検査する。生成された設定コマンドに合成stdinを渡し、両製品で目的付きの操作と成功結果がログへ入ることを確認する。実際の設定を切断する違反probeも追加する。

scripts/check_dashboard.cjsはDOMのスタブで配布HTMLのJavaScriptを実行する。操作カード・目的・期待結果・観測結果・未記録表示、目的/対象/結果の検索、目的の根拠表示とJSON保存、製品フィルター、空表示、UTC、ページ送りを検証する。

Playwrightの実ブラウザー起動は、この環境のmacOSがMachPortRendezvousの登録を拒否するため確認できない。権限を上げた起動とヘッドレス専用Chromiumでも同じ制約があった。任意で実行できる検証スクリプトはscripts/check_browser.cjsに置く。DOM検証をブラウザーの目視検証と扱わない。

Claudeの実セッション検証は利用者の指示により省略する。Codexは実起動を再試行し、Codex自身による12件のhook認識を確認した。すべて信頼待ちで、モデル要求もDNS/接続エラーにより終了したため、hook発火と実操作の記録は未確認。[実セッションの検証記録](codex-live-validation.md)を参照する。CLIの合成stdinによる両製品の記録・context・導入検証とは区別する。独立収束試験は前回の中止指示以後に再実施していない。

機械検査の最新結果は[validation-results.json](../../.foundation/validation-results.json)、違反検出は[probe-results.json](../../.foundation/probe-results.json)に保存する。検証範囲を超える実機動作は保証として報告しない。
