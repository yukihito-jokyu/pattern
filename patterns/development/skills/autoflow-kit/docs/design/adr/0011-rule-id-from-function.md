# 0011 H1・H2 の規則の id を判定の関数名から決める

- 状態：採用
- 関係するルール：GATE-01

## 背景

H1・H2 の規則は、`policy.py` の `H1_RULES`・`H2_RULES` に「id、文、判定の関数」の組で足す（GATE-01）。規則の id は、`gates.md`、実行の記録（`trail.jsonl` の H2 の理由）、テストのメソッド名 `test_<id>` に現れる。

収束テストの2ラウンド目で、同じ依頼（受け入れ条件が全部「人が確かめる」なら H1 を起こす）を受けた3人が、判定の関数は全員 `_is_human_only` と名付けたのに、id は2人が `h1_human_only`、1人が `h1_human_criteria` にした。実装用スキルの既定値は「依頼の語を英語の snake_case にした名前」で、関数名と id を別々に決めさせていたため、選択が2回起きていた。見本も、7つの規則のうち id と関数名が対応していたのは2つだけだった（`h1_dependency` と `_has_new_dependency` など）。

## 選択肢

| 選択肢 | 良い点 | 悪い点 |
|---|---|---|
| 既定値表の言い回しを細かくする | コードを変えない | 自然言語から名前を作る選択は残る。検査で縛れない |
| id を判定の関数名から決め、テストで縛る | 選択が関数名の1回になる。違反はテストで落ちる | 既存の5つの規則の id を改名する |
| 揺れを害の無いもの（R7）として受け入れる | 何も変えない | 人が読む id と記録が作者ごとに変わる |

## 決定

規則の id は、`h1_`・`h2_` に、判定の関数名から先頭の `_is_`・`_has_` を除いた名前をつなげたものにする（`_has_new_dependency` → `h1_new_dependency`）。`tests/test_policy.py` の `test_rule_ids_match_functions` で確かめる。

既存の規則は、関数名が意味を表しているほうに合わせて次のとおり改名した。

| 旧 id | 新 id | 判定の関数 |
|---|---|---|
| `h1_dependency` | `h1_new_dependency` | `_has_new_dependency` |
| `h1_scope` | `h1_wide_scope` | `_has_wide_scope`（旧 `_is_wide`） |
| `h1_always_human` | `h1_human_paths` | `_has_human_paths` |
| `h2_fix_attempts` | `h2_too_many_failures` | `_has_too_many_failures` |
| `h2_review_rounds` | `h2_too_many_open_rounds` | `_has_too_many_open_rounds` |

## 理由

2ラウンドで6人全員が同じ関数名を選んでおり、関数名は真偽値の名前の決まり（NAM-02 の `is_`・`has_`）があるぶん揺れにくい。id をそこから機械的に決めれば、選択が1回になり、テストで縛れる。

## 影響

規則を足す作者は、判定の関数名だけを決めればよい。配布前なので、改名した id を読み替える移行は要らない。配布後に id を変えるときは、古い実行の記録に旧 id が残るので、この ADR に対応表を足す。
