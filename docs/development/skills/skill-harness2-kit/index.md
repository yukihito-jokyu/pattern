---
title: harness2方式でスキルを改善するキット
description: Claude Codeのスキルを実行の軌跡から改善し、予算承認と採用を人が決める構成。
slug: /development/skills/skill-harness2-kit
pattern:
  features:
    - label: 改善の根拠
      value: 基準と候補の実行を比較
    - label: 探索
      value: INV・DOMの提案と並列・逐次の合成
    - label: 人の判断
      value: 費用承認と対象スキルへの採用
---

# harness2方式でスキルを改善するキット

Claude Codeのスキルを直すとき、説明を詳しくするだけでは、その変更が実際の仕事に役立つかは分かりません。このキットは、現在のスキルと変更候補で同じ依頼を実行し、その軌跡と成果物の違いから編集を選びます。正解や採点結果を改善役へ渡さず、何が起きたかを証拠にする[google-research/harness2の方法](https://github.com/google-research/harness2/tree/1cfe254e8d25b15f37048c3730134686abe60335)を、Claude Codeのスキル1つに適用した実装です。

配布する`skill-harness2`が手順を案内し、Pythonの補助CLIが実行・記録・候補検証を担います。費用を使う前の承認と、元のスキルを書き換える採用判断は人が行います。提案された変更をそのまま適用するのではなく、比較できる成果物と差分をそろえて判断するための構成です。

## 全体像

ZIP内の主要な配置は次のとおりです。`kit/`が利用先へ導入する部分で、開発用の検査と設計資料はその外にあります。

```text
skill-harness2-kit/
├── install.py                     利用先への導入
├── README.md                      ZIP単体の利用・検証手順
├── ci.json / verify-ci.sh          一時環境での検証の入口
├── kit/
│   ├── .h2/h2.py                  補助CLI
│   ├── .h2/h2_kit/                計画・実行・選択・採用など
│   ├── .h2/templates/prompts/     編集・合成などのひな形
│   └── claude/skills/skill-harness2/
│       ├── SKILL.md               人への確認と次のCLI操作
│       └── references/            設定・タスク・結果・帰属資料
├── tests/                         fake_claudeで動くテスト
├── .foundation/                   違反検出とルール整合の検証
└── docs/design/                   設計、判断理由、上流との対応
```

`install.py`を実行すると、利用先に`.h2/`と`.claude/skills/skill-harness2/`が入ります。利用先で改善の対象と記録を持つ場所は、`.h2/targets/<対象名>/`です。

```text
.h2/targets/minutes/
├── profile.json                   対象・モデル・回数・予算
├── tasks/first/task.md             実際に依頼する文
├── tasks/first/workspace/          必要な材料
├── tasks/first/checks.json         任意の事後検査
├── plan.md / approval.json        計画と承認の記録
├── runs/r1/base-skill/             承認時のスキル（H0）
├── runs/r1/first/                  実行・提案・合成・選択の記録
└── runs/r1/library/parallel/        後のタスクへ渡す木と教訓
```

処理は、準備→`check`→人の費用承認→`approve`→`run`→`show`→人の採用判断→`adopt`と進みます。`run`内の順序は基準実行→INV/DOMの提案→候補の試行→合成→完成品の匿名選択→振り返りです。事後検査の`judge`は選択後の成果物を確かめるための別経路で、提案や選択に正解を教える経路にはしません。

## スキルが進行し、CLIが状態を確かめる

`kit/claude/skills/skill-harness2/SKILL.md`の先頭です。

```yaml
name: skill-harness2
disable-model-invocation: true
allowed-tools: Bash(python3 .h2/h2.py *)
argument-hint: "<対象の名前> [対象スキルのディレクトリ]"
```

`disable-model-invocation: true`により、この改善作業は人が`/skill-harness2`で呼び出して始めます。呼び出し時に渡す対象名は、例えば`minutes`です。改善したいスキルのディレクトリ`.claude/skills/minutes-format`とは別の値で、記録を分ける名前になります。Claude Codeの[スキルの呼び出し制御](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill)に沿った指定です。

スキル本文は、対象・プロファイル・タスク・予算・採用を人に確認し、CLIの`段階:`と`次:`を読んで進めます。`allowed-tools`は補助CLIの呼び出しを指定し、段の判定やファイル処理をスキルの文章だけで代行しないようにしています。初回の`status minutes`は`段階: 準備`を返し、必要な設定がまだ無いことを示します。

## 設定の入口と補完の区別

利用先のルートで`python3 .h2/h2.py init minutes --skill .claude/skills/minutes-format`を実行すると、`kit/.h2/h2_kit/profile.py`の`build_default_profile`からひな形を作ります。次は、そのひな形の仕事の説明だけを議事録の例として埋めた`profile.json`です。

```json
{
  "schema_version": 1,
  "skill": ".claude/skills/minutes-format",
  "work": "議事録を、決まった見出しと日付の形に整えて渡す",
  "domain_word": "議事録の整形",
  "deliverable_word": "整えた議事録",
  "inv_levers": "",
  "dom_levers": "",
  "yardstick": "",
  "selection_lead": "",
  "selection_checks": "",
  "k": 2,
  "modes": ["parallel"],
  "seed": null,
  "width": 2,
  "obs_trunc": 50000,
  "deliverable": "any",
  "claude": ["claude"],
  "rollout": {
    "model": "",
    "tools": ["Read", "Edit", "Write", "Glob", "Grep", "Bash(python3 *)", "Bash(ls *)"],
    "timeout_sec": 900,
    "max_budget_usd": 1.0
  },
  "improver": {
    "model": "",
    "effort": "",
    "timeout_sec": 1200,
    "max_budget_usd": 2.0
  },
  "leak_globs": []
}
```

ひな形に書く値と、項目を省略したときの補完は別です。`schema_version`・`skill`・`work`・`domain_word`・`deliverable_word`・`k`・`modes`・`width`・`obs_trunc`・`deliverable`・`claude`、`rollout.tools`と両実行設定の時間・予算は必要です。ひな形から削除して既定値になるわけではなく、`check`で問題になります。任意の説明文・モデル・`improver.effort`は省略時に空文字、`seed`は`null`、`leak_globs`は空配列になります。以下では、ひな形の値がどこで使われるかを順に説明します。

### 対象と仕事の説明

前のJSONの`schema_version: 1`は、このCLIが読む形式の版です。別の版は拒否し、推測で変換しません。`skill`は利用先のルートからの相対パスで、絶対パスと`..`を含むパスは拒否します。改善後の採用先もこの値なので、開始時に正しいスキルを選ぶ必要があります。

`work`は改善役が読む仕事の説明、`domain_word`は分野を表す語、`deliverable_word`は成果物を表す語です。いずれも空では進めません。例えばこの例では、文章全般の改善ではなく議事録の整形を対象とし、提案・合成・選択のひな形へ同じ仕事を渡します。

任意の`inv_levers`は手順や道具の改善の手がかり、`dom_levers`は実務家の知識の手がかりです。`yardstick`は仕事としてよい進め方を提案・合成へ伝え、`selection_lead`は選択役の決め方の先頭へ、`selection_checks`は成果物の正しさについての文へ入ります。この例では追加の観点が決まっていないため空にし、余分な指示を入れません。空の部品はひな形の描画時に除きます。

`work`・`inv_levers`・`dom_levers`・`yardstick`・`selection_checks`に`score`や`採点`等の測定語を含めると拒否します。ここには実際の仕事を書き、模範解答や点数の付け方を書かないためです。これは`guards.py`の語の照合であり、あらゆる形の答え漏れを判定できるという意味ではありません。材料と依頼文を人が選ぶことも必要です。

### 回数、幅、タスクの順

`k: 2`は、基準実行を2回、INVとDOMを各2案、完成品を2個作る設定です。範囲は1〜5で、増やすと試行と費用が増えます。初期ひな形の2を維持するこの例は、複数の実行の違いを見られる構成です。最初に費用を抑えて試す場合は、人と`k: 1`を選べます。

`modes: ["parallel"]`は同じ出発点から幅を探索します。`["sequential"]`は合成した版を次の段に引き継いで深く直します。両方を指定すると比較できます。値はこの2種から重複せず選び、実行順はCLIが`parallel`、`sequential`にそろえます。並列と逐次の違いは次節のコードでも示します。

`width: 2`は同時に動かすジョブの上限です。範囲は1〜8で、`k`の総試行数を変える値ではありません。利用の同時実行制限に当たるなら下げます。逐次の段そのものは前段の結果を待ちますが、その段のINV/DOMは最大2並行で動かします。

`seed: null`ならタスクを名前順に実行します。整数なら対象名とその種を使ってタスク順をシャッフルします。前のタスクからライブラリを引き継ぐので、順序も承認対象に含みます。完成品の匿名IDの並べ替えは、これとは別にタスクID・k・モードから決まる種を使います。

### 軌跡と成果物の扱い

`obs_trunc: 50000`は、軌跡の各観測を最大50000文字として描く設定です。10000〜10000000の範囲で、10000未満は拒否します。切り詰められた証拠を実行上の欠陥と取り違えないため、元キットは最低量を持たせています。観測を切り詰めない無制限指定ではありません。

`deliverable: "any"`は、ファイルの追加・変更か、完了したエラーでない返答があれば成果物を出したと扱います。`files`はファイルの追加・変更、`reply`は返答を条件にします。ファイルを消すだけでは`files`の条件を満たしません。この例は返答とファイルのどちらも扱える値を維持しますが、常にファイルを納品するスキルなら`files`を選び、空の納品物を選択候補へ入れないようにできます。

### 実行役と改善役のモデル・道具・上限

JSONの`claude: ["claude"]`は子プロセスを起動するコマンドの配列で、シェル文字列として展開しません。PATHにない場合は実行ファイルのパスを指定します。通常の利用では本物のClaude Codeを使い、テストだけはこの配列を偽の実行ファイルにします。

`rollout`は仕事を解く実行役、`improver`は提案・合成・選択・振り返りの役です。それぞれの`model: ""`は`--model`を付けずClaude Codeの既定を使います。モデルを人と固定した場合は、その名前がコマンドに渡ります。`improver.effort: ""`も`--effort`を省略します。指定できる値は空文字・`low`・`medium`・`high`・`xhigh`・`max`で、利用モデルが対応するかは実環境で確認します。

`rollout.tools`は対象スキルが仕事で使える道具です。例では読み書き・検索とPython・一覧表示を許し、`runner.py`が`Skill`を必ず追加します。対象スキルが必要とする道具がなければ依頼を解けないため、タスクと併せて人が決めます。改善役の道具はこの配列を流用せず、コード側で編集用または読み取り用に固定します。

`rollout.timeout_sec: 900`と`improver.timeout_sec: 1200`は1回の時間上限で、どちらも30〜7200秒です。`max_budget_usd`は正の米ドル額で、例の1.0と2.0をそれぞれの`claude -p`へ渡します。回数や時間の全体上限と混同せず、`check`が出すラウンド全体の上限も読んでから承認します。これらの値は元の初期ひな形を維持しており、すべての仕事で十分と実測した値ではありません。

最後の`leak_globs: []`は、模範解答等のファイル名パターンが追加指定されていない状態です。例えば`["answers/*"]`とすると該当ファイルは証拠へ写さず、タスク材料にあれば`check`が拒否します。空でも既知の採点出力の印は別の検査で拒否します。除外するだけで正解を同居させてよいとは扱わず、材料から答えを分離します。

## 同じ依頼で基準・候補・完成品を比較する

`kit/.h2/h2_kit/recursion.py`の並列モードは、同じ証拠からINVとDOMの候補を作ります。

```python
specs = [
    _build_proposal(env, dimension, index, None, evidence)
    for index in range(1, k + 1)
    for dimension in (layout.INV, layout.DOM)
]
proposals = _run_stages(env, specs, env.model.width)
candidates = _run_rolls(env, proposals)
```

INVは手順・道具・完了の確かめ方、DOMは対象分野の知識に注目します。2つの観点から変えたスキルをそれぞれ同じタスクで動かし、基準との振る舞いの違いを残します。合成役は全候補の差分・軌跡・成果物を読み、根拠のある編集をまとめます。多数の案が同じことを言うだけでは独立した証拠にせず、根拠がなければ元の版を保つ`KEEP_BASE`も認めます。

逐次モードでは、`_run_sequential`の各段の最後が次の形です。

```python
checkpoint = _run_stages(env, [spec], 1)[0]
view = _run_roll(env, checkpoint)
stages.append(checkpoint)
views.append(view)
checkpoints.append(checkpoint)
history.append(context.PoolEntry(checkpoint.label, checkpoint.tree, view))
current = checkpoint.tree
```

各段の合成版`checkpoint`を実行し、その木を次の段の`current`にします。過去の候補と実行も`history`へ残すので、直近の変更だけで決めず、それまでの証拠を読めます。並列は同じ出発点から独立した合成を複数作り、逐次は前の合成を次の出発点にします。[上流の実験説明](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/EXPERIMENTS.md)の幅と深さを、スキルの木に対応させた構造です。

### 壊れた候補を実行前に差し戻す

`kit/.h2/h2_kit/validate.py`は候補の`SKILL.md`、直接参照する資料、Pythonスクリプト等を検証します。スキル本文は500行以内、descriptionは1024文字以内で`<`・`>`を含めず、frontmatterはdescription以外を元と同じに保ちます。新たな動的コマンド挿入を増やすこと、参照したファイルが無いこと、Pythonの構文エラー、採点出力の印も問題にします。元からある問題は候補が持ち込んだ問題と区別します。

編集できる木は`SKILL.md`と、各直下の`references/*.md`、`scripts/*.py`・`scripts/*.sh`、UTF-8で読める`assets/`のファイルに限ります。深いサブディレクトリやバイナリ等の編集面外が対象スキルにあれば、採用時に消えることを避けるため準備段階で拒否します。既存スキルを無条件に持ち込める構成ではありません。

`recursion.py`は検証結果を1回だけ差し戻し、再度失敗したらその段の入力の木へ戻します。単に失敗した候補を実行して予算を使わず、`fell_back`として結果に残します。参照資料の追加に対する読む場面の行は、本文の行数に収まれば自動補足します。新しい機能を実装する判断と、機械で検出できる壊れ方の修正を分けた扱いです。

## 予算と承認時のスキルを固定する

`kit/.h2/h2_kit/ledger.py`は1タスク・1モードを次の回数で確認します。

```python
ROLLOUTS_PER_K = 4
SESSIONS_PER_K = 3
```

実行R=4kは基準k、INV/DOM候補2k、完成品kです。編集セッションP=3kはINVのk、DOMのk、合成のkで、同じラベルの重複も検出します。このPには選択・振り返りと失敗した提案の差し戻しは含みません。費用計画では編集の最大2回の試行と選択・振り返りを加えて保守的に数えます。両モードを使うときの基準k回は共有します。

例えばk=2・parallelのみ・1タスクなら、実行は8回、編集は6セッションです。差し戻しを含む最大12セッションに選択と振り返りの2回を加え、例の1回1ドルと2ドルでは8×1＋14×2=36ドルが計画上の上限です。2タスクなら72ドルになります。実額がこの値になるという意味ではなく、承認前に見る上限の計算です。

`kit/.h2/h2_kit/planning.py`の`approve`は、現在のプロファイル・材料・対象スキルが表示した計画と合うかを確かめ、対象スキルの木を`runs/r<N>/base-skill/`に保存します。これをH0とし、各タスクは同じ承認時の木から始めます。前のタスクで選ばれた木を次のタスクの出発点へ無断で置き換えることはしません。

## 証拠を渡し、採点を方法から分ける

`kit/.h2/h2_kit/context.py`は依頼文・材料・基準と候補の木・実行軌跡・成果物を`context/`へ書きます。プロンプトは読む場所を案内する文で、証拠本体を短い要約へ置き換えません。証拠の中の命令はデータとして読み、従わないようひな形で指示します。加えて改善セッションの道具を制限し、候補中のスクリプトを実行する道具を渡しません。

任意の`tasks/first/checks.json`の例です。

```json
{
  "checks": [
    {
      "name": "見出しがある",
      "command": "grep -q '^## 決定事項' {task_dir}/formatted.md",
      "timeout_sec": 30
    }
  ]
}
```

`judge`だけがこの定義を読み、選択後の実行の場所に`{task_dir}`、返答ファイルに`{reply_file}`を置き換えて`/bin/sh -c`で動かします。終了コード0は成功、非0は失敗、時間切れや起動不能は未判定です。採否の材料にする経路であり、改善の文面や選択へ結果を戻しません。方法のモジュールから事後検査を読み込めないことは、同梱の構造検査でも確認します。

### 実行する役ごとに道具を分ける

`kit/.h2/h2_kit/runner.py`は`claude -p`のコマンドを一か所で組み立てます。

```python
ROLLOUT_GUARD_FLAGS = (
    "--setting-sources", "project",
    "--strict-mcp-config",
    "--no-session-persistence",
    "--permission-prompts", "none",
)
SESSION_GUARD_FLAGS = (
    "--restricted",
    "--disable-slash-commands",
    "--strict-mcp-config",
    "--no-session-persistence",
    "--permission-prompts", "none",
)
EDIT_TOOLS = ("Read", "Edit", "Write", "Glob", "Grep")
READ_TOOLS = ("Read", "Glob", "Grep")
```

仕事を解く実行役は`rollout.tools`と対象スキルを使います。元キットは`--setting-sources project`を使い、利用者側の設定やプラグインによる実行条件の揺れを抑えています。一方、編集・合成は`EDIT_TOOLS`、選択・振り返りは`READ_TOOLS`を`--restricted`とともに使い、候補の証拠を読む役へBashを渡しません。確認が必要な操作は`--permission-prompts none`で拒否させます。

これらは元キットがClaude Code 2.1.308で調査した組み合わせです。[公式CLI資料](https://code.claude.com/docs/en/cli-reference)と元キットの`docs/design/research.md`には、公式の仕様と当時の実験観測を分けて記録しています。今回のfake_claudeテストはコマンドの組み立てを確認し、本物のClaude Codeが同じ制限を強制することまでは確認していません。版を変えた場合は同梱のtroubleshootingに従って実環境を確かめます。

## 匿名選択、教訓、人の採用

`kit/.h2/h2_kit/selection.py`は、正常に終わり成果物を出した完成品だけを候補に残します。基準の実行や未完成の提案は候補に入れません。タスク・k・モードから再現できる匿名IDへ並べ替え、どの変更で作られたかを伏せて成果物を比較します。k=1なら選択役を起動せず、その完成品を選びます。選択役が失敗したときはラベル順の先頭の完成品へ戻し、fallbackと理由を残します。

振り返りは、各編集に効果があったか・害があったか・観測できないか・切り分けられないかを記録し、移せる教訓を最大1件作ります。十分な根拠がなければ教訓を作りません。`library.py`は教訓がある場合だけ、選ばれたスキルの木と`EXPERIENCE.md`を保存します。後のタスクは前のタスク分だけを読み、仕事固有の事実をそのまま真実として引き継がず、確かめ直す仮説として使います。

最後は`show`で差分と結果を人へ示します。`adoption.py`は承認時から対象スキルが変わっていないこと、選択記録と候補の指紋、`show`が出した確認符号が合うこと、候補の検証を確認してから木を書き込みます。確認符号は指紋の先頭12文字で、採用する候補を取り違えないために使います。人が採用しないと決めた場合は`adopt`を実行しません。

## 導入・使用方法

ZIPを展開した`skill-harness2-kit/`で`python3 install.py /path/to/your-repository`を実行します。利用時はPython 3.9以上、Claude Codeと認証が必要です。実行時の追加Pythonパッケージはありません。導入先で既に内容の違う配布ファイルがあればエラーで止まり、確認後に`--force`を選ぶと`.h2/h2_kit/`・`.h2/templates/`・配布スキルのディレクトリを消して入れ直します。そこへの手編集は失われますが、`.h2/targets/`の記録は保持します。

利用先のルートでClaude Codeを起動して呼びます。

```text
/skill-harness2 minutes .claude/skills/minutes-format
```

タスクは`tasks/<id>/task.md`へ実際の依頼文、`workspace/`へその依頼を解く材料を置きます。IDは小文字・数字・`-`・`_`の64文字以内です。対象スキルが人の呼び出し専用なら、依頼文の最初を`/minutes-format`のように対象スキルのディレクトリ名で始めます。材料の`.claude/`と`.git/`は写さず、対象スキルは実行時に補助CLIが入れます。

```sh
# 以下は利用先のルート。人の確認を挟みながら進める。
python3 .h2/h2.py check minutes
# plan.mdの費用を人が承認した後
python3 .h2/h2.py approve minutes
python3 .h2/h2.py run minutes
python3 .h2/h2.py show minutes
```

中断した場合は同じ`run minutes`で続けます。実行の指紋はスキル・依頼・材料・コマンド・観測の切り詰め条件から計算し、一致する完了記録を再利用します。編集セッションもプロンプト・証拠・コマンドが同じ正常結果を再利用します。完了済みタスク・モードは飛ばすため、承認後に設定を手で変えて記録を流用せず、変更が必要なら`check`から計画を見せ直します。

## 検証方法と結果

ZIPを別のディレクトリへ展開し、その`skill-harness2-kit/`で実行します。bash・make・`venv`と`pip`を使えるPython、初回のネットワーク接続が必要です。

```sh
bash verify-ci.sh
```

`verify-ci.sh`は一時環境へuv 0.13.4とPython 3.12を用意し、元Makefileのruff 0.17.2・mypy 1.20.2を準備してから`make check`を実行します。準備が失敗したら停止します。`ci.json`も同じコマンドとPython 3.12を指定し、サイトの依存関係を使いません。

確認日は2026-10-24、検証環境はmacOS arm64・Python 3.12.15・uv 0.13.4です。期待する結果は、整形・lint・型・構造・133件のテスト・guard・ルール整合の成功、代表違反4件の検出、導入先との内容一致と初回の準備表示です。生成ZIPを別の場所へ展開して同じ手順を実行し、いずれも成功しました。移行先とZIPの全141ファイルの内容一致も確認しています。

実際の対象サイトでは、トップ一覧・ヘッダーからサイドバーを経て対象ページへ移動し、本文と設定JSONの表示を確認しました。本文のダウンロードリンクをブラウザーでクリックし、取得したZIPが生成ZIPと同じ294390バイトで、SHA-256も一致することを確認しました。

元の設計資料に残る収束実験や実Claudeの記録は移行前の観測です。今回の検証はfake_claudeを子プロセスとして使い、有料の実モデル実行・実対話・改善効果の測定を含みません。Windowsと他のClaude Code版での動作も未確認です。

## 参考資料

- [harness2固定版](https://github.com/google-research/harness2/tree/1cfe254e8d25b15f37048c3730134686abe60335)：方法・プロンプトの参照元。
- [Claude Codeのスキル仕様](https://code.claude.com/docs/en/skills)：呼び出しとfrontmatter。
- [Claude CodeのCLI資料](https://code.claude.com/docs/en/cli-reference)：ヘッドレス実行と各フラグ。
- ZIP内の`docs/design/research.md`とADR：参照した仕組み、実装への対応、当時の実験観測と採用理由。

上流から日本語化・移植したひな形の帰属、変更表示、Apache-2.0全文は、ZIP内の`kit/claude/skills/skill-harness2/references/third-party-notices.md`にあります。導入先の配布スキルにもコピーされます。元キット独自部分へ新しい包括ライセンスを指定したものではありません。

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/skills/skill-harness2-kit.zip)
