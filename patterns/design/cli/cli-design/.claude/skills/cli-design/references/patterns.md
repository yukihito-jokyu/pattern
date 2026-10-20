# パターン

実装用スキル `cli-design` の「1. 振り分け表」の各行に対応する手順である。節の番号は振り分け表と一致させる。コマンドは全部、基盤のルート（`Makefile` のあるディレクトリ）で実行する。

## 1. サブコマンドを持つ CLI を新しく設計する

- 使う場面：依頼が、何かを記録・管理する新しい CLI を求めている（操作が2つ以上）
- 見本：`specs/notes/cli.json`、`specs/notes/cli.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/cli.json` | `specs/notes/cli.json` | STR-01、STR-05、NAM-01〜07、CODE-01〜05、ERR-01、STATE-01、OPS-02〜04、OPS-06 |
  | 2 | `specs/<name>/cli.md` | `specs/notes/cli.md`（生成物） | STR-04 |

- 手順：
  1. 依頼から、CLI 名、名詞、名詞ごとの動詞、名詞ごとの項目（名前・型・`list`・`nullable`・`enum` の選択肢）を、スキルの2節の既定値表で書き出す
  2. `make new NAME=<name>`
  3. 名詞ごとに、動詞を `make command NAME=<name> NOUN=<名詞> VERB=<動詞>` で足す。識別子が `name` の名詞は、最初の `make command` に `KEY=name` を付ける
  4. 名詞ごとに、項目を `make field NAME=<name> NOUN=<名詞> FIELD=<項目名> TYPE=<型>` で足す（リストは `LIST=1`、null を許すなら `NULLABLE=1`、`enum` は `VALUES=<a,b,c>`）
  5. `cli.json` を開き、`TODO` を埋める。依頼が既定値を決めた項目だけ、`create` のオプションを `"required": false` とその `default` に変える（NAM-07）
  6. 依頼が求めた絞り込み（`list` の `--<項目>`）と標準のオプション（`--force` など）を足す。summary は CODE-04 の表の文にする
  7. `make fix`、`make check`
- この場面で間違えやすいこと：
  - 識別子が `id` の名詞の `create` に位置引数を足す（NAM-04。値は全部オプションで受け取る）
  - 依頼に無い項目・動詞・絞り込みを足す。足すのは依頼に出たものと、生成器が足すものだけ
  - 依頼が選択肢を列挙していない値を `enum` にする（`string` にする）

## 2. サブコマンドを持たない CLI を新しく設計する

- 使う場面：依頼が、1回の変換・集計・出力だけを行う新しい CLI を求めている（操作が1つ）
- 見本：`specs/count-words/cli.json`、`specs/count-words/cli.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/cli.json` | `specs/count-words/cli.json` | STR-05、NAM-01〜06、CODE-01〜05、ERR-01、STATE-01、OPS-02〜04、OPS-06 |
  | 2 | `specs/<name>/cli.md` | 生成物 | STR-04 |

- 手順：
  1. CLI 名を `<動詞>-<目的語の複数形>` にする（NAM-02）
  2. `make new NAME=<name> SINGLE=1`
  3. `cli.json` の `TODO` を埋める：CLI と `commands[0]` の summary（同じ文。CLI 名の最初の語を大文字にした語で始める）、入力（読むファイルは `file` の位置引数 `file`、複数を受け付けるなら `variadic`）、出力先（依頼が結果をファイルに書くことを求めたときだけ `-o/--output` を置く。求めていなければ置かず、stdout に書く）、`output`（OPS-04 の決定表）、型（1行の型）
  4. 位置引数とオプションの型・`exit_codes` を ERR-01 の決定表で決める（`file` の位置引数があれば `[0, 1, 2, 3]`）
  5. `make fix`、`make check`
- この場面で間違えやすいこと：
  - 入力と出力先を両方位置引数にする（CODE-03。ファイルに書くなら出力先は `-o/--output`）
  - 集計の結果を文章で返す（OPS-04。行の型を作って `list` にする）

## 3. 既存の CLI に名詞・動詞を足す

