# go-clean

ユーザー作成・取得APIで、HTTP、業務ルール、PostgreSQLを分けるGoのテンプレートです。`cmd/api/`が起動と組み立て、`internal/domain/`が入力のルール、`internal/usecase/`が処理手順、`internal/adapter/`がHTTP・SQLとの変換を担当します。

ZIPにはソース、DBマイグレーション、API仕様、設定台帳、setupスキル、テストを含みます。掲載サイトのNode.js環境は必要ありません。

## 環境と導入

macOSまたはLinuxのBash/zshを前提にしています。Go 1.27.1、Docker EngineとCompose v2、Make、Bash、curl、Perl、Python 3.10以上（venv・pipを利用可能）を用意します。Windowsの手順は未検証です。

ZIPを任意の場所へ展開し、`go-clean/`全体を利用先のリポジトリとして開きます。以降の作業場所はすべてこのディレクトリです。

```sh
cd go-clean
go mod download
make tools
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-setup.txt
python3 scripts/setup.py check
```

各コマンドが成功してから次へ進みます。準備に失敗したら停止して原因を解消してください。初回はネットワーク接続が必要です。Goはgo.mod/go.sum、setupはrequirements-setup.txtのPyYAML 6.0.3で依存を固定しています。golangci-lint v2.14.0とmigrate v4.20.1は`make tools`がプロジェクトの`bin/`へ導入します。

### setupスキルで設定する

`.agents/skills/`を認識するCodex等で、展開先を開いて`$setup`を指定します。本体は[.agents/skills/setup/SKILL.md](.agents/skills/setup/SKILL.md)です。質問範囲は次の3つです。

| 範囲 | 確認する内容 |
| --- | --- |
| 重要のみ / important | モジュール名・DB接続先の2項目 |
| 重要＋普通 / normal | 上記にAPI/DBポート、同梱DBの初期資格情報、DB接続数を加えた9項目 |
| すべて / advanced | ログ、タイムアウト、lint、エディター、API検証先を含む変更可能な178項目 |

台帳全体は318項目です。バージョン、API・DB契約、依存方向、権限など、初期設定では維持する140項目も台帳に含めています。範囲外は現在値・未設定時の動作を維持し、個別に確認した回答と区別します。既存DBを使うなら同梱Composeの項目は非該当とし、繰り返し質問しません。

CLIだけでも同じ操作ができます。

```sh
python3 scripts/setup.py init --level important --out setup-answers.json
python3 scripts/setup.py list --answers setup-answers.json --group runtime
```

回答JSONでは`databaseTarget`を`local`（同梱DB）か`external`（既存DB）にし、`settings`へ希望する値を入れます。次の例は、生成したJSONの一部です。他の項目・baseline・snapshotは残してください。

```json
{
  "databaseTarget": "local",
  "settings": {
    "module": "github.com/acme/user-api",
    "DATABASE_URL": "postgres://app:app@localhost:5432/app?sslmode=disable"
  },
  "reviews": {
    "module": {"status": "confirmed", "value": "github.com/acme/user-api"},
    "DATABASE_URL": {"status": "confirmed", "value": "postgres://app:app@localhost:5432/app?sslmode=disable"}
  }
}
```

質問した項目は、最終値を確認して`reviews`をconfirmedにします。範囲外はretainedのまま維持します。範囲外を変更する場合は追加確認してconfirmedにします。既存DB利用で同梱DBの質問が不要な場合は、例えば`reviews.DB_PORT`を`{"status":"not-applicable","value":"5432","reason":"既存DBを使うため"}`と記録し、値を変えません。valueは実際の元の値に合わせます。未回答・確認後の変更・非該当なのに変更した値は拒否します。

```sh
python3 scripts/setup.py validate --answers setup-answers.json
python3 scripts/setup.py plan --answers setup-answers.json
python3 scripts/setup.py apply --answers setup-answers.json
python3 scripts/setup.py check
```

planで変更ファイル・設定値・維持項目を見てからapplyします。DATABASE_URLとComposeのパスワードは画面に出しません。モジュール名はGoのimportとlintの自プロジェクト参照も同期し、その他の値は台帳が指す設定・定数へ反映します。変更したGoファイルにはgofmtを実行します。DBの起動やマイグレーションは実行しません。

既存.envのコメント・未知のキー・省略された任意キーは保持します。対象値は引用符なしKEY=value形式に対応し、特殊文字を含むパスワードは接続URL内でエンコードします。任意キーのnullは未設定、空文字は既定動作、DATABASE_URLは必須です。回答JSONと.envは秘密情報を含み得るため、Git・ZIP・Issueへ含めないでください。

