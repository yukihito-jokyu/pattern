---
title: Claude CodeとCodexの行動ログ・HTML分析
description: hooksで操作・明示された目的・結果を共通JSONLへ記録し、根拠までたどれる単体HTMLを作るスキル。
slug: /development/skills/agent-behavior-html
pattern:
  features:
    - label: 記録
      value: 操作・目的・結果を共通JSONLへ保存
    - label: 分析
      value: 外部通信のないHTMLと根拠JSON
    - label: 導入
      value: 既存hooksを維持して両製品へ接続
---

# Claude CodeとCodexの行動ログ・HTML分析

エージェントの実行を振り返るには、最後の回答だけでなく、どの操作を、何の目的で実行し、どの結果を得たかを追う必要があります。このパターンは、Claude CodeとCodexのhooksが渡すイベントを同じJSONLへ変換し、操作・明示された目的・観測結果を並べた単体HTMLを作ります。

目的はツール入力のdescriptionか、操作前に明示した申告を使います。説明のない操作は「未記録」のまま残します。同様に、後イベントに成否の根拠がなければ成功とはせず、completedとして表示します。失敗した実行と記録不足を混同しないための構成です。会話履歴や内部の推論を復元する機能ではありません。

## 全体像

配布ZIPの中心は`.claude/skills/agent-behavior-html/`です。別のプロジェクトへ導入すると、この単位を`.agent-observer/agent-behavior-html/`へコピーし、両製品のスキル入口から同じ実装を参照します。

```text
agent-behavior-html/
  README.md
  CI.md / ci.json             # このパターン集向けの検証手順と実行設定
  AGENTS.md / CLAUDE.md / Makefile
  .claude/skills/agent-behavior-html/
    SKILL.md
    scripts/
      event_model.py          # 製品別一覧・正規化・スキーマ検証
      record.py               # stdinからJSONLへ追記
      install.py              # 設定の確認・退避・導入
      analyze.py              # 前後対応・目的対応・指標・HTML生成
    assets/dashboard.html     # CSSとJavaScriptを含む単体テンプレート
    references/               # 接続・スキーマ・指標
  .claude/settings.json        # 編集検査と元の行動記録hooks
  .codex/hooks.json            # 元の行動記録hooks
  .agent-observer/backups/     # 元実装に含まれる設定の退避記録
  scripts/                    # 開発検査と合成デモ生成
  tests/test_observer.py       # 元実装の実行契約
  examples/                   # 合成JSONLと生成したHTML・JSON
  .foundation/                # 規則検査・違反例と過去の実行記録
  docs/design/                # 選択理由と検証範囲
```

データは「製品のstdin JSON → record.py → event_model.pyによる正規化 → ローカルJSONL → analyze.py → HTMLとJSON」の順に流れます。install.pyはこの実行経路を製品のhooks設定へつなぐ役です。分析器は製品の会話ファイルを読まず、指定されたJSONLだけを読みます。

ZIPは元実装の全60ファイルを、相対パスと内容を変えずに収録しています。そのため、このディレクトリ自身を観測するhooksには旧作業環境の絶対パスが残り、設計資料・設定のバックアップ・過去の失敗や未検証の記録も含まれます。これに、このパターン集のCI用として`CI.md`、`ci.json`、`scripts/verify-ci.sh`の3ファイルを追加しています。別のプロジェクトへの導入は元のinstall.pyを使い、開発検査は追加スクリプトが一時コピーを準備して実行します。

## 設定・構造と具体的な動作

### 両製品のイベントを同じ形式へ変換する

`.claude/skills/agent-behavior-html/scripts/event_model.py`は、収集を許可するイベントを製品別に定義します。

```python
COMMON_EVENTS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "SubagentStart", "SubagentStop", "PreCompact", "Stop", "SessionEnd",
)
SOURCE_EVENTS = {
    "claude": COMMON_EVENTS + ("PostToolUseFailure", "Notification", "PostCompact"),
    "codex": COMMON_EVENTS + ("PostCompact", "Interrupt"),
}
```

共通10件にClaude Codeの3件、Codexの2件を加えます。例えばClaude CodeのPostToolUseFailureは明示失敗として扱えますが、Codexへ同じイベントを設定しません。保存前にこの一覧を照合し、未知のイベントは保存しません。製品差をここへ集めることで、分析器は共通のsource・event・statusを読めます。

