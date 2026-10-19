---
name: setup
description: go-cleanのGoモジュール名とAPI・DB・lint・エディターの初期設定を、質問範囲を選んで確認しCLIで反映する。go.mod、scripts/setup.py、setup/settings.catalog.jsonがある配布先で使う。
---

# go-cleanのセットアップ

ZIP展開先の`go-clean/`を作業場所にする。READMEに従いPython仮想環境へrequirements-setup.txtの依存を導入する。準備が成功してから`python3 scripts/setup.py check`が成功することを確かめる。別プロジェクトやこのパターン集のルートへ適用しない。

1. 最初に質問範囲を選んでもらう。「重要のみ（推奨）」はモジュール名とDB接続先の2項目、「重要＋普通」は待受・DBポート・同梱DBの資格情報・DB接続数を含む9項目、「すべて」はログ・タイムアウト・lint・エディターを含む178項目。台帳全体は318項目で、変更不可の140項目も根拠と現在値を記録している。範囲外は現在値または未設定時の動作を維持する。対応するCLIのlevelはimportant、normal、advanced。
2. `python3 scripts/setup.py init --level important --out setup-answers.json`のように回答ファイルを作り、`python3 scripts/setup.py list --answers setup-answers.json --group runtime`等を区分ごとに使い、対象の質問・現在値・省略時の動作・理由・参照先を読む。既存回答は上書きせず別名を使う。全台帳は`list --level advanced`で確認できる。groupはruntime/database/server/lint/editor/contract/verification。editable=falseの項目はretainedのまま説明し、変更を質問しない。大きな配列やlint一覧は関連する設定をまとめて提示し、一括で現状維持する回答もその対象・値を確認してから記録する。
3. 台帳に沿って関連項目をまとめて質問する。回答JSONのdatabaseTargetをlocal（同梱DB）かexternal（既存DB）にする。未回答では適用できない。既存DBではDB_PORTとComposeの項目をnot-applicableとし、valueを現在値、reasonを非該当の理由にして維持する。同梱Composeの初期値はDB・ユーザー・パスワードがapp。変更するならDATABASE_URLとhealthcheck.testも追加確認して合わせる。既存ボリュームの資格情報はComposeの変更だけでは更新されないので、既存DBの移行を初期設定で行わない。既存DBを使う場合はDB_PORTを変えない。DB_PORTを変えるなら同梱DB用DATABASE_URLのポートも追加確認し、一方だけ変えない。待受を変えるならAPI_BASE_URLの検証先も必要に応じて追加確認する。待受の`:8080`は全インターフェース、ローカル限定は`127.0.0.1:8080`。LOG_LEVELはdebug/info/warn/error。
4. 回答ファイルのsettingsへ最終値を入れ、その値を確認したreviewsのstatusをconfirmed、valueを同じ値にする。範囲内で現在値を維持する場合も利用者へ示して確認する。範囲外はretainedのまま。範囲外を変更する必要があれば追加質問してconfirmedにする。未設定はnull、空文字はアプリの既定動作を使う設定として扱うが、DATABASE_URLは必須。推奨値や無回答を利用者の回答に置き換えない。
5. `python3 scripts/setup.py validate --answers setup-answers.json`、`plan`の順に実行し、変更対象・最終値・維持した項目を示して依頼された設定を`apply`する。各コマンドに同じ`--answers`を指定する。DBの資格情報は画面に再掲しない。planはDATABASE_URLとComposeのパスワードを隠すため、接続先のホスト・ポート・DB名だけを安全に要約する。回答ファイルと.envは秘密情報を含み得るのでZIP・Git・Issueに含めない。
6. `python3 scripts/setup.py check`、`make test-setup`、`make check`を順に実行する。準備失敗では後続を実行しない。ローカルDB起動・マイグレーション・API起動は利用者が選んだ接続先と依頼範囲に従いREADMEを使う。既存DBへ勝手にマイグレーションを適用しない。DBへの操作を行わなければ動作は未検証と報告する。

CLIはモジュール名をGoのimport・lint設定・同梱文書へ反映し、環境変数は`.env`へ、その他は台帳のsource/pathが指す箇所へ書く。Goファイルはgofmtで整形する。`.env.example`、バージョン、DB/API契約、依存方向の制約、エージェント権限は台帳に記録した上で変更不可。モジュール名に連動するimportの許可先だけは同じ意味を保って同期する。台帳の範囲と設定の参照先は`setup/sources.md`にある。

既存の.envは引用符なしKEY=value形式のみ扱い、コメント・未知のキーを保持する。特殊文字はURLエンコードする。シェル展開は行わない。手編集を検出したら適用せず、差分を確認して現在値から別名の回答を作り直す。適用後の変更も次回は現在値からinitする。公開・Git操作・外部サービス登録はsetupの依頼から推測しない。