適用前に手編集を検出した場合は上書きせず停止します。差分を確認し、現在値から別名の回答を作り直します。再設定時もinitから始めます。途中の書き込み・整形の失敗では変更済みファイルを復元しますが、プロセス強制終了までは保証しません。

全台帳は`list --level advanced`、区分別なら`--group database`等で確認できます。groupはruntime/database/server/lint/editor/contract/verificationです。意味・型・重要度・変更可否・参照先は[setup/settings.catalog.json](setup/settings.catalog.json)、照合範囲は[setup/coverage.json](setup/coverage.json)、保存と反映の仕組みは[setup/sources.md](setup/sources.md)にあります。

### 手動で最小構成を試す場合

setupを使う代わりの手順です。setup適用済みなら実行しません。

```sh
make rename MODULE=github.com/acme/user-api
cp .env.example .env
```

## 使用方法

同梱DBの初期値はユーザー・パスワード・DB名がapp、DB公開ポートが5432、APIが8080です。変更するならDATABASE_URLの値も合わせます。同梱DBではsetupが接続URL・Compose・healthcheckの一致を確認します。既存ボリュームの資格情報はComposeの初期化設定だけでは変更されません。

同梱DBを使う場合、次を順に実行します。

```sh
make db-up
make migrate-up
make run
```

既存DBを選んだ場合は`make db-up`を使わず、マイグレーションの要否もそのDBの管理手順に従います。DBの準備やマイグレーションに失敗したら、APIを起動しないでください。

別ターミナルからユーザーを作成し、返ったIDで取得します。次のURLは初期ポートの例です。変更した場合は合わせてください。

```sh
CREATED_USER="$(curl -fsS -X POST http://localhost:8080/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"  Taro  ","email":"TARO@example.com"}')"
printf '%s\n' "$CREATED_USER"
USER_ID="$(printf '%s' "$CREATED_USER" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl -i "http://localhost:8080/users/$USER_ID"
```

作成は201と`id`・`name`・`email`・`created_at`を返し、名前はTaro、メールはtaro@example.comになります。取得は200で同じユーザーを返します。同じメールで再作成すると409です。終了時はAPIをCtrl+Cで止め、`make db-down`でDBを停止します。ボリュームのデータは残ります。

## 検証

準備が成功し、Python仮想環境を有効にした状態で実行します。

```sh
make test-setup
make check
make test
make check-deps
```

- test-setup：一時コピーで、全設定の台帳照合、質問範囲、範囲外維持、未回答・古い回答・未確認変更の拒否、反映、再適用、失敗時復元を確認する。全テストのOKを期待する。
- check：build → vet → domain/usecaseのテスト → lint。すべて成功し、lintの最後に`0 issues.`を期待する。
- test：race検出付きのGoテスト。DBは不要。
- check-deps：一時コピーへdomainからnet/httpへのimportを追加し、depguardが拒否することを確認する。`rejected by depguard`を期待する。

専用の検証用DBでマイグレーションとAPI起動が成功した後、別ターミナルから実行します。

```sh
API_BASE_URL=http://127.0.0.1:8080 make smoke
```

API_BASE_URLは実際の待受に合わせます。healthz、作成・取得、正規化、重複409、不正入力400、未知フィールド400、不正ID400、未登録ID404を確認し、成功時は`API smoke: ... passed`、失敗時は非0で終了します。検証ごとに一意なメールで1件保存するため、運用DBでは実行しません。マイグレーションの巻き戻しは、検証用DBに限って`make migrate-down`（users削除）→`make migrate-up`で確認します。

## 制約

認証・認可はありません。app:app、TLS無効、DB公開ポートはローカル開発用です。公開運用ではアクセス制限と資格情報・TLSを整える必要があります。

名前の50文字上限はdomain・DB・API仕様にありますが、メールの254文字上限はDBだけです。長いメールがdomainを通ると保存時に500になる可能性があります。JSONは未知項目を拒否し読み取りを1MiBに制限しますが、末尾に別のJSONが続くかは検査していません。healthzはHTTP応答の確認で、起動後のDB疎通は確認しません。これらの契約変更はsetupでは扱いません。

## 詳しい説明

- [docs/architecture.md](docs/architecture.md)：層と設計判断
- [docs/coding-rules.md](docs/coding-rules.md)：層ごとの書き方
- [docs/adding-a-feature.md](docs/adding-a-feature.md)：機能追加の手順
- [docs/lint-rules.html](docs/lint-rules.html)：lintの正常・違反例
- [AGENTS.md](AGENTS.md)：作業ルール
