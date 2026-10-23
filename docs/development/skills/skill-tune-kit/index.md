---
title: 評価データでスキルを改善するskill-tune-kit
description: Claude Codeの既存スキルを学習用・検証用・テスト用のケースで評価し、独立した4役で改善候補の作成と採否を進める構成。
slug: /development/skills/skill-tune-kit
pattern:
  features:
    - label: 改善対象
      value: 既存スキルの文書と参照ファイル
    - label: 評価
      value: 学習・検証・テストを分離
    - label: 採否
      value: 検証用の成績で機械判定
---

# 評価データでスキルを改善するskill-tune-kit

スキルの指示を直したとき、手元の例だけが良くなり、別の依頼では悪くなることがあります。skill-tune-kitは、Claude Codeの既存スキルを評価データで測り、改善の根拠に使うケースと、候補の採否を決めるケースを分ける道具です。

ここでいう学習は、学習役が`SKILL.md`や参照ファイルを改善することです。モデルの重みは更新しません。正解があるなら正解との一致、正解が1つに決まらないなら人と決めた評価項目で測ります。成績が改善した候補だけを残し、最後に使っていなかったテスト用のケースで元の版と比較します。得られるのは選んだ評価データでの結果であり、あらゆる依頼で品質が上がる保証ではありません。

## 全体像

ZIPには利用先へ入れる配布物と、その配布物自体を検査する道具を収録します。

```text
skill-tune-kit/
  install.py                         利用先へコピーする入口
  kit/
    .tune/tune.py                     補助CLI
    .tune/tune_kit/                   計画・評価・学習・採否・報告
    .tune/templates/prompts/          4役へ渡すプロンプトのひな形
    claude/skills/skill-tune/          人が呼ぶスキルと形式の説明
    claude/agents/                    実行・採点・学習・監査の4役
  tests/                             一時fixtureで流れを確かめるテスト
  .foundation/                       構造・ルール・違反例の検査
  docs/design/                       設計・ADR・移行元の検証記録
  Makefile、pyproject.toml            固定版の検査ツールと設定
  ci.json、verify-ci.sh               ZIP単体の準備・検証
```

`install.py`は`kit/.tune/`を利用先の`.tune/`、`kit/claude/`を`.claude/`へコピーします。開発用の検査設定や設計文書を利用先へ入れることはありません。導入後は`.claude/skills/skill-tune/SKILL.md`が人とのやり取りを受け持ち、`.tune/tune.py status`が次の処理を指定します。

利用先の`.tune/targets/<target-id>/`には`plan.json`、`dataset/`、`versions/v0/`以降のスキルの写し、`results/`、`rounds/`、最終の`report.md`が残ります。`v0`は承認時の元の版、`v1`以降は学習役が直す候補です。実行用の作業場所は`.tune/work/`に分け、こちらだけを`.gitignore`へ追加します。計画と評価結果を後から辿れるように残す構成です。

### 人と4つの役をつなぐ

`kit/claude/skills/skill-tune/SKILL.md`の実際のfrontmatterです。

```yaml
name: skill-tune
description: 既存の Claude Code スキルを評価データで改善する。正解データがあれば学習用・検証用・テスト用に分け、無ければ人と評価項目を決め、独立した学習と検証のラウンドを回し、最後にテスト用で測って報告する。
disable-model-invocation: true
allowed-tools: Bash(python3 .tune/tune.py *)
argument-hint: <target-id> [対象スキルのディレクトリ]
```

`name`は`/skill-tune`という呼び出し名、`description`は用途の説明です。`disable-model-invocation: true`で自動起動を止め、人が改善を始める入口にします。`argument-hint`は入力時のヒントで、本文の`$ARGUMENTS`からtarget IDと対象スキルの場所を読みます。`allowed-tools`は補助CLIの呼び出しを事前許可する指定で、ほかのツールを禁止する指定ではありません。これらの意味と`.claude/skills/<名前>/SKILL.md`という配置は[Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills)に対応します。1つの入口へまとめた理由は同梱の`docs/design/adr/0004-one-human-invoked-skill.md`にあります。

4役は`kit/claude/agents/`に定義します。

