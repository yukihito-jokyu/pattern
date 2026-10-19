# 設定台帳の範囲と、JSONの保存先

台帳は「何を設定できるか」を配布側で管理するための情報、回答JSONは「利用者が何を選んだか」を保存する情報である。APIが実行時に読むのは.env等から渡された環境変数とGoコードで、回答JSONではない。

| ファイル | 内容 |
| --- | --- |
| settings.catalog.json | 318項目の意味、型、source/path、重要度と理由、変更可否、未設定時の動作 |
| coverage.json | 抽出する設定ファイルと全キー、対象外の範囲 |
| setup-answers.json（initで生成） | questionLevel、databaseTarget、settings、reviews、baseline、snapshot |

## 台帳と実ファイルの照合

scripts/settings_inventory.pyが、Compose・lint・VS Code・エージェント設定のYAML/JSONを読み、すべての値を抽出する。文字列だけの配列は一項目、辞書を含む配列は要素の各フィールドに分ける。EditorConfigの各項目、cmd/internalのテスト以外のGoファイルにあるパッケージ定数、固定ツールとGoの版・依存、APIとDB契約も記録する。API・DB契約は全体を一項目として保護する。環境変数はconfigとAPI検証スクリプトの読み取り箇所も照合する。

台帳はruntime/database/server/lint/editor/contract/verificationに分ける。変更可能178項目、初期設定では維持する140項目で、保護項目も台帳から除かない。重要のみは2項目、普通まで含めると9項目、すべてでは変更可能178項目が対象。新しいキーや定数が実ファイルにあり台帳にないときはcheckが失敗し、黙って対象外にしない。

未使用のOSS機能・未導入pluginの全API、処理手順、エラー変数、関数内のSQLや検証スクリプト内部の待機回数は、導入時の設定項目には含めない。対象にしていない新しい設定ファイルを導入する場合は、抽出範囲も保守時に追加する。

保守用のscripts/update-settings-catalog.pyは、設定を追加・変更した後に台帳を作り直す入口。利用者のsetupで実行して不足を隠すものではない。新しい項目を追加する際は、意味・型・分類理由・省略動作・変更可否を確認し、文書・テスト・coverageも更新する。実ファイルの値はsampleに保存するが、現在値は毎回実ファイルから読み、sampleで上書きしない。

## 質問と保存

initは.envがあればそこを読み、なければ.env.exampleを使う。任意キーがない場合はnullで記録する。親シェルの一時的な環境変数は回答へ取り込まない。databaseTargetは同梱DB(local)か既存DB(external)かを確認するための情報で、未回答のままでは適用しない。

reviewsはunanswered（未回答）、confirmed（最終値を確認）、retained（質問範囲外なので維持）、not-applicable（理由付き非該当）を区別する。not-applicableは既存DB利用時のComposeとDB_PORTに限り、元の値を保つ場合だけ認める。同梱DBではDATABASE_URLとComposeのポート・ユーザー・パスワード・DB名、healthcheck.testを照合する。既存ボリュームの移行や資格情報変更は実行しない。

スキルは値を質問しCLIを使う。JSONには318項目を保持するが、質問量は選んだ範囲と条件で減らす。保護項目は回答不要で、バージョン、API/DB契約、依存方向、エージェント権限などを変更しない。モジュール名の変更に連動するimport・lintの自プロジェクト参照は、意味を保ったまま同期する。

## 反映と再設定

applyは確認済みの値だけを.env・対象YAML/JSON・EditorConfig・Go定数へ反映する。YAML/JSONは値の位置だけを置換し、未変更部分のコメントと書式を保持する。配列全体を変更した場合はその配列をJSON形式のYAMLへ置換するため、変更した配列内のコメントは失われる。planで対象を確認する。Goはgofmtで整形する。

モジュール参照の同期対象はルートのgo.mod/規約・README/.golangci.ymlと、internal/cmd/docs/.claude/.agents/.vscode内のGo・Markdown・YAML・JSON。生成図HTML、バイナリ、.git、回答JSONは対象外。利用先で独自ディレクトリへ参照を追加した場合は別途確認する。

snapshotは対象ファイルのハッシュ。回答開始後に対象が変わっていれば古い回答を拒否する。適用後は現在値から新しい回答を作る。既存回答は上書きしない。途中の書き込み・gofmt失敗では変更済みファイルを復元するが、プロセス強制終了までは保証しない。

.envは引用符なしKEY=value形式。コメント・未知キー・省略キーを保持し、シェル展開は行わない。URLの特殊文字はエンコードする。plan/listはDB接続URL・Composeパスワード・資格情報を含むテンプレートの現在値を隠す。回答JSONと.envには秘密情報が残るため、Git・ZIP・Issueへ含めない。

CLIは型と項目、接続数・整形幅・同梱DBの整合を検証する。OSSの全設定組み合わせまでは検証しないので、適用後はmake test-setupとmake checkも実行する。外部サービス、DB接続、マイグレーションはapplyでは実行しない。

## 依存と出典

Python 3.10以上とPyYAML 6.0.3を仮想環境へ導入する。API本体のGo依存とは独立している。根拠は各台帳項目のsource/path、型は実ファイルの解析結果。各数値の採用理由が配布元にない場合は、既存規約であることと実際の動作を区別する。

- [Goのモジュールと依存](https://go.dev/doc/modules/managing-dependencies)
- [net/http.Server](https://pkg.go.dev/net/http#Server)
- [database/sql](https://pkg.go.dev/database/sql)
- [golangci-lintの設定](https://golangci-lint.run/docs/linters/configuration/)
- [Composeの変数補間](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [PostgreSQLの接続URI](https://www.postgresql.org/docs/16/libpq-connect.html#LIBPQ-CONNSTRING)
- [PyYAMLのsafe_load](https://pyyaml.org/wiki/PyYAMLDocumentation)

`ci.json`と`scripts/verify-ci.sh`は配布物のCI検証用です。アプリの導入設定とは分け、setup台帳の対象には含めません。CIで使う接続先などは環境変数で指定でき、未指定時は使い捨てのローカル検証用DB・ポートを使用します。
