"""パターン保守用。実ファイルの設定を抽出する。setup利用時には実行しない。"""

import json
from pathlib import Path
import re

from settings_inventory import discover

root = Path(__file__).resolve().parent.parent
previous = json.loads((root / "setup/settings.catalog.json").read_text())
base = [e for e in previous if e["key"] in {"module", "DATABASE_URL", "APP_ADDR", "DB_PORT", "LOG_LEVEL", "API_BASE_URL"}]
if not any(e["key"] == "API_BASE_URL" for e in base):
    base.append({"key":"API_BASE_URL", "importance":"advanced", "importanceReason":"APIの検証先を変えるときだけ必要で、通常は既定のローカルAPIを使うため。", "question":"API動作確認の接続先URLを変更しますか？", "source":"scripts/verify-api.py", "default":"http://127.0.0.1:8080"})
for entry in base:
    entry.update(group="verification" if entry["key"] == "API_BASE_URL" else "runtime", editable=True, type="string", optional=entry["key"] in {"APP_ADDR", "DB_PORT", "LOG_LEVEL", "API_BASE_URL"})
    entry["meaning"] = {
        "module": "Goのimportとlintの自プロジェクト参照先をそろえる。",
        "DATABASE_URL": "APIとmigrateが接続するPostgreSQLのホスト・ポート・資格情報・DB名。",
        "APP_ADDR": "HTTPサーバーが接続を受け付けるインターフェースとポート。",
        "DB_PORT": "同梱PostgreSQLをホスト側へ公開するポート。DATABASE_URLとは別に使われる。",
        "API_BASE_URL": "make smokeが接続するHTTP APIのURL。サーバーの待受アドレスを変えた場合はこの検証先も合わせる。",
        "LOG_LEVEL": "標準出力へ出すJSONログの下限。debugほど多く、errorほど少なくなる。",
    }[entry["key"]]
    entry["unsetBehavior"] = "起動に必須。未設定なら起動を止める。" if entry["key"] == "DATABASE_URL" else ("go.modに必須。省略不可。" if entry["key"] == "module" else "省略・空文字では" + entry["default"] + "を使う。")

GROUPS = {
    "depguard": "filesが対象ファイル、allow/denyが許可・禁止するimport。list-modeが判定方式を決め、descが違反時の説明になる。",
    "forbidigo": "patternに一致する呼び出しを禁止し、msgを診断に出す。analyze-typesは同名の関数を型で区別する。",
    "copyloopvar": "check-aliasはループ変数を別名に写した場合も不要なコピーとして調べる。",
    "dupl": "thresholdは重複コードとして報告するトークン数の境界。小さいほど短い重複も拾う。",
    "embeddedstructfieldcheck": "empty-lineは埋め込みフィールドと通常フィールドの間の空行を要求する。",
    "errcheck": "check-blankはエラーを_に代入して捨てた場合も検査する。",
    "exhaustive": "checkでswitch/mapを対象にし、default-signifies-exhaustiveでdefault節を網羅済みと扱う。",
    "funcorder": "functionは公開関数を非公開関数より前へ置く並び順の検査を有効にする。",
    "gocognit": "min-complexity以上の認知的複雑度を持つ関数を報告する。深い分岐を分割する目安になる。",
    "gocritic": "enabled-tagsとenabled-checksで採用する指摘、disabled-checksで重複・矛盾する指摘を指定する。",
    "godox": "keywordsに挙げた作業メモをコードに残すと報告する。未完了の修正を持ち込まないための設定。",
    "gomoddirectives": "go.modに許可しないディレクティブを指定する。ツールやGo版を複数箇所で管理しないために使う。",
    "gomodguard_v2": "allowedは直接依存として採用する外部モジュールの一覧。他のモジュール追加をレビュー対象にする。",
    "govet": "enable-allですべての解析を有効にし、disableでこのテンプレートに採用しない解析を除外する。",
    "iface": "enableは同形interface、未使用interface、未使用メソッドの検査を選ぶ。",
    "ireturn": "allowはinterfaceを返してよい型の分類。errorや標準ライブラリのinterface等を例外にする。",
    "lll": "line-lengthは行長の上限、tab-widthはタブを何文字と数えるか。golinesの整形とそろえる。",
    "misspell": "localeは綴りの基準。USでは米国英語へそろえる。",
    "nestif": "min-complexity以上の入れ子になったifを報告し、分岐の分割を促す。",
    "nilnil": "detect-oppositeはnilと有効値の組み合わせに加え、値とエラーを同時に返す逆の組み合わせも検査する。",
    "nolintlint": "allow-unusedは不要な抑制、require-explanationは理由、require-specificは対象linterの指定を検査する。",
    "perfsprint": "err-errorはfmt.Sprintfでエラーを文字列化する箇所も簡潔な書き方にできるか調べる。",
    "reassign": "patternsに一致する他パッケージの変数への再代入を報告する。.*は全名を対象にする。",
    "revive": "rulesのnameで検査を選び、argumentsでその検査の許容範囲を指定する。ルール名と引数は対で扱う。",
    "sloglint": "構造化ログのキーと値の書式を統一する。kv-onlyはキー値形式、contextはcontextがある範囲での使用、forbidden-keysは標準フィールドとの衝突防止。",
    "staticcheck": "checksで解析セットを指定する。allを使い、-ST1000だけ除いてパッケージコメントを必須にしない。",
    "tagliatelle": "case.rules.jsonはJSONタグの命名、use-field-nameはGoフィールド名との対応を検査する。snakeはsnake_case。",
    "unqueryvet": "check-n1はN+1の疑い、check-tx-leaksはトランザクションの閉じ忘れを検査する。",
    "unused": "field-writes-are-usesは書き込むだけのフィールドを使用済みと数えるかを決める。falseでは未使用のまま扱う。",
    "usestdlibvars": "各項目は曜日・時刻書式・暗号方式・HTTP等の定数を標準ライブラリの名前へそろえる検査を選ぶ。",
    "usetesting": "各項目はテストのcontextや一時領域にtestingパッケージのAPIを使う検査を選ぶ。",
    "wrapcheck": "ignore-package-globsに一致する自プロジェクトのエラーは再ラップを要求せず、外部境界のエラーへ文脈を加える。",
    "wsl_v5": "空行を置く条件と許す省略を指定する。行数しきい値は短い分岐と長い分岐を区別する。",
}