- 使う場面：依頼が、既存の CLI に新しい対象や操作（コマンド）を求めている
- 見本：`specs/notes/cli.json` の `tag`（識別子が `name`）と `note`（識別子が `id`）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/cli.json` | `specs/notes/cli.json` | STR-05、NAM-02、NAM-04、NAM-07、CODE-04、ERR-01、PROC-02、PROC-06 |
  | 2 | `specs/<name>/cli.md` | 生成物 | STR-04 |

- 手順：
  1. `make command NAME=<name> NOUN=<名詞> VERB=<動詞>`（新しい名詞で識別子が `name` なら `KEY=name`）
  2. 新しい名詞なら、項目を `make field` で足す（1節の4）
  3. 表に無い動詞なら、`summary` を `<動詞を大文字で始めた語> ` で始め、`output` を OPS-04 の決定表で、`exit_codes` を ERR-01 の決定表で決める
  4. `make fix`（版はマイナーが上がる）、`make check`
- この場面で間違えやすいこと：
  - 表の「使わない語」を動詞にする（`add`、`remove`、`show`。NAM-04）

## 4. 既存の名詞に項目を足す

- 使う場面：依頼が、既存の対象に新しい属性（期限、メモ、優先度など）を求めている
- 見本：`specs/notes/cli.json` の `note` の `tags`、`tag` の `color`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/cli.json` | `specs/notes/cli.json` | NAM-01、NAM-02、NAM-05、NAM-07、CODE-02、CODE-04、PROC-02、PROC-06 |
  | 2 | `specs/<name>/cli.md` | 生成物 | STR-04 |

- 手順：
  1. `make field NAME=<name> NOUN=<名詞> FIELD=<項目名> TYPE=<型>`（`LIST=1`・`NULLABLE=1`・`VALUES=`）。`create`・`edit` のオプション、`edit` の `--clear-<項目>`（`nullable`・`list`・`boolean` の項目）、`list` の `--sort` の選択肢が一緒に変わる
  2. 既存の CLI に必須の項目を足すと、`create` に必須のオプションが増えて互換性を壊す（PROC-06 のメジャー）。依頼が既定値を決めていればその `default` にし、決めていなければ `NULLABLE=1` にする
  3. 依頼が絞り込みを求めていれば、パターン5の手順1で `list` に足す
  4. `make fix`（版はマイナーが上がる）、`make check`
- この場面で間違えやすいこと：
  - 日付を `string` にして summary に形式を書く（CODE-02、CODE-05。`date` にする）
  - `date` の項目名を `<意味>_date`、`timestamp` を `<意味>_at` にしない（NAM-02）

## 5. オプション・環境変数を足す、summary を変える

- 使う場面：依頼が、既存のコマンドの絞り込み、標準のオプション（`--force`、`--output` など）、環境変数、説明の文の変更を求めている
- 見本：`specs/notes/cli.json` の `note list` の `--tag`、`specs/count-words/cli.json` の `COUNT_WORDS_MIN_LENGTH`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/cli.json` | 上の見本 | NAM-03、NAM-07、CODE-02〜05、STATE-01、OPS-02、PROC-06 |
  | 2 | `specs/<name>/cli.md` | 生成物 | STR-04 |

- 手順：
  1. 標準の意味のオプションは NAM-03 の表の名前と型で、項目に対応するオプションは NAM-07 の名前で足す。`list` の絞り込みは次の表で決める（型・`values` は項目と同じ、`default` は `null`、`required` は `false`。summary は CODE-04 の表の文）

     | 依頼の言い方 | 足すオプション | summary |
     |---|---|---|
     | 「〜が X のもの」「〜で絞り込む」（値の一致） | `--<項目>` | `Show only <nouns> with this <label>` |
     | 「〜以降」「〜まで」「〜より前」「期間」「〜以上」「〜以下」（範囲。`date`・`integer`・`number` の項目） | `--<項目>-from` と `--<項目>-to` の2つ組（片側だけを求められても両方） | `date` は `... with <label> on or after this`・`... on or before this`、数は `... of at least this`・`... of at most this` |

  2. 環境変数は、同じ名前のオプションがあるときだけ、型・`values`・`default` をそのオプションと同じにして足す（STATE-01）
  3. `make fix`、`make check`
- この場面で間違えやすいこと：
  - `--yes`・`--verbose` など表の「使わない名前」を使う（NAM-03）
  - 設定ファイルや秘密情報を環境変数で受け取る（STATE-01、OPS-02。秘密情報は `<名前>-file`）

## 6. 公開面を消す・名前や型を変える

- 使う場面：依頼が、コマンド・オプション・項目などの削除、名前や型の変更、必須の追加を求めている
- 見本：なし（ルールの PROC-06 と ADR のひな形 `docs/design/adr/_template.md`）
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/adr/<次の番号>-<題名>.md` | `_template.md` | PROC-06 |
  | 2 | `specs/<name>/cli.json` | — | PROC-06 と、変える要素のルール |
  | 3 | `specs/<name>/cli.md` | 生成物 | STR-04 |