| 役 | 受け取るものと成果物 | 分離する理由 |
| --- | --- | --- |
| `tune-executor` | スキルの写しと1ケースの入力を受け、sandboxで依頼を実行し`response.md`を書く | 正解を見て答えを作ることを避ける |
| `tune-grader` | 返答・成果物と`judge`の項目を受け、合否と根拠を`grade.json`へ書く | 学習役自身による採点を避ける |
| `tune-learner` | 学習用の証拠と現在・候補のスキルを受け、候補を直して`proposal.json`を書く | 検証用とテスト用に合わせた修正を避ける |
| `tune-auditor` | 失敗を点検して、原因とデータ修正案を`audit.json`へ書く | 誤った正解や検査をスキルの失敗として扱い続けない |

例えば`kit/claude/agents/tune-grader.md`は次の設定です。

```yaml
name: tune-grader
description: skill-tune の採点役。版を知らされずに、1件の返答を評価項目ごとに採点し、合否と根拠を grade.json に書く。skill-tune の status が示す job からだけ起動する。
tools: Read, Write, Glob, Grep
omitClaudeMd: true
```

`tools`は役が使えるツールを絞ります。採点役と監査役は上の4ツール、学習役はそれに`Edit`、実行役は`Read, Write, Edit, Glob, Grep, Bash`を使います。全役から`Skill`と`Agent`を外し、別の手順やエージェントを自分で起動させない設計です。`omitClaudeMd: true`は採点・学習・監査役に付け、利用先の指示が判定へ混ざるのを避けます。実行役には付けず、実際に使う条件へ近づけます。モデル指定はなく、呼び出し側の設定を引き継ぎます。配置・`tools`・`omitClaudeMd`・モデル省略時の意味は[サブエージェント仕様](https://code.claude.com/docs/en/sub-agents)で確認できます。

役の独立性は、与える証拠とプロンプト、出力検査で支えます。読めるパスをOSで隔離する実装ではないため、指示に反した閲覧まで防げると扱いません。

### statusが次の処理を決める

`kit/.tune/tune_kit/status.py`では、進み具合を別の状態ファイルへ書かず、計画・承認・結果・提案の有無やハッシュから次の手を求めます。スキルは次の行の意味に従って動き、1つ終わるたびに`status`へ戻ります。

| 行 | スキルが行うこと |
| --- | --- |
| `対象:`、`ラウンド:`、`段階:` | 現在地を人へ伝える |
| `問題:` | 計画を直し、再検査する |
| `次: python3 .tune/tune.py ...` | 指定のCLIを実行する |
| `job <役> <ラベル> <プロンプト>` | 指定の役へプロンプトを渡す |
| `その後:` | 全jobの出力がそろってから実行する |
| `承認なら:`、`適用するなら:`、`適用しないなら:` | 人の回答に合う処理を実行する |

最初に`init`で計画を作り、`check-plan`で形式・分割・起動回数を確認して、人が`plan.md`を承認します。`approve`は計画とデータのハッシュを記録し、元のスキルを`v0`へ保存します。その後、`eval-prepare`が作業場所とjobを作り、`eval-collect`が返答と差分を回収し、`eval-score`が検査結果をまとめます。

最初の学習用・検証用の評価が終わると、`audit`と`audit-check`で失敗を点検し、`data-fix`で人が選んだデータ修正を適用するか、修正なしにします。次に`learn`と`learn-check`で候補を作成・検査し、候補を同じ手順で評価して`decide`で採否を決めます。段を飛ばすとCLIが不足する成果物を示すので、役が独自に進行を決める必要を減らせます。

## 計画とケースから評価を作る

### plan.jsonで固定すること

`kit/.tune/tune_kit/plan.py`の`build_skeleton`が作る初期値です。

```python
def build_skeleton(target_id: str, skill_path: str) -> dict[str, object]:
    """init が書く plan.json のひな形。goal、mode、checks は人と決めて埋める。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {"id": target_id, "skill_path": skill_path},
        "goal": "",
        "mode": "",
        "sandbox": CASE_SANDBOX,
        "split": {"seed": DEFAULT_SEED, "ratios": {TRAIN: 0.6, VAL: 0.2, TEST: 0.2}},
        "checks": [],
        "budget": {"runs_per_case": 1, "max_rounds": 3, "patience": 2, "parallel": 4},
    }
```

定数は`SCHEMA_VERSION = 1`、`CASE_SANDBOX = "case"`、`DEFAULT_SEED = "skill-tune"`、`TRAIN/VAL/TEST = "train"/"val"/"test"`です。`goal`と`mode`が空のままでは評価を始められません。ひな形の値と、省略できる項目の既定値を混同しないことが大切です。planの最上位8項目は全て必須で、未知のキーも検出します。

| 項目 | 値・範囲と、処理へのつながり |
| --- | --- |
| `schema_version` | `1`。形式の版が違う計画を混ぜないために検査する |
| `target.id` | CLIの`--target`と同じID。小文字の英数字で始まる64文字以内の英数字・ハイフン。記録の置き場を識別する |
| `target.skill_path` | `SKILL.md`を持つ対象ディレクトリ。通常は利用先ルートからの相対パス。実装の`layout.skill_dir`は絶対パスも解決する。承認時の保存元と最終適用先になる |
| `goal` | 空でない文字列。何を達成するスキルかを人と定め、学習役・監査役へ渡す |
| `mode` | `reference`は正解データと比較。`criteria`は人と決めた評価項目を使い、計画の`checks`に`judge`を1つ以上必要とする |
| `sandbox` | `case`はケースの入力を空の作業場所へコピー。`repo`はリポジトリの写しに入力を重ねる。既存コードを読む・直すスキルでは後者を選ぶ |
| `split.seed` | 空でない文字列。ひな形は`skill-tune`。IDのハッシュと組み合わせ、同じケースを同じ分割へ戻せるようにする |
| `split.ratios.train/val/test` | 全て正の数で合計1。ひな形は`0.6/0.2/0.2`。比率から目標件数を計算する |
| `checks` | 全ケースに当てる検査の配列。`groups`を指定した検査は対象groupだけへ適用。ケース固有の検査と合成する |
| `budget.runs_per_case` | 整数1〜5、ひな形1。同じケースを複数回実行して出力の揺れを率で測る。回数分だけ実行が増える |
| `budget.max_rounds` | 整数1〜10、ひな形3。改善ループの回数上限 |
| `budget.patience` | 整数1〜10かつmax_rounds以下、ひな形2。不採用がこの回数続くと停止 |
| `budget.parallel` | 整数1〜10、ひな形4。statusが一度に案内するjob数を抑える |

3分割と採否の理由は同梱ADR 0007・0008にあります。数値の比率・予算上限は移行元の設定を維持しています。各数値の個別の比較実験や最適値を選んだ記録は未特定なので、利用先のケース数や費用に応じて計画時に調整します。

`repo`でも全ファイルをコピーするわけではありません。`fsops.DEFAULT_SKIP`にある`.git`・`.tune`・仮想環境・`node_modules`・各種キャッシュと、ルート直下の`dist/build/coverage/target`を除き、ディレクトリのシンボリックリンクも追いません。これにより履歴や改善作業の再帰コピーを避けます。一方、必要な入力まで除外名の下にある場合は作業場所に届かないため、ケースの入力へ用意します。sandboxはコマンドが実行される作業場所であり、ネットワークやプロセス権限を隔離する機能ではありません。

### cases.jsonで入力と期待結果を結ぶ

`kit/claude/skills/skill-tune/references/plan-schema.md`の形式に沿ったケース例です。入力を`dataset/files/memo-slash/input/files/memo.txt`へ置き、内容を「2026/1/5 に打ち合わせ。次回は 2026/2/10。」とします。実行時はsandbox直下の`files/memo.txt`へコピーされるので、依頼と検査もそのパスへそろえます。

```json
{
  "cases": [
    {
      "id": "memo-slash",
      "group": "memo",
      "prompt": "files/memo.txt の日付を ISO 8601 にそろえてください",
      "expected": "2026-01-05 に打ち合わせ。次回は 2026-02-10。",
      "checks": [
        {"id": "K1", "kind": "equals", "severity": "must", "target": "file:files/memo.txt"}
      ],
      "note": "スラッシュ区切りの日付"
    }
  ]
}
```

この例は、更新後の`files/memo.txt`を`expected`の文字列と比較します。依頼、入力先、検査対象が同じファイルを指すので、表記の変換がファイルへ反映されたことを測れます。この1件だけでは3分割できないため、実際の計画には少なくとも3件を用意します。

| ケースの項目 | 意味と、省略したときの動作 |
| --- | --- |
| `id` | 必須。全ケースで一意、小文字の英数字で始まる64文字以内の英数字・ハイフン。入力ファイルと結果のディレクトリ名に使う |
| `group` | 同じ形式の名前で入力の種類を表す。省略・空なら`default`。分割で種類を偏らせないために使う |
| `split` | 省略・空なら自動分割。`train`・`val`・`test`ならその分割に固定する |
| `prompt` | 必須の空でない依頼文。実行役へ渡す |
| `expected` | 正解の文字列か`null`（省略もnull扱い）。referenceでは文字列必須。ファイルだけが正解なら空文字にしてexpectedディレクトリへ実ファイルを置く。criteriaでは正解を持たなければnullにする |
| `checks` | ケース固有の検査。省略は空配列。計画の検査に追加し、`groups`は指定しない |
| `note` | 人向けの説明。省略は空文字で、実行役・採点役へ渡さない |

入力は`dataset/files/<id>/input/`、正解ファイルは同じケースの`expected/`へ配置します。正解ファイルは実行役に渡さず、検査の`expected_file`で参照します。全ケースに適用する検査と固有の検査を合わせて、各ケースには`must`が1つ以上必要です。referenceでは今のスキルが出した結果をそのまま正解にせず、人の成果物や決まった変換規則から正解を作ります。誤りを正解として固定しないためです。

ケースは3件未満で検査エラー、10件未満で警告です。少数のgroupは検証用・テスト用へ1件も入らない場合があるので、`plan.md`の分割表と警告を読みます。似た入力の言い換えを別の分割へ散らすと暗記でも良い成績になるため、重複を避け、必要なら`split`で同じ分割へ固定します。同じgroupにするだけでは同じ分割には固定されません。

### 検査の共通項目と8種類の判定

`kit/.tune/tune_kit/plan.py`は検査に使えるキーを次のように定義します。

```python
CHECK_KEYS = ("id", "kind", "severity", "groups", "target", "value", "pattern", "expected_file", "run", "criterion")
CHECK_FLAGS = ("use_expected",)
```

`id`は英字で始まる32文字以内の英数字・`_`・`-`で、1ケースに当たる検査内で重複させません。`kind`と`severity`も必須です。`must`の不合格はその実行のケース不合格になり、`should`の不合格は検査の通過率へ反映します。`target`は省略で`response`、ファイルなら`file:<sandboxからの相対パス>`です。`groups`の省略は全group、`use_expected`の省略はfalseで、その他の文字列の省略は空文字です。種類に必要な項目が空なら検査エラーになります。

`checks.KINDS`から生成される`references/check-kinds.md`が8種類の正本です。種類によって使える項目が異なるので、不要な項目を付けても検査エラーになります。

| kind | 項目と具体的な判定 |
| --- | --- |
| `contains` | 必須の`value`を含むか。任意の`target`を指定でき、NFKC正規化と空白の圧縮後に比較する。全角数字や改行の違いを吸収する |
| `not_contains` | 同じ比較方法で必須の`value`を含まないか。禁止語などに使う。`target`は任意 |
| `regex` | 必須の`pattern`にPythonの`re.search`・複数行モードで一致するか。`target`は任意で、表記の形式を測る |
| `equals` | 正解と文字列が等しいか。NFKC、改行統一、行末空白・前後の空行除去後に比較。任意の`value`、`expected_file`、ケースの`expected`の順で空でない指定を優先し、最後はexpectedへ戻る。`target`は任意 |
| `json_equals` | equalsと同じ正解の選び方で、JSONとして読み取った値を比較。キー順と空白は問わない。`value`もJSONを表す文字列として書く |
| `exists` | 必須の`target`で指定したファイルが存在するか。`response`は使わず`file:`で指定する |
| `command` | 必須の`run`をsandboxでシェル実行し、終了コード0なら合格。300秒で打ち切り。`target`は指定しない |
| `judge` | 必須の`criterion`を採点役が二値判定。任意の`use_expected: true`で正解文字列・正解ファイルも見せる。`target`は指定しない |

例えば`{"id":"K1","kind":"contains","severity":"must","value":"2026-01-05"}`は返答にこの日付があるかを機械判定します。意味の妥当性を測る`judge`では「分かりやすい」だけでなく「返答の最初の段落に変更の目的が書かれている」のような観測できる条件を書きます。機械で決まる条件を機械に任せ、曖昧さが残る部分だけ採点役へ渡すと、採点の揺れを減らせます。

`expected_file`とファイルtargetは絶対パス・`..`・バックスラッシュを含めません。expected_fileの基準はそのケースの`expected/`です。これらは評価ファイルを正しい場所から読むための形式検査であり、`command`をOSで隔離する制限ではありません。

## 学習・検証・テストを分けて候補を選ぶ

### 決定的な分割と承認

`kit/.tune/tune_kit/splitting.py`は`sha256(seed + ":" + case_id)`で各group内の順序を決め、groupを均等に混ぜた列を目標件数へ配ります。検証用とテスト用の目標は`round(総数 × 比率)`で最低1件、学習用は残りで最低1件になるよう調整します。分割固定のケースは先に割り当て、自動分割は残りの枠を使います。結果に空の分割があれば計画検査で検出します。

既定で10件なら目標は学習6件・検証2件・テスト2件です。同じseed・ID・group・固定指定なら同じ分割に戻せるため、候補を変えるたびに評価対象まで変わることを避けます。承認後に`plan.json`や`dataset/`を変えると、ハッシュが一致せず評価段階が止まります。再検査・再承認すれば、内容の変わったケースだけ古い結果として再評価し、テスト用が変わった事実も承認記録と報告へ残ります。

### 監査と学習の範囲

`audit`は失敗の原因を`skill`（スキル）、`expected`（正解）、`check`（検査）、`input`（入力）へ分けます。監査役は修正の提案だけを書き、人が選んだ指摘だけを`data-fix --apply`で反映します。修正しない場合も`--none`で記録して次へ進みます。評価データを書き換えて成績を上げたことを、スキル改善と混同しないためです。最後のテスト監査ではデータを直さず、疑わしい点を報告します。

`learn.py`の証拠取得は学習用に絞っています。

```python
results = workspace.load_results(where, approved, current, (plan.TRAIN,))
cases = approved.list_cases(plan.TRAIN)
```

学習役にはこの証拠と計画の共通検査、改善履歴、現在の版・候補の場所を渡し、候補だけを直させます。`learn-check`は宣言した変更と実際の変更の一致、`SKILL.md`の存在、frontmatterの`name`不変、500行以内を確認します。さらに正規化後20文字以上の検証用・テスト用の文が追加行へ写っていれば差し戻します。学習用の写しは警告です。短い断片や意味の言い換えまで検出する仕組みではないため、データ漏えいを完全に証明する検査とは扱いません。

### 検証用の成績で採否を決める

`kit/.tune/tune_kit/metrics.py`は、全`must`に通った実行を合格とし、ケースごとの合格割合を平均して「合格率」を計算します。「検査の通過率」は全実行・全検査のうち通った割合です。同じケースを3回解いて2回合格なら、そのケースの合格割合は2/3になります。

候補の採否は学習用の成績から切り離して決めます。

```python
if regressions:
    reason = f"検証用で退行したケースがある（{', '.join(regressions)}）"
    return Decision(adopted=False, reason=reason, regressions=regressions, overfit=improved_train)
if candidate_val.pass_rate > current_val.pass_rate:
    return Decision(adopted=True, reason="検証用の合格率が上がった", regressions=(), overfit=False)
```

ここでの退行は、現在の版で全実行が合格だったケースが、候補では全実行不合格になることです。退行があれば全体の率が上がっても不採用です。退行がなければ検証用の合格率が上がった候補を採り、合格率が同じときだけ検査の通過率の上昇で採ります。どちらも上がらなければ不採用です。学習用だけ改善した不採用候補は、合わせすぎの疑いとして記録します。複数回実行で100%から50%へ下がるケースは、この実装の退行条件には入りません。

例えば現在の検証2ケースが「合格・不合格」、候補が「合格・合格」なら合格率50%から100%で採用します。「不合格・合格」への入れ替わりなら、全体は50%のままでも元の合格ケースが退行しているため不採用です。これは規則を説明する例で、実モデルの実測結果ではありません。

### 停止、最後の評価、適用

`workspace.compute_stop_reason`は、検証用の全ケース・全検査が合格、最大ラウンド到達、直近patience回が連続不採用、のいずれかでループを止めます。採用された最後の候補を最良の版とし、採用がなければ`v0`を維持します。

その後で元の版と最良の版だけをテスト用で評価します。ここでいう最後の1回は、計画の`runs_per_case`で定めた実行を含む最終評価です。結果を見てさらに候補を学習させるループには戻しません。`report`はテスト用の成績、各ラウンドの採否、データ修正履歴、テスト監査を`report.md`へまとめます。

人が報告と差分を読み、`apply`か`apply --skip`を選びます。`apply`は対象スキルのディレクトリを最良の版で置き換えますが、承認時から対象スキルが変わっていれば上書きを拒み、手動取り込みを案内します。見送りなら対象は変えず候補を残します。採用された候補自体がなければ適用するものはなく、そのまま終了します。

## 導入・使用方法

利用にはPython 3.9以上、Git、Claude Codeが必要で、CLIはPythonの標準ライブラリだけで動きます。ZIPを展開し、`README.md`のある`skill-tune-kit/`で利用先を指定します。

```bash
python3 install.py /path/to/your-repository
```

同じコピー先が1つでも存在すると、何もコピーせず`.gitignore`も変えず終了コード1で止まります。更新時に既存ファイルの上書きを意図する場合は、差分を確認して`--force`を付けます。利用先のルートでClaude Codeを起動し、既存のスキルを指定します。

```text
/skill-tune date-format .claude/skills/date-format
```

スキルがゴール・ケース・検査・予算を人とまとめ、`plan.md`を提示します。以降はstatusの指示に沿って進みます。途中の確認だけなら利用先ルートで次を実行します。

```bash
python3 .tune/tune.py status --target date-format
```

Claude Code側のツール実行権限は利用先セッションに従います。このZIPは権限を一括変更する設定を利用先へ入れません。特に実行役のBashと`command`検査はコマンドを実行するため、計画の内容と利用先の許可範囲を確認します。

## 検証方法と結果

確認日は2026-10-23です。今回の移行では、配布CLI、プロンプト、4役、計画スキーマ、分割と採否、既存テストを維持し、ZIPでの再現手順を追加しました。ローカル提供の0.1.0を元にし、外部取得元・元コミット・ライセンスは未特定です。

`ci.json`は次の設定です。

```json
{
  "command": ["bash", "verify-ci.sh"],
  "pythonVersion": "3.12"
}
```

ZIP展開先で`bash verify-ci.sh`を実行します。macOSまたはLinux、Bash、make、Git、venv・pipを含むPython、パッケージ取得用のネットワークが必要です。スクリプトは一時venvへ`uv==0.11.14`を準備し、`make check`を実行します。Makefileがruff 0.17.1とmypy 1.20.2を固定して呼ぶため、サイトのNode.js依存とは独立します。uvの版指定は[公式のツール実行仕様](https://docs.astral.sh/uv/guides/tools/#requesting-specific-versions)に対応します。準備が失敗したら後続は実行しません。

続けて、生成文書の手編集・学習用以外の証拠混入・抑止コメントという3種類の違反を一時コピーへ挿入し、想定の理由で検査が失敗することを確かめます。最後に別の一時ディレクトリへ導入し、配布物の一致、重複導入時の無変更、導入先CLIの起動を確認します。成功時は最終行に`ZIP検証: 全検査・代表的な違反3件の検出・導入検証に成功`が出ます。

既存テストは、役の出力をfixtureで用意して、計画承認から学習、候補評価、最終評価、報告、適用・見送りまでを確認します。学習役への証拠の限定、承認後の改変検出、検証用の退行による不採用、データ修正の選択待ちも含みます。実モデルで改善ループを回すテストではありません。

今回、macOS arm64、Python 3.15.0、Git 2.50.1、GNU Make 3.81で、生成ZIPを一時展開して上記スクリプトを実行し、終了コード0を確認しました。固定版uvの導入、整形53ファイル、型検査49ファイル、既存104テスト、構造・生成文書・guard・ルール対応の検査が成功しました。代表的な違反3件は全て想定の失敗を検出し、新規導入36ファイル・重複導入時の無変更・導入先CLI起動も成功しています。最初はネットワーク制約で準備が停止したため後続を実行せず、パッケージ取得可能な環境で同じ手順を再実行した結果です。

CI指定のPython 3.12とLinux、実モデルによる通し実行、Claude Codeでの実際の権限挙動、人間による説明の分かりやすさの確認は今回未実施です。同梱の`docs/design/e2e-run.md`・`research.md`・`convergence-report.md`と`.foundation/probe-results.json`は移行元の記録で、今回の成功を示す資料ではありません。キャッシュと`.foundation/convergence/`の作業記録はZIPへ収録していないため、その生データはZIP単体から再確認できません。

## 参考資料

- [Claude Codeのスキル](https://code.claude.com/docs/en/skills)：配置、frontmatter、引数の仕様。
- [Claude Codeのサブエージェント](https://code.claude.com/docs/en/sub-agents)：役の定義と使えるツールの指定。
- [uvのツール実行](https://docs.astral.sh/uv/guides/tools/)：検査ツールを版指定で動かす方法。
- ZIP内の`docs/design/architecture.md`、`adr/0007-train-val-test-split.md`、`adr/0008-mechanical-adoption.md`、`adr/0009-data-fix-with-human-approval.md`：分割・採否・人がデータ修正を選ぶ設計の根拠。

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/skills/skill-tune-kit.zip)