CONSTANTS = {
    "maxOpenConns": "同時に開くDB接続の上限。0は上限なしなので、DB側の接続枠と合わせて決める。",
    "maxIdleConns": "再利用のため保持する待機接続の上限。0では待機接続を残さない。",
    "connMaxLifetime": "DB接続を再利用する最大時間。期限後に返却された接続を張り直す。",
    "pingTimeout": "起動時にPostgreSQLへ疎通確認する待ち時間。超過するとAPI起動を止める。",
    "readHeaderTimeout": "HTTPヘッダーを読み終えるまでの期限。ヘッダーだけを遅く送る接続を長時間待たない。",
    "readTimeout": "リクエスト全体の読み取り期限。大きな本文や遅い送信の許容時間になる。",
    "writeTimeout": "レスポンスを書き込む期限。処理時間を含むため、長い処理を持つ利用先では見直す。",
    "idleTimeout": "keep-aliveで次のリクエストを待つ時間。超過した未使用接続を閉じる。",
    "shutdownTimeout": "終了シグナル後に処理中のリクエストを待つ最大時間。超過したらShutdownがエラーを返す。",
    "maxBodyBytes": "JSON本文を読み取る最大バイト数。上限を超えた読み取りはエラーになる。",
    "maxNameLength": "空白除去後の名前の最大文字数。DBのVARCHAR(50)とOpenAPIのmaxLengthとの同期が必要。",
    "codeInvalidArgument": "入力不正時の公開エラーコード。API仕様とクライアントの契約になる。",
}

