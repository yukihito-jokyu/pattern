---
name: skill-tune
description: 既存の Claude Code スキルを評価データで改善する。正解データがあれば学習用・検証用・テスト用に分け、無ければ人と評価項目を決め、独立した学習と検証のラウンドを回し、最後にテスト用で測って報告する。
disable-model-invocation: true
allowed-tools: Bash(python3 .tune/tune.py *)
argument-hint: <target-id> [対象スキルのディレクトリ]
---

# skill-tune

対象のスキルを、評価データ（ケース）で測りながら改善する。段の順番と次の手は補助 CLI の `status` が決める。このスキルの役目は、`status` の指示を実行し、人に決めてもらう場面で AskUserQuestion を使うことである。

## 前提

- 補助 CLI は `python3 .tune/tune.py <サブコマンド> --target <target-id>` で呼ぶ。`<target-id>` は小文字の英数字とハイフンの名前で、作業の記録は `.tune/targets/<target-id>/` に残る
- 引数 `$ARGUMENTS` の1つ目を `<target-id>` にする。無ければ、対象スキルの名前から作り、人に確かめる
- `.tune/tune.py` が無ければ、skill-tune-kit の `install.py` で入れるよう人に伝えて止める

## 全体の流れ

| 段 | すること | 誰が |
|---|---|---|
| A. 計画 | モードを決め、ケースと検査を作り、分割と見積もりを人に承認してもらう | このスキルと人 |
| B. ラウンド | 監査 → データの直し（人が選ぶ）→ 学習 → 候補の評価 → 採否、を止める条件まで繰り返す | status の指示どおり |
| C. 最後 | 元の版と最良の版をテスト用で評価し、テスト用を監査し、報告し、適用を人が決める | status の指示どおり |

## 手順 A：計画を決める

`status` が「計画が無い」か「計画に問題がある」と言ったら、この手順を行う。

1. 計画が無ければ `python3 .tune/tune.py init --target <target-id> --skill <対象スキルのディレクトリ>` を実行する
2. 対象スキルの SKILL.md を読み、スキルの目的を1文にまとめ、ゴールとして人に確かめる
3. モードを AskUserQuestion で決める
   - 入力と正解の組がある、または作れる → `reference`。ケースの作り方は [references/dataset-guide.md](references/dataset-guide.md)
   - 正解が1つに決まらない → `criteria`。評価項目を人と壁打ちで決める。進め方は [references/criteria-guide.md](references/criteria-guide.md)
4. `plan.json` と `dataset/cases.json` を書く。形は [references/plan-schema.md](references/plan-schema.md)、検査の種類は [references/check-kinds.md](references/check-kinds.md) にある
5. `python3 .tune/tune.py check-plan --target <target-id>` を実行する。エラーが出たら、エラーの文に従って直し、通るまで繰り返す
6. `status` を実行し、その指示（plan.md を人に見せて承認を聞く）に従う

承認の後に `plan.json` と `dataset/` を手で変えない。変えると評価の段は止まり、承認からやり直しになる。データの直しは手順 B の `data-fix` だけで行う。

## 手順 B と C：繰り返すこと

`python3 .tune/tune.py status --target <target-id>` を実行し、出力の行を次の表で読み分けて実行する。実行したら、また `status` に戻る。`段階: 完了` が出るまで繰り返す。

| 行の書き出し | すること |
|---|---|
| `対象:`、`ラウンド:`、`段階:` | 読むだけ。人への途中報告に使う |
| `問題:` | 手順 A に戻って計画を直す |
| `次: python3 .tune/tune.py …` | そのコマンドをそのまま実行する |
| `次: 下の job をすべて Agent ツールで…` | 続く `job` の行を全部、1つのメッセージの中の Agent ツールの呼び出しにして起動し、全員の完了を待つ |
| `job <エージェント> <ラベル> <プロンプトのパス>` | Agent ツールを、subagent_type に `<エージェント>`、description に `<ラベル>`、prompt に「`<プロンプトのパス>` を読み、その指示に従ってください。」として呼ぶ |
| `その後: python3 .tune/tune.py …` | job が全部終わってから、そのコマンドを実行する |
| `次: <ファイル> を人に見せ、… AskUserQuestion で聞く` | ファイルを読み、要点を人に示して AskUserQuestion で聞く。答えに合う次の行のコマンドを実行する |
| `承認なら:`、`適用するなら:`、`適用しないなら:` | 人の答えに合う行のコマンドを実行する。`<…>` は答えで置き換える |
| `次: <ファイル> の要点を人に見せる` | 報告を読み、要点を人に示して終える |

補助 CLI のコマンドが `エラー:` で失敗したら、エラーの文に書かれたことをしてから `status` に戻る。同じエラーが2回続いたら、人に状況を伝えて止める。

## 人が決める場面

次の場面では、AskUserQuestion で人の答えを得るまで、表の右のコマンドを実行しない。

| 場面 | 人に見せるもの | 答えで実行するコマンド |
|---|---|---|
| 計画の承認 | plan.md（ゴール、モード、検査、分割、起動回数の見積もり、警告） | `approve`（承認しないなら手順 A に戻る） |
| データの直しの採否 | audit.md（指摘ごとの原因、根拠、直しの差分） | `data-fix --apply '<選んだ指摘の ID>'` か `data-fix --none` |
| 最良の版の適用 | report.md（結論、テスト用の比較、ラウンドの経過、テスト用の監査） | `apply` か `apply --skip` |

データの直しを聞くときは、指摘ごとに「正解・検査・入力のどれを、どう変えるか」と、直すとゴールが変わることを示す。テスト用の監査の指摘は報告に載せるだけで、ループの中では直さない。

## サブエージェント

| エージェント | 役目 | 見せるもの |
|---|---|---|
| `tune-executor` | スキルの写しに従って1件の依頼をこなす | スキルの写し、作業場所、依頼 |
| `tune-grader` | 版を知らずに返答を評価項目で採点する | 依頼、正解（使う項目だけ）、返答、作業場所 |
| `tune-learner` | 学習用の失敗から候補の版を直す | 学習用のケースの証拠、今の版、候補 |
| `tune-auditor` | 失敗の原因がスキルかデータかを見分け、データの直しを提案する | 不合格のケースの証拠 |

## 守ること

- サブエージェントの仕事を自分でしない。返答、採点、提案、監査の中身を読んで書き換えない。読むのは、人に見せる plan.md、audit.md、report.md だけにする
- 検証用・テスト用のケースの中身を、学習役へのプロンプトや候補の版に持ち込まない
- `.tune/targets/<target-id>/` の中は、手順 A の `plan.json`、`dataset/` 以外を手で書かない
- 段を飛ばさない。次の手は必ず `status` で確かめる
- 補助 CLI のコマンドが失敗したら、`status` に戻る（`-check` の失敗は、問題をプロンプトに書き足してあるので、status が同じサブエージェントを起動し直させる）。同じ段で同じエラーが2回続いたら、それ以上起動せず、エラーの文と status の出力を人に見せて止める