- 手順：
  1. 変更がメジャーを上げることを、ユーザーに伝えて承認を得る。承認が得られない状況なら変更せず、報告に提案として書く
  2. ADR に、変えるもの・理由・承認を書く
  3. `cli.json` を変え、`make check` が示す版（`version を 'X.0.0' にする`）を `version` に書く。`make fix` はメジャーの版を書かない
  4. `make fix`、`make check`
- この場面で間違えやすいこと：
  - `released/` のファイルを直す（STR-04。リリース済みの仕様は変えない）

## 7. リリースする

- 使う場面：依頼が、仕様の版の確定・公開・リリースを求めている
- 見本：`specs/notes/released/1.0.0.json`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `specs/<name>/released/<version>.json` | `specs/notes/released/1.0.0.json` | STR-04、PROC-06 |

- 手順：
  1. `make check` を通す
  2. `make release NAME=<name>`
- この場面で間違えやすいこと：
  - 依頼がリリースを求めていないのに `make release` を回す。設計の依頼では回さない

## 8. 設計を実装する・適合テストをかける

- 使う場面：依頼が、この基盤の仕様を Go・Python・Node.js・Rust などで実装すること、または実装が仕様に合うかの確認を求めている
- 見本：`tools/clispec/tests/fixtures/notes_impl.py`、`tools/clispec/tests/fixtures/count_words_impl.py`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | 実装のリポジトリ（この基盤の外） | 上の見本 | DEP-02、DEP-03、DEP-04、ERR-02、ERR-03、OPS-01、OPS-03〜05、STATE-01、STATE-02、TEST-01 |

- 手順：
  1. `references/stdlib-mapping.md` の 1〜4.1 節と、実装する言語の節を読む
  2. `specs/<name>/cli.md` のヘルプの文面を定数として写す
  3. 共通の処理の順（stdlib-mapping.md の1節）で `main` を書く
  4. `make conform SPEC=specs/<name>/cli.json CMD="<実装の起動コマンドの絶対パス>"` を回し、全項目を通す
- この場面で間違えやすいこと：
  - 解析器の自動のヘルプ・usage・エラー文を使う（OPS-05、ERR-02）
  - 標準ライブラリ以外の解析器を使う（DEP-04）
  - 絞り込みの繰り返しを OR にする、`edit` のリストの値を置き換えずに足す、消した `id` を再利用する（STATE-02）

## 9. 検査ツールの Python・uv の版を上げる

- 使う場面：依頼が、検査ツールを動かす Python や uv の版を上げることを求めている
- 見本：`docs/design/adr/0003-python-and-uv.md`
- 作る・変えるファイル：

  | 順 | パス | 見本との対応 | 守るルール |
  |---|---|---|---|
  | 1 | `docs/design/research.md` の Python・uv の節 | 既存の節 | PROC-03 |
  | 2 | `.python-version` | — | TOOL-04 |
  | 3 | `docs/design/adr/0003-python-and-uv.md` に追記 | — | PROC-03 |

- 手順（PROC-03）：
  1. 新しい版をコマンドで確かめ、research.md を書き直す
  2. `.python-version` を変える（保護ファイル。ユーザーの承認が要る）
  3. `make check` と `python3 .foundation/bin/violation_probe.py --root .` を通す
  4. ADR 0003 に版と日付を追記する
- この場面で間違えやすいこと：
  - `Makefile` の `PYTHON` を `python3` に変えて動かす（TOOL-04）