entries = list(base)
for key, item in discover(root).items():
    file, path, value, adapter = item['source'], item['path'], item['value'], item['adapter']
    group = 'lint' if file == '.golangci.yml' else ('database' if file == 'compose.yaml' or file.endswith('database.go') else 'server' if file.startswith('cmd/') or file.endswith('json.go') else 'editor' if file.startswith('.vscode') or file == '.editorconfig' else 'contract')
    meaning = ''
    editable = adapter != 'readonly' and file != '.claude/settings.json' and file != 'internal/adapter/handler/error.go' and file != 'internal/domain/user/user.go'
    reason = '通常の導入では現在値で動作し、規約や実行条件を調整する場合に確認するため。'
    importance = 'advanced'
    if adapter == 'constant':
        meaning = CONSTANTS[path[0]]
        if path[0] in {'maxOpenConns', 'maxIdleConns'}:
            importance, reason = 'normal', 'DB側の接続枠とアプリケーションの並列処理数に合わせて調整するため。'
    elif file == '.golangci.yml':
        if path[:2] == ['linters', 'settings']:
            meaning = GROUPS.get(path[2], '')
        elif path[:2] == ['linters', 'enable']:
            meaning = '有効にする追加linter。各ルールの意味と正常・違反例は説明ページのlint詳細に対応する。'
        elif path[:2] == ['linters', 'default']:
            meaning = '追加linterの前に適用する標準セット。standardはerrcheck/govet/ineffassign/staticcheck/unused。'
        elif path[:2] == ['linters', 'exclusions']:
            meaning = 'generatedは生成コードの扱い、presetsは既知の誤検出、rulesは特定の場所・診断だけを除く条件、pathsは対象外パスを決める。path/path-except、linters、text/sourceを組み合わせる。'
        elif path[:1] == ['formatters']:
            meaning = 'enableは整形器、settingsはその幅・import順・書き換え規則、exclusionsは整形から外すファイルを指定する。gofumptで基本書式、goimportsでimport、golinesで120文字へ折り返す。'
        else:
            meaning, editable = 'golangci-lint設定ファイルの形式バージョン。v2形式で読むことを指定する。', False
        if path[:3] in [['linters','settings','depguard'],['linters','settings','forbidigo'],['linters','settings','gomodguard_v2']] or path[:2] == ['linters','exclusions']:
            editable = False
            reason = '依存方向・例外の許可は設計上の制約。初期設定で弱めず、規約変更としてコードと一緒にレビューするため。'
    elif file == 'compose.yaml':
        if path == ['services','db','image']:
            meaning, editable = '実行するPostgreSQLのイメージとメジャーバージョン。データ互換性を確認して更新する。', False
        elif 'environment' in path:
            meaning = '初回DB作成時のユーザー・パスワード・DB名。既存ボリュームの資格情報はこの値の変更だけでは変わらない。DATABASE_URLとhealthcheckも合わせる。'
            importance, reason = 'normal', '同梱DBの接続先をDATABASE_URLとそろえる必要があるため。'
        elif 'healthcheck' in path:
            meaning = 'testはDBの準備確認コマンド、intervalは間隔、timeoutは1回の期限、retriesは失敗を許す回数。make db-upの待ち条件になる。'
        elif 'ports' in path:
            meaning, editable = 'ホストのDB_PORTからコンテナの5432へ転送する。ホストポート変更はDB_PORTで行い、この補間式を維持する。', False
        elif 'volumes' in path:
            meaning, editable = 'DBファイルをdb-dataボリュームへ保存する。接続停止後も残る。初期設定で保存先を移すと別DBになるため維持する。', False
    elif file == '.vscode/settings.json':
        meaning = 'VS CodeのGo lint・保存時整形・改行設定。固定ツールのパスを使い、保存時に同じ整形を行う。API実行には影響しない。'
        if 'alternateTools' in str(path):
            editable = False
    elif file == '.vscode/extensions.json':
        meaning = 'チームへ推奨する拡張。Goの言語支援とEditorConfigの読み取りを案内し、自動インストールはしない。'
    elif file == '.editorconfig':
        meaning = 'エディターの文字コード・改行・インデント・末尾空白の規約。sectionが適用するファイルを絞る。GoとMakefileのタブは各ツールの書式に合わせる。'
    elif file == '.claude/settings.json':
        meaning = 'エージェントの操作権限。固定ツール経由の検証を許可し、グローバルツール・依存更新・.env読取を制限する。setupでは権限を増やさない。'
    elif file == 'Makefile':
        meaning = 'マイグレーションの配置とプロジェクト内ツールの固定バージョン。ツールパス・Goとの互換性を同時に確認して更新する。'
    elif key.startswith('go.'):
        meaning = 'APIのGoバージョンと依存モジュール。go.sumの検証結果と組で扱い、setupではアップグレードしない。'
    elif file.startswith('api/') or file.startswith('db/'):
        meaning = '公開APIまたは保存形式の契約。変更時はdomain・handler・repository・OpenAPI・マイグレーションを対応させる。'
    elif file == '.env.example':
        meaning = '初回.env作成用のサンプル。実際の利用先の値はruntimeの各項目で設定し、資格情報をこのサンプルへ保存しない。'
    elif file == 'requirements-setup.txt':
        meaning = 'setupのYAML解析用依存。API本体とは分離してPython仮想環境へ導入する。'
    if not meaning:
        raise RuntimeError('説明が未定義: ' + key)
    if not editable:
        reason = '初期設定では維持し、変更時は対応するコード・契約・規約を一緒に確認する必要があるため。' if reason.startswith('通常') else reason
    kind = 'boolean' if isinstance(value,bool) else 'integer' if isinstance(value,int) else 'array' if isinstance(value,(list,tuple)) else 'object' if isinstance(value,dict) else 'null' if value is None else 'string'
    entries.append({'key':key, **{k:v for k,v in item.items() if k!='value'}, 'sample':value, 'type':kind, 'group':group, 'importance':importance, 'importanceReason':reason, 'editable':editable, 'meaning':meaning, 'question':meaning + (' 現在値を維持しますか、変更しますか？' if editable else ' 初期設定では維持する。'), 'unsetBehavior':'このパターンでは明示設定。setupは削除せず、未変更なら元の値・書式を維持する。', **({'sensitive':True} if path[-1:] == ['POSTGRES_PASSWORD'] or file == '.env.example' else {})})
(root/'setup/settings.catalog.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
(root/'setup/coverage.json').write_text(json.dumps({'version':1,'surfaces':sorted({e['source'] for e in entries[len(base):]}),'keys':sorted(e['key'] for e in entries),'excluded':['GoのSQL定義・処理手順は設定項目ではなく、対応する実装節で説明する。','OSSの未使用機能・未導入pluginの全APIは対象外。']},ensure_ascii=False,indent=2)+'\n')
print('設定台帳:', len(entries), '項目; 変更可能:',sum(e['editable'] for e in entries))