2026-10-24に[Claude Codeのhooks仕様](https://code.claude.com/docs/en/hooks)と[Codexのhooks仕様](https://learn.chatgpt.com/docs/hooks)を照合しました。この一覧は本パターンが採用した観測範囲であり、製品に存在する全イベントを自動で収集する設定ではありません。元実装の確認対象はClaude Code 2.1.308とCodex 0.162.0-alpha.17.2です。今回の合成契約検証を、それらの実セッションでのhook発火確認へ置き換えていません。

### 導入先とコマンドを明示する

`scripts/install.py`では、設定先とスキル入口を分けています。

```python
CONFIG_PATHS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
DISCOVERY_PATHS = {"claude": ".claude/skills", "codex": ".agents/skills"}
```

通常導入では`--project`の実在ディレクトリにスキルをコピーし、上の入口へ相対リンクを生成します。Python実行ファイル、record.py、ログ先は導入時の絶対パスをshell quoteしてコマンドへ書きます。これにより、エージェントの作業場所がサブディレクトリへ変わっても、同じスクリプトとログ先を使えます。一方、導入先を移動すると絶対パスが古くなるため再導入が必要です。

生成される設定の形は次のとおりです。`command`内のパスは実際の導入場所から生成されます。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/python /project/.agent-observer/agent-behavior-html/scripts/record.py --source codex --log-dir /project/.agent-logs",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

`type: command`でローカル収集器を起動し、`--source`で正規化する製品を決め、`--log-dir`で保存先を固定します。`timeout: 3`の単位は秒です。短い追記処理に限った上限として元実装が採用した値を維持しています。3秒という数値自体の比較測定は記録されていません。matcherを省略した観測groupは対象イベント全体へ適用し、既存の別matcher groupを置換しません。

UserPromptSubmitとSubagentStartだけはコマンドへ`--context`を追加します。この場合は目的を申告する手順を`hookSpecificOutput.additionalContext`で返します。ほかの正常な収集ではstdoutを空にし、製品へ不要な本文を返しません。Codexの`additionalContextLimit`や`async`は指定せず、短い同期hookとして動かします。製品側の既定のcontext上限を使い、バックグラウンド完了順へ依存させません。Codexではプロジェクト層の信頼と、`/hooks`での定義の確認・信頼が別途必要です。定義が変われば再確認が必要になります。[Codexの信頼と出力の仕様](https://learn.chatgpt.com/docs/hooks)

CLIの指定と省略時の動作も、導入先へ持ち込めるように固定しています。

| CLI | 指定 | 省略した場合と役割 |
| --- | --- | --- |
| install.py | `--project` | 必須。利用者のプロジェクトを曖昧に決めない |
| install.py | `--providers claude codex` | 両製品。片方だけの導入も選べる |
| install.py | `--apply` | 未指定なら変更予定の表示だけ。確認後に適用する |
| install.py | `--in-place` | 未指定なら利用先へコピー。指定時はこのソースの正本へ接続する |
| record.py | `--source` | 必須。製品別一覧を明示して使う |
| record.py | `--log-dir` | `.agent-logs`。installは絶対パスを明示するためcwdに依存しない |
| record.py | `--intent` | 未指定なら製品イベント。指定時は目的申告のActionIntentを生成する |
| record.py | `--context` | 未指定ならstdoutなし。開始の2イベントで指定したときだけ案内を返す |
| analyze.py | 入力パス | `.agent-logs`。複数ファイル・ディレクトリも指定できる |
| analyze.py | `--output` | `reports/agent-behavior.html`。任意のHTML保存先を選べる |
| analyze.py | `--summary` | HTMLと同じ名前の`.json`。入力ログやHTMLと同じパスは拒否する |
| analyze.py | `--synthetic` | 未指定は通常レポート。合成デモ生成時に指定して画面へ表示する |

導入は既存の別設定・hooksを維持し、変更前の設定と.gitignoreを`.agent-observer/backups/<ID>/`へ保存します。同じ導入の再実行でhookを重複追加せず、同名の別スキルや異なる内容の導入済みスキルは上書きせず停止します。ユーザー全体の設定とCodexの信頼記録は変更しません。

設定全文には非公開の値が含まれる場合があるため、install.pyが新たに作成するバックアップファイルは`0600`（所有者だけ読み書き可）にします。ZIPに元から入っている`.agent-observer/backups/`は過去の設定を保全した記録であり、今回の導入先の復元用ファイルではありません。

### 保存する情報と上限を限定する

`scripts/event_model.py`は保存時の境界を定数にしています。

```python
SCHEMA_VERSION = 2
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_LOG_LINE_BYTES = 16384
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 100000
LOCK_TIMEOUT_SEC = 0.5
DETAIL_LIMITS = {"action": 160, "target": 2048, "purpose": 1024, "expected": 512, "result_summary": 2048}
```

stdinは8MiB以下のJSONオブジェクトに制限します。分析時は1行16KiB、入力合計64MiB、有効イベント10万件を上限にし、読み込み中に増えた分も合計へ数えます。長い行は不正行として数え、合計サイズや件数超過は分析全体を非0で停止します。不正行の診断は最大100件まで保持します。小規模なローカル実行を単体HTMLへ載せるための境界であり、これらの数値を導いた容量・性能の比較測定は元資料にありません。今回は互換性を保つため値を維持しています。

v2のactionは操作種別、targetは対象パス・コマンド・検索条件、purposeは明示目的、expectedは申告された期待結果、result_summaryは観測結果の抜粋です。表の上限はUTF-8バイト数で、長い文字列は末尾を省略します。purpose_sourceにはmissing、tool_description、agent_intentのいずれかを保存し、後の分析で目的の出所を区別します。

共通フィールドはschema_version、event_id、observed_at、source、event、session_id、turn_id、agent_id、tool_use_id、tool_name、status、exit_code、input_fingerprint、input_bytesです。UUIDのevent_idは重複排除、UTCのobserved_atは順序と時間、各IDは操作の対応付けに使います。渡されなかった任意IDはnullとし、mainなどで補いません。session_idは必須です。各IDは安全な文字1〜200文字なら維持し、それ以外の文字列はSHA-256へ変換します。

v1/v2とも定義外のキーと型を拒否します。新しい収集器はv2を書きますが、分析器はv1も読み、存在しなかった操作情報や目的を後付けしません。全フィールドの型と成否の決定順は配布スキルの`references/schema.md`にあります。

record.pyは`.agent-logs/`へ追記し、ファイル名を`<source>-<UTC日付>-<session_idのSHA256先頭32文字>.jsonl`にします。日をまたぐセッションは複数ファイルに分かれ、分析時に同じsourceとsession_idで合流します。書き込みロックと鍵ファイル・JSONLは600権限で作り、ディレクトリは新規作成時700権限にします。既存ディレクトリの権限は変更しません。シンボリックリンクのログ先・ファイルを拒否し、ロックは0.01秒間隔で待ち、0.5秒を超えたら記録を諦めます。

記録失敗は固定のstderrと終了0で知らせ、本来の操作を止めません。例外の本文に元入力が混ざるのを避けるため、入力内容や例外全文を出しません。この設計では、保存失敗をログ自身へ残せず、欠落の集計にも現れない場合があります。

### 入力の本文を保存せず、同一入力を比較する

`scripts/event_model.py`のnormalizeは、入力のdescriptionを外してから指紋を作ります。

```python
tool_input = {name: value for name, value in tool_input.items() if name != "description"}
canonical = json.dumps(tool_input, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False).encode("utf-8")
fingerprint = hmac.new(key, source.encode() + b"\0" + tool_name.encode() + b"\0" + canonical,
                       hashlib.sha256).hexdigest()
```

source・ツール名・並べ替えた入力JSONをHMAC-SHA256へ渡し、入力全体は保存しません。descriptionを除くのは、同じコマンドへ別の目的説明を付けても同一入力として数えるためです。鍵は導入先ごとに32byteを生成し、`.agent-logs/.fingerprint-key`に保存します。HTML/JSONへ鍵を含めません。異なる鍵のプロジェクト間では指紋を比較できず、鍵を変更すると同一入力の集計も分かれます。既存ログの分析だけなら鍵は不要です。

Read/Write/Editのファイル本文、プロンプト、会話履歴、transcript_path、cwd、環境変数は保存しません。パッチは対象ファイルのヘッダーだけをtargetへ取り出します。一方、コマンド・目的・Bashの結果抜粋は保存します。既知のtoken、password、Authorization、API key形式はマスクしますが、任意の機密文字列を完全に除去できるものではありません。共有するHTML/JSONにも抜粋が残る点を確認してください。

### 目的を次の1操作へ対応付ける

説明欄がない操作では、開始hookが案内するセッションIDと目的記録コマンドを使います。ActionIntentは製品のイベント名ではなく、`record.py --intent`が生成する申告です。

```json
{
  "session_id": "hookで案内された値",
  "turn_id": null,
  "agent_id": null,
  "tool_name": "Read",
  "tool_input": {"file_path": "/absolute/project/src/auth.ts"},
  "purpose": "認証エラーの原因を確認する",
  "expected": "トークンの判定条件が分かる"
}
```

実際には案内されたsession_id・turn_id・agent_idを使い、次のhookと同じツール名・入力を申告します。Claude CodeのRead/Write/Editは絶対パス、Codexのシェル操作はhook上のBashとcommandキーを使います。単に似たパスや似たコマンドでは対応しません。

analyze.pyはsource・session・turn・agent・tool・入力指紋が全一致し、申告より後で300秒以内の次のPreToolUseだけへ目的を結びます。一度取り出した申告を後の操作へ使い回しません。候補が複数ならambiguous、候補がなければツールのdescriptionを使い、それもなければ未記録とします。申告の期待結果と、後から観測したresult_summaryは別の情報として表示します。

### 前後のイベントと成否を分けて集計する

`scripts/analyze.py`はsource・session_id・tool_use_idで前後をまとめます。ツールIDのないイベントは件数だけ数え、時刻が近い操作へ推測で結びません。前後が1件ずつでツール名が一致すればmatched、片方だけならmissing_startまたはmissing_end、複数候補やツール名不一致ならambiguousです。

PostToolUseFailure、構造化応答のisError/is_error、整数exit_codeだけを成否の根拠にします。明示失敗はerror、exit_codeが0ならsuccess、それ以外はerror、根拠のないPostToolUseはcompletedです。出力テキストにerrorという単語があるだけでは失敗としません。成否の分からない操作を除くため、失敗率の分母は次のようになります。

```python
known = statuses["success"] + statuses["error"]
completed = known + statuses["completed"]
# call_metricsが返す項目
"outcome_coverage": round(known / completed, 4) if completed else None,
"error_rate": round(statuses["error"] / known, 4) if known else None,
```

error_rateは明示された失敗÷明示成否、outcome_coverageは明示成否÷後イベントの成否対象です。分母が0ならnullで、0%の失敗と区別します。missing_end、ambiguousなどを失敗率の分母へ足しません。purpose_coverageは目的ありの呼び出し÷呼び出し数です。小数は4桁へ丸めます。

所要時間は後hook受信時刻から前hook受信時刻を引いた値で、msへ変換して小数3桁へ丸めます。起動・待機も含み、正味のCPU時間や思考時間ではありません。逆転時はclock_reversedとして時間をnullにしますが、明示された成否は残します。p50は並べた時間の中央の下側の値で、偶数件の平均ではありません。並行呼び出しの時間合計は実際の経過時間を超える場合があります。

繰り返しは同じ製品・セッション・ツール・入力指紋でまとめ、各組の2回目以降を数えます。開始なしと曖昧な呼び出しは除きます。繰り返された入力が不要だった、直前の編集が成功原因だった、といった因果関係までは断定しません。

### HTMLから根拠の行へたどる

`assets/dashboard.html`は、分析結果を埋め込んだJSON、インラインCSS、JavaScriptだけで動きます。山括弧とアンパサンドをエスケープしてJSONを埋め込み、ログをtextContentで表示します。外部スクリプト・フォント・通信は使いません。

初期表示は日本時間（Asia/Tokyo）、フィルター未指定の全操作、100件ごとの呼び出し表です。操作カードは先頭20件、繰り返しは上位20組、時系列は先頭300イベント、ツール別グラフは上位12種を表示します。表示を有限に保つ設定であり、全有効イベントは同時生成JSONに残ります。時刻はUTCにも切り替えられます。

製品・セッション・ツールは操作と時系列の両方へ適用し、成否と検索は操作カード・呼び出し表へ適用します。上側の指標は選択範囲、ログ品質は入力全体です。「記録を見る」からcallsのevidenceとpurpose_evidenceをevent_idで引き、locationsにあるファイル番号・ファイル名・1始まりの行番号を表示します。選択範囲のJSON保存には操作とその根拠イベントを含めます。

合成デモでは、認証調査・テスト失敗・編集・再テストを両製品の例として確認できます。これは操作の経過を読む見本であり、製品の性能比較や実際の成功率を示すデータではありません。

## 導入・使用方法

macOS/Linuxのローカル実行と保守対象のPythonを使います。標準ライブラリだけで動き、サイトの依存関係を導入先へ持ち込む必要はありません。ZIPを展開した`agent-behavior-html/`で次を実行し、導入先を実在するパスへ置き換えます。

```bash
python3 .claude/skills/agent-behavior-html/scripts/install.py --project /absolute/path/to/project
python3 .claude/skills/agent-behavior-html/scripts/install.py --project /absolute/path/to/project --apply
```

再起動とCodexの`/hooks`での確認後、短い操作を行い、JSONLが増えることを確認します。分析は次のように実行します。

```bash
python3 /absolute/path/to/project/.agent-observer/agent-behavior-html/scripts/analyze.py \
  /absolute/path/to/project/.agent-logs \
  --output /absolute/path/to/project/reports/agent-behavior.html
```

この展開先自体を観測する場合、元READMEは、旧作業環境のrecord.pyを呼ぶhandlerを両製品の設定から除いてから`make hooks`を実行するよう案内しています。Claude Code側のfoundation編集検査と、ほかのhandlerを残して作業してください。`make hooks`は`install.py --project . --in-place --apply`を呼び、展開先の正本スキルへ接続します。既存handlerを自動で除去する処理ではないため、そのまま実行すると旧パスのhandlerも残ります。

元AGENTS.mdはCodex用の`.agents/skills/`も案内しますが、元実装の全60ファイルにはシンボリックリンクがありません。`make hooks`で生成する入口は配布スキルのagent-behavior-htmlだけで、開発検査が要求するimpl・reviewの入口は生成しません。この状態を変えずに収録しているため、ZIPの展開だけで`make check`が成功するとは扱っていません。開発検査だけを行う場合は、次のCI用スクリプトが一時コピー内に必要な入口を作ります。

停止する場合は、対象製品の設定からrecord.pyを呼ぶhandlerだけを削除して再起動します。通常導入先を更新・移動するときは、変更したスキルと設定を保全し、古い観測handler・入口・配布スキルを退避してから導入し直します。バックアップ復元では、その後の別変更を失わないよう差分を確認します。詳細手順はZIPの`.claude/skills/agent-behavior-html/references/integration.md`にあります。

記録は完全な監査証跡ではありません。hook未発火、保存失敗、特殊な実行経路は復元できず、Codexのホスト側ツール・クラウド・Windowsは動作確認範囲外です。ログの自動削除は行わないため、利用者が日付ファイル単位の保管期間を決めます。

## 検証方法と結果

開発検査にはPythonに加えてNode.jsとmakeが必要です。元READMEにあるコマンドは次のとおりで、ZIP展開先の`agent-behavior-html/`を作業場所にします。途中で失敗した場合はそこで停止します。

```bash
make check
make demo
make probes
python3 .foundation/bin/rules_check.py --root . --final
```

展開直後の`make check`は、旧パスを指す25件の行動記録hookと、存在しない3つのCodexスキル入口を検出して停止します。`make probes`も正常例の`make check`が失敗すると、違反例の検査へ進みません。元のファイルを保持して検証するため、ZIPの展開先では次を実行します。必要な環境と手順は、追加した`CI.md`にも収録しています。

```bash
bash scripts/verify-ci.sh
```

`scripts/verify-ci.sh`は一時コピーを作り、その中だけで古い行動記録handlerを除き、既存のinstall.pyを`--in-place --apply`で実行して現在のパスへ接続します。他のhookと設定は残します。impl・reviewのCodex入口も相対リンクで補い、準備に成功してから前述の4コマンドを順に実行します。途中失敗は非0で返し、一時コピーは終了時に削除します。配布元やユーザー全体の設定、Codexのhook信頼は変更しません。

共通CIは、パターンのルートに追加した`ci.json`を読みます。

```json
{
  "command": [
    "bash",
    "scripts/verify-ci.sh"
  ],
  "pythonVersion": "3.12"
}
```

`pythonVersion`でPython 3.12を用意し、`command`の配列をZIP展開先で実行します。Node.js 22とmakeは共通runnerの環境を使います。個別ジョブや検査の例外を共通処理へ追加せず、元の品質検査・契約テスト・違反検出を実行する構成です。リポジトリのルートから同じZIP検証を行う場合は、`npm run verify:patterns -- --id development/skills/agent-behavior-html --ci --timeout-ms 1200000`を使います。

確認日：2026-10-25。ローカル確認環境：macOS arm64、Python 3.15.0、Node.js 26.12.1。共通処理で63ファイルのZIPを生成し、元実装の60ファイルについて移行先・ZIPそれぞれの相対パス、バイト数、SHA-256が一致することを確認しました。追加3ファイルもZIPに収録しています。動作確認はZIPを別の場所へ展開し、追加スクリプトが作る一時コピーで行います。

| 確認 | 期待結果 | 今回の結果 |
| --- | --- | --- |
| 準備後の全検査 `make check` | 品質・契約・画面・規則検査がすべて成功する | 成功。展開直後の未準備状態での失敗とは区別する |
| 契約テスト `make test` | 既存の実行契約を満たす | 19件成功。合成入力と一時導入の検証であり、実セッションの確認ではない |
| `node scripts/check_dashboard.cjs` | 絞り込み・根拠表示・JSON保存などが動く | DOMスタブによる検査は成功 |
| `make demo` | 合成ログからHTMLとJSONを生成する | 42イベントを読み込み成功。不正行0、重複0。見本は12操作・2セッション |
| 準備後の`make probes` | 21件の違反とcheck組み込み3件を検出する | 成功。正常例の成功後に全違反を検出 |
| 最終rules_check | 規則と今回の検証結果の整合を確認する | 24規則、エラー0・警告0。今回生成したprobe結果を照合 |
| 生成ZIP | 元実装とCI用の追加ファイルを収録する | 元の全60ファイルが相対パス・内容とも一致し、追加3ファイルを含む63ファイルを収録 |
| 共通CIの対象一覧生成・`--ci`検証 | 必要な設定を読み、対象ZIPを検証する | 成功。パターンを対象に選び、ZIP単体で準備と検証を実行 |
| サイト側の必須6検査 | 配置・文書・共通テスト・型・ビルド・E2Eを確認する | 6コマンド成功。E2Eは6件成功。実際の対象文書とZIPは次の実ブラウザー確認で別に確認 |
| 対象サイトの実ブラウザー | 本文・導線・ZIP取得が成功する | Chromium 156.0.8078.4で本文・コード13箇所・一覧とヘッダーとサイドバーからの導線・63ファイルのZIP取得を確認。1440×1000／390×844でJavaScriptエラー・横はみ出しなし |
| 合成デモの実ブラウザー | 絞り込み・根拠・JSON保存などが動く | 復元版ではChromium起動時の権限エラーで実施できず。DOMスタブの成功とは区別する |
| 実製品のhook発火 | 短い操作からログが増える | 今回は未実施。利用先で再起動・信頼・実操作による確認が必要 |
| 独立作者の収束・人間の最終確認 | 別の判断として確認する | 未実施／確認待ち |

元実装の過去記録には、Codexが12件のhooks設定を読み込んだ一方で信頼待ちと接続失敗により実操作の記録へ進めなかった経緯があります。独立作者の収束試験も成功したセッションは0件で、未測定です。ZIPの`docs/design/`と`.foundation/`にはこれらの記録を元のまま収録しており、今回の実機成功や収束完了へ読み替えていません。

元の`.gitignore`は`.agent-observer/`を除外します。同梱バックアップの2ファイルは、この設定を変更せずにGitへ明示的に追加し、元実装の全60ファイルを保存しています。CIの追加ファイルは元の60ファイルと区別でき、検証時の設定変更と生成結果は一時コピー内に閉じます。

## 参考資料

- [Claude Code Hooks reference](https://code.claude.com/docs/en/hooks)：設定先、製品別イベントとstdin・出力契約。
- [Codex Hooks](https://learn.chatgpt.com/docs/hooks)：プロジェクト層、hook定義の信頼、対応イベントと観測経路。
- [Python fcntl](https://docs.python.org/3/library/fcntl.html)：Unixのファイルロック。
- 配布スキルの`references/schema.md`、`references/metrics.md`、`references/integration.md`：フィールド、分母、導入・停止・復元の詳細。

## ダウンロード

[実装をダウンロード](/downloads/patterns/development/skills/agent-behavior-html.zip)
