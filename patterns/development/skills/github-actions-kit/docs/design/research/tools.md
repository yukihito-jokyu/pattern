# GitHub Actions 用 lint ツール群 調査レポート（2026-10-23 実施）

## 0. この調査の前提

GitHub Actions のワークフロー（`.github/workflows/*.yml`）、composite action（`action.yml`）、`dependabot.yml` を機械的に検査する基盤を作る前提で、候補ツールを実際に動かして確かめた。
各事実には「確認済み（コマンド実行または取得したページで裏付けた）」か「未確認」を付ける。

- 実行環境：uv 0.13.4（`uv --version` → `uv 0.13.4 (Homebrew 2026-10-20 aarch64-apple-darwin)`）、macOS arm64
- 作業ディレクトリ：`/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/`
  - `a/`：actionlint 用サンプル（git init 済み）
  - `b/`：zizmor 用サンプル（workflow、composite action、dependabot.yml）
  - `y/`：yamllint 用サンプル
  - `src/`：`git clone --depth 1` で取得した上流ソース（actionlint v1.7.12、zizmor v1.31.1）
  - `docs/`：raw.githubusercontent.com から取得したドキュメント

### PyPI の最新版（確認済み）

コマンド：`curl -s https://pypi.org/pypi/<pkg>/json`

| パッケージ | 最新版 | requires-python | 配布形式 / アップロード日 |
|---|---|---|---|
| actionlint-py | 1.7.12.25 | >=3.7 | **sdist のみ**（`actionlint_py-1.7.12.25.tar.gz`、2026-09-22） |
| shellcheck-py | 0.11.0.1 | >=3.9 | プラットフォーム別 wheel（2025-08-09） |
| zizmor | 1.31.1 | >=3.11 | `py3-none-<platform>` wheel（2026-10-15） |
| yamllint | 1.38.0 | >=3.10 | wheel（2026-01-13） |
| pyyaml | 6.0.3 | >=3.8 | wheel（2025-09-25） |

依頼文にあった想定バージョンは、すべて PyPI の最新版と一致した。

---

## A. actionlint（PyPI `actionlint-py`）と shellcheck（PyPI `shellcheck-py`）

### A-1. バイナリ名と同梱している上流の版（確認済み）

`actionlint-py` は sdist なので、インストール時にビルドが走る。そのビルドで GitHub のリリースページから actionlint のバイナリを取得する。そのため CI ではインストール時に github.com へ到達できる必要がある。

```
$ uvx --from actionlint-py==1.7.12.25 actionlint -version
   Building actionlint-py==1.7.12.25
      Built actionlint-py==1.7.12.25
1.7.12
installed by downloading from release page
built with go1.26.1 compiler for darwin/arm64

$ uvx --from shellcheck-py==0.11.0.1 shellcheck --version
version: 0.11.0
```

- インストールされるバイナリ名は `actionlint` と `shellcheck`。
- `actionlint-py 1.7.12.25` が同梱するのは上流の actionlint **v1.7.12**。4つ目の数字（`.25`）はラッパー側の連番。
- 上流の最新タグも v1.7.12（`git ls-remote --tags https://github.com/rhysd/actionlint` → `v1.7.10, v1.7.11, v1.7.12`）。
- PyPI の説明文（https://pypi.org/project/actionlint-py/ ）より：「A python wrapper to provide a pip-installable [actionlint] binary … download the pre-built actionlint binary for your particular platform」。

### A-2. shellcheck を自動で見つけるか（確認済み）

結論から言うと、見つける。actionlint は既定で `PATH` 上の `shellcheck` を呼ぶ（`-shellcheck` の既定値が `"shellcheck"`）。`uv run --with` で入れたバイナリは同じ環境の `bin/` に置かれて PATH に乗るので、追加の設定なしで連携する。

検証に使ったのは [sc.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/a/.github/workflows/sc.yml) で、中身は `env: MY_VAR: hello world` と `if [ $MY_VAR = x ]; then …` である。

```
$ uv run --no-project --with actionlint-py==1.7.12.25 --with shellcheck-py==0.11.0.1 \
    sh -c 'actionlint -no-color .github/workflows/sc.yml; echo "exit=$?"'
.github/workflows/sc.yml:9:9: shellcheck reported issue in this script: SC2086:info:1:6: Double quote to prevent globbing and word splitting [shellcheck]
exit=1

# shellcheck-py を入れない場合（PATH に shellcheck なし）
$ uv run --no-project --with actionlint-py==1.7.12.25 sh -c 'actionlint -no-color .github/workflows/sc.yml; echo "exit=$?"'
exit=0
```

**注意点（確認済み）**
- shellcheck が見つからないと、actionlint は**何も言わずに shellcheck 検査を飛ばして exit 0 で終わる**。CI では shellcheck の導入漏れに気付きにくいので、`-shellcheck=<絶対パス>` で明示するか、shellcheck の存在を別途確かめるとよい。
- `VAR=foo; [ $VAR = x ]` のように、同じスクリプトの中で定数を代入した変数では SC2086 が出なかった（shellcheck が値を安全と判断するため）。検証用には `env:` 経由の変数を使う必要がある。
- actionlint は shellcheck を `-e SC1091,SC2194,SC2050,SC2153,SC2154,SC2157,SC2043` 付きで呼ぶ。つまりこれらの SC コードは常に除外される。
  - 根拠：[rule_shellcheck.go 193行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/actionlint/rule_shellcheck.go:193:1)
  > `args := []string{"--norc", "-f", "json", "-x", "--shell", sh, "-e", "SC1091,SC2194,SC2050,SC2153,SC2154,SC2157,SC2043", "-"}`

`-shellcheck` フラグの挙動も確かめた（確認済み）。

```
# 絶対パスで明示した場合 → 検出される
$ actionlint -no-color -shellcheck='/Users/.../uv/archive-v0/Z68sT-hKaBMBJ2Es/bin/shellcheck' .github/workflows/sc.yml
... SC2086:info:1:6: Double quote to prevent globbing and word splitting [shellcheck]
exit=1
# 空文字を渡した場合 → shellcheck 連携が無効になる
$ actionlint -no-color -shellcheck= .github/workflows/sc.yml
exit=0
```

pyflakes も同じ仕組みで連携する（`--with pyflakes` を付けると `shell: python` の step に対して `[pyflakes]` が出た。確認済み）。

```
.github/workflows/cfg.yml:9:9: pyflakes reported issue in this script: 2:7: undefined name 'undefined_name' [pyflakes]
```

### A-3. フラグ（確認済み：`actionlint -h`）

| フラグ | 内容（help 原文の要約） |
|---|---|
| `-format string` | Go テンプレートで出力を整形する。`-format '{{json .}}'` で JSON 配列を出す |
| `-config-file string` | 設定ファイルのパス |
| `-ignore value` | エラーメッセージに対する正規表現。繰り返し指定できる |
| `-shellcheck string` | shellcheck のコマンド名またはパス。空なら無効（既定 `"shellcheck"`） |
| `-pyflakes string` | pyflakes のコマンド名またはパス。空なら無効（既定 `"pyflakes"`） |
| `-no-color` / `-color` | 色付けを無効にする / 強制する |
| `-oneline` | 1エラー1行で出す |
| `-init-config` | `.github/actionlint.yaml` の雛形を生成する |
| `-stdin-filename` | `-`（stdin）で読んだときのファイル名 |
| `-verbose` / `-debug` / `-version` | 詳細出力 / 開発用出力 / バージョン表示 |

`-format '{{json .}}'` の実際の出力（確認済み）：
```
[{"message":"shellcheck reported issue in this script: SC2086:info:1:6: Double quote to prevent globbing and word splitting","filepath":".github/workflows/sc.yml","line":9,"column":9,"kind":"shellcheck","snippet":"      - run: |\n        ^~~~","end_column":12}]
```
`-format` を付けても、指摘があれば exit 1 になる（確認済み：`exit=1`）。

`-ignore 'SC2086'` を付けると上の指摘が消えて exit 0 になった（確認済み）。

### A-4. 終了コード（確認済み）

https://github.com/rhysd/actionlint/blob/v1.7.12/docs/usage.md の「Exit status」節と、[command.go 19〜26行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/actionlint/command.go:19:1) の定義が一致している。

| コード | 意味 | 実測 |
|---|---|---|
| 0 | 問題なし | `-shellcheck=` 指定時 `exit=0` |
| 1 | 問題あり | サンプル実行で `exit=1` |
| 2 | コマンドラインオプションが不正 | `actionlint -badflag` → `exit=2` |
| 3 | 致命的エラー | `actionlint nonexist.yml` → `could not read "nonexist.yml" … exit=3` |

引数なしで実行する場合は git リポジトリが必要になる。git 管理外のディレクトリでは exit 3 で止まった（確認済み）。
```
no project was found in any parent directories of ".../tools-probe/a". check workflows directory is put correctly in your Git repository
exit=3
```

### A-5. 設定ファイル `actionlint.yaml`（確認済み）

出典は https://raw.githubusercontent.com/rhysd/actionlint/v1.7.12/docs/config.md 。

- 自動で探す場所は `<リポジトリルート>/.github/actionlint.yaml`、次に `.github/actionlint.yml` の順。
  - 根拠：[config.go 120〜134行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/actionlint/config.go:120:1)
  > `for _, f := range []string{"actionlint.yaml", "actionlint.yml"} { p := filepath.Join(root, ".github", f)`
- スキーマ（config.md の原文例）：
```yaml
self-hosted-runner:
  labels: [linux.2xlarge, ...]       # path.Match のグロブが使える
config-variables: [DEFAULT_RUNNER, ...]  # 配列を書くと vars.* を厳密に検査する。[] は「変数なし」、null（既定）は検査しない
paths:
  .github/workflows/**/*.{yml,yaml}:  # リポジトリルートからの相対グロブ（doublestar）
    ignore:
      - 'shellcheck reported issue in this script: SC2086:.+'   # エラーメッセージに対する正規表現
```
- 実測：`.github/actionlint.yaml` を置くと、何も指定しなくても読み込まれた。`labels: [my-gpu]` によって `[runner-label]` の指摘が消え、`config-variables: [KNOWN_VAR]` によって次の指摘が新たに出た。`paths.<file>.ignore` で SC2086 も抑止できた。`-config-file ../custom-al.yaml` を指定した場合も同じ結果になった。
```
.github/workflows/cfg.yml:7:23: undefined configuration variable "unknown_var". defined configuration variables in actionlint.yaml are "KNOWN_VAR" [expression]
```

### A-6. ルールの kind 名（出力の `[...]` に出る文字列）（確認済み）

kind 名はソースの `RuleBase{name: ...}` で定義されている（`src/actionlint/rule_*.go` を grep した）。これに parse.go の `syntax-check` を加えると、全部で次の **18 種**になる。

`syntax-check`, `expression`, `action`, `runner-label`, `shellcheck`, `pyflakes`, `permissions`, `job-needs`, `matrix`, `events`, `deprecated-commands`, `if-cond`, `credentials`, `env-var`, `id`, `glob`, `workflow-call`, `shell-name`

依頼文の列挙に無かった kind は `shell-name` だけだった。依頼文の kind はすべて実在する。

docs/checks.md（v1.7.12）の節と、その節の出力例に出る kind の対応は次のとおり（`awk` で抽出した）。

| checks.md の節 | kind |
|---|---|
| Unexpected keys / Missing required keys and key duplicates / Unexpected empty mappings / Unexpected mapping values | `syntax-check` |
| `${{ }}` の構文・型検査、contexts と組み込み関数、steps/matrix/needs の型付け、比較演算子の厳密型検査、contexts の利用可否、**Script injection by potentially untrusted inputs** | `expression` |
| shellcheck integration / pyflakes integration | `shellcheck` / `pyflakes` |
| Job dependencies validation | `job-needs` |
| Matrix values | `matrix` |
| Webhook events / workflow_dispatch / CRON | `events`（一部 `syntax-check`） |
| Glob filter pattern | `glob` |
| Runner labels | `runner-label` |
| `uses:` の形式、local / popular action の inputs、古い popular action、Action metadata、Deprecated inputs | `action` |
| Shell name validation | `shell-name` |
| Job ID / step ID の一意性、ID naming convention | `id` |
| Hardcoded credentials | `credentials` |
| Environment variable names | `env-var` |
| Permissions | `permissions` |
| Reusable workflows | `workflow-call`（一部 `events` / `expression`） |
| Check deprecated workflow commands | `deprecated-commands` |
| Constant conditions at `if:` | `if-cond` |
| YAML anchors | `syntax-check` / `credentials` |

main ブランチの checks.md と比べると、節見出しの違いは1か所だけだった（`CRON syntax check at schedule:` → `CRON syntax and IANA timezone string at on.schedule`）。

### A-7. 信頼できない入力を `run:` に埋め込んだ場合（確認済み）

actionlint は **`[expression]` の kind で検出する**。サンプルは [bad.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/a/.github/workflows/bad.yml)。
```
.github/workflows/bad.yml:14:24: "github.event.pull_request.title" is potentially untrusted. avoid using it directly in inline scripts. instead, pass it through an environment variable. see https://docs.github.com/en/actions/reference/security/secure-use#good-practices-for-mitigating-script-injection-attacks for more details [expression]
```
同じ実行では、ほかに `[job-needs]`（存在しない job を needs に指定）、`[runner-label]`（`ubuntu-latst`）、`[expression]`（`matrix.nonexistent`）も出た。

---

## B. zizmor（PyPI `zizmor` 1.31.1）

### B-1. 起動とフラグ（確認済み：`uvx zizmor@1.31.1 --help`）

uvx は requires-python>=3.11 を満たす Python を自動で選んだ（この環境では 3.14.5）。`zizmor --version` → `zizmor 1.31.1`。上流の最新タグも v1.31.1（`git ls-remote --tags`）。

| フラグ | 内容 |
|---|---|
| `-o, --offline` | オンライン監査を無効にし、リモートリポジトリも監査しない（env `ZIZMOR_OFFLINE`） |
| `--no-online-audits` | `--offline` より弱い。オンラインが必要な監査だけを無効にする（env `ZIZMOR_NO_ONLINE_AUDITS`） |
| `--persona <regular\|pedantic\|auditor>` | 既定は `regular`。`-p/--pedantic` は `--persona=pedantic` の別名 |
| `--format <plain\|json\|json-v1\|sarif\|github>` | 既定は `plain`（cargo 風の出力） |
| `--min-severity <informational\|low\|medium\|high>` | 指定より低い重大度を除外する |
| `--min-confidence <low\|medium\|high>` | 指定より低い確信度を除外する |
| `-c, --config <FILE>` | 全入力に1つの設定を適用する（env `ZIZMOR_CONFIG`） |
| `--no-config` | 設定を一切読まない |
| `--no-ignores` | ignore コメントと設定の ignore を無視する |
| `--collect <all\|default\|workflows\|actions\|dependabot\|pre-commit>` | 収集する入力の種類。既定では workflow と composite action を `.gitignore` を尊重して集める |
| `--strict-collection` | 構文・スキーマエラーを警告ではなく失敗として扱う |
| `--fix[=safe\|unsafe-only\|all]` | 自動修正（EXPERIMENTAL） |
| `--no-exit-codes` | 11以上の終了コードを使わない |
| `--gh-token` | env `GH_TOKEN` / `GITHUB_TOKEN` / `ZIZMOR_GITHUB_TOKEN` |

### B-2. 終了コード（確認済み）

出典は [usage.md 563行目〜](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/docs/usage.md:563:1)（= https://docs.zizmor.sh/usage/#exit-codes ）。

| コード | 意味 | 実測 |
|---|---|---|
| 0 | 指摘なし（または SARIF モード） | 指摘のない ok.yml で `No findings to report. Good job! (2 suppressed)` → `exit=0` |
| 1 | 監査中のエラー | 存在しないファイルを渡すと `fatal: no audit was performed` → `exit=1` |
| 2 | 引数の解析に失敗 | （未実測） |
| 3 | 入力を1つも収集できなかった（v1.21.0〜） | （未実測） |
| 11 / 12 / 13 / 14 | 最も重い指摘が informational / low / medium / high | サンプルで `exit=14`、dependabot.yml だけで `exit=13` |

- `--format=sarif` と `--no-exit-codes` のときは 11 以上を使わない。実測でどちらも `exit=0` になった。
- `--fix` で全件が修正できた場合も 11 以上を使わない（ドキュメントの記述）。
- plain 出力の見出しと重大度の対応は `error`=High、`warning`=Medium、`help`=Low、`info`=Informational。
  - 根拠：[plain.rs 37〜40行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/crates/zizmor/src/output/plain.rs:37:1)
  > `Severity::Informational => Level::INFO, Severity::Low => Level::HELP, Severity::Medium => Level::WARNING, Severity::High => Level::ERROR`

### B-3. 監査（audit）一覧（確認済み）

v1.31.1 には **41 個**の監査がある。次の3つの情報源で数が一致した。
- `docs/audits.md` の `## \`...\`` 節が 41 個
- `crates/zizmor/src/audit/*.rs` が 41 ファイル
- `-vv` 実行時のログで「scheduling」が 36 個、「skipping」が 5 個

依頼文に挙がった 32 個は**すべて存在する**。依頼文に無く追加で存在するのは `adhoc-packages`, `github-app`, `hardcoded-container-credentials`, `insecure-url-scheme`, `secrets-outside-env`, `self-repository`, `typosquat-uses`, `unpinned-tools`, `unsound-ternary` の 9 個。

**オンライン専用の監査（トークンがないと skip される）は5個。**

```
$ uvx zizmor@1.31.1 --offline -v --no-progress --format=json . 2>&1 >/dev/null | grep skip
DEBUG zizmor::registry: skipping impostor-commit: can't run without a GitHub API token
DEBUG zizmor::registry: skipping ref-confusion: can't run without a GitHub API token
DEBUG zizmor::registry: skipping known-vulnerable-actions: can't run without a GitHub API token
DEBUG zizmor::registry: skipping stale-action-refs: can't run without a GitHub API token
DEBUG zizmor::registry: skipping ref-version-mismatch: can't run without a GitHub API token
```

ドキュメントの表（docs.zizmor.sh/audits を WebFetch で確認、ローカルの audits.md でも同じ）では、`ref-version-mismatch` が「Works offline ✅」になっている。しかしソースでは offline 時とトークンが無いときに Skip しており、実際の挙動もオンライン専用だった。ドキュメントと実装が食い違っているので、**実装の挙動を優先する**。
- 根拠：[ref_version_mismatch.rs 252〜261行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/crates/zizmor/src/audit/ref_version_mismatch.rs:252:1)
> `if state.no_online_audits { return Err(AuditLoadError::Skip(anyhow!("offline audits only requested"`

重大度と persona は監査ごとに固定ではなく、**指摘ごとに変わる**。そこで、zizmor 自身のテストデータ（`crates/zizmor/tests/integration/test-data` の 225 ファイル）に `--offline --persona=auditor --no-config --format=json` をかけて集計した。下表はその**観測値**（severity/confidence/persona）で、網羅を保証するものではない。

| 監査 | 対象 | 導入版 | 観測された severity / persona | 自動修正 | 設定 |
|---|---|---|---|---|---|
| adhoc-packages | WF, Action | v1.26.0 | Low / Regular | ❌ | ❌ |
| anonymous-definition | WF, Action | v1.10.0 | Informational〜Low / **Pedantic** | ❌ | ❌ |
| archived-uses | WF, Action | v1.19.0 | Medium / Regular（オフラインで動作） | ❌ | ❌ |
| artipacked | WF | v0.1.0 | Medium(conf Low) / Regular（一部 Auditor, Pedantic） | ⚠️ | ❌ |
| bot-conditions | WF | v1.2.0 | High / Regular | ✅ | ❌ |
| cache-poisoning | WF | v0.10.0 | High / Regular | ⚠️ | ❌ |
| concurrency-limits | WF | v1.16.0 | Low / **Pedantic** | ❌ | ❌ |
| dangerous-triggers | WF | v0.1.0 | High / Regular | ❌ | ❌ |
| dependabot-cooldown | Dependabot | v1.15.0 | Medium / Regular | ✅ | ✅ `days`（既定 7） |
| dependabot-execution | Dependabot | v1.15.0 | High / Regular | ⚠️ | ❌ |
| excessive-permissions | WF | v0.1.0 | High〜Medium / Regular（一部 Pedantic） | ❌ | ❌ |
| forbidden-uses | WF, Action | v1.6.0 | 設定したときだけ動く（サンプルでは error=High） | ❌ | ✅ `allow` / `deny` |
| github-app | WF, Action | v1.25.0 | High / Regular | ❌ | ❌ |
| github-env | WF, Action | v0.6.0 | High / Regular | ❌ | ❌ |
| hardcoded-container-credentials | WF | v0.1.0 | High / Regular | ❌ | ❌ |
| impostor-commit | WF, Action, pre-commit | v0.1.0 | **オンライン専用**（未観測） | ✅ | ❌ |
| insecure-commands | WF, Action | v0.5.0 | High / Regular（一部 Auditor） | ⚠️ | ❌ |
| insecure-url-scheme | pre-commit | v1.29.0 | High / Regular | ❌ | ❌ |
| known-vulnerable-actions | WF, Action | v0.1.0 | **オンライン専用**（未観測） | ⚠️ | 表は ❌、本文には `config.allow` あり |
| misfeature | WF, Action | v1.21.0 | Low / Regular（一部 Auditor） | ❌ | ❌ |
| obfuscation | WF, Action | v1.7.0 | Low / Regular（一部 Pedantic, Informational） | ⚠️ | ❌ |
| overprovisioned-secrets | WF, Action | v1.3.0 | Medium / Regular | ❌ | ❌ |
| ref-confusion | WF, Action | v0.1.0 | **オンライン専用**（未観測） | ❌ | ❌ |
| ref-version-mismatch | WF, Action | v1.14.0 | **オンライン専用（実装上）**（未観測） | ⚠️ | ❌ |
| secrets-inherit | WF | v1.1.0 | Medium / Regular | ❌ | ❌ |
| secrets-outside-env | WF | v1.23.0 | Medium / **Auditor** | ❌ | 表は ❌、本文には `config.allow` あり |
| self-hosted-runner | WF | v0.1.0 | Medium / **Auditor** | ❌ | ❌ |
| self-repository | WF, Action | v1.30.0 | Low / Regular | ⚠️ | ❌ |
| stale-action-refs | WF, Action | v1.7.0 | **オンライン専用**（未観測） | ❌ | ❌ |
| superfluous-actions | WF, Action | v1.23.0 | Informational / Regular（一部 Pedantic） | ❌ | ❌ |
| template-injection | WF, Action | v0.1.0 | High / Regular（不審度の低い展開は Low/Pedantic など） | ⚠️ | ❌ |
| typosquat-uses | WF, Action, pre-commit | v1.26.0 | High(conf Low) / Regular | ❌ | ❌ |
| undocumented-permissions | WF | v1.13.0 | Low / **Pedantic** | ❌ | ❌ |
| unpinned-images | WF, Action | v1.7.0 | High / Regular（一部 Pedantic） | ❌ | ❌ |
| unpinned-tools | WF, Action | v1.25.0 | Medium / Regular | ❌ | ❌ |
| unpinned-uses | WF, Action | v0.4.0 | High / Regular | ⚠️ | ✅ `policies` |
| unredacted-secrets | WF, Action | v1.4.0 | Medium / Regular | ❌ | ❌ |
| unsound-condition | WF, Action | v1.12.0 | High / Regular | ✅ | ❌ |
| unsound-contains | WF | v1.7.0 | High / Regular | ❌ | ❌ |
| unsound-ternary | WF, Action | v1.26.0 | Low / Regular | ❌ | ❌ |
| use-trusted-publishing | WF | v0.1.0 | Informational / Regular | ❌ | ❌ |

表の見方：
- 「対象」「導入版」「自動修正」「設定」の列は [audits.md](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/docs/audits.md) の各節の表から取った。自動修正の記号は、✅ が safe fix、⚠️ が unsafe fix（`--fix=all` が必要）を表す。
- 設定できる項目の見出し（`grep '^#### \`rules\.'`）は `dependabot-cooldown.config.days`、`forbidden-uses.config.<allow|deny>`、`known-vulnerable-actions.config.allow`、`secrets-outside-env.config.allow`、`unpinned-uses.config.policies` の5つ。
- persona の観点では、**regular（既定）では出ない監査がある**。Pedantic 以上で出るのが `concurrency-limits`、`undocumented-permissions`、`anonymous-definition`、Auditor でのみ出るのが `self-hosted-runner`、`secrets-outside-env` だった。

**`unpinned-uses` の既定ポリシー（確認済み、audits.md より）**
v1.20.0 以降は「すべての action を SHA で固定する」一律ポリシーになった。どのルールにも一致しない uses には暗黙の `"*": hash-pin` が適用される。ポリシーの値は `hash-pin` / `ref-pin` / `any` の3つ。

```yaml
rules:
  unpinned-uses:
    config:
      policies:
        actions/checkout: hash-pin
        actions/*: ref-pin
```

**`forbidden-uses`** は opt-in で、設定しなければ何もしない。`config.allow`（許可リスト）か `config.deny`（拒否リスト）を書き、値には repository pattern（`owner/repo/subpath@ref`、`owner/repo`、`owner/repo/*`、`owner/*`、`*`）を使う。

### B-4. 設定ファイルの探索と書式（確認済み）

出典は [configuration.md](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/docs/configuration.md)。

- git リポジトリ内では、リポジトリルートで次の順に探す：`.github/zizmor.yml` → `.github/zizmor.yaml` → `zizmor.yml` → `zizmor.yaml`。
- `--config` や `ZIZMOR_CONFIG` を指定すると、その1ファイルだけを全入力に使い、ローカルの探索は行わない。
- `--no-config` を付けると設定を一切読まない。
- キーは `rules.<id>.disable`（v1.13.0〜）、`rules.<id>.ignore`、`rules.<id>.config`、`rules.<id>.remap.severity`（v1.25.0〜）。
- `ignore` の書式は `filename.yml[:line[:column]]`。filename は**ベース名で照合する**。

実測（[b/.github/zizmor.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/b/.github/zizmor.yml) を自動で読み込んだ）：
- `unpinned-uses.config.policies: {actions/*: ref-pin}` → unpinned-uses の指摘が消えた。
- `forbidden-uses.config.deny: [actions/setup-node]` → `error[forbidden-uses]: forbidden action or repository used` が出た。
- `dependabot-cooldown.config.days: 3` → cooldown の指摘が消えた（Dependabot の暗黙の既定は3日）。
- `template-injection.ignore: [action.yml]` → composite action 側の2件が ignored になった。

ドキュメントには「Composite action findings cannot be ignored via `zizmor.yml` currently」と書かれているが、実際には抑止できた。理由はソースにある。照合がベース名だけで行われるので、`action.yml` と書くと**すべての composite action が一律に対象になってしまい、個別の action を指定できない**、というのが実態だった。
- 根拠：[config/mod.rs 801〜807行目](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/src/zizmor/crates/zizmor/src/config/mod.rs:801:1)
> `// TODO: This needs to filter on something other than filename, since that doesn't work for action definitions (which are all \`action.yml\`).`

**インライン抑止（確認済み）**
`# zizmor: ignore[audit-name]` と書く。カンマ区切りで複数指定でき（`# zizmor: ignore[artipacked,ref-confusion]`）、後ろに説明文を続けてもよい。コメントは YAML コメントとして認識される位置に置く必要があり、`run: |` のブロック文字列の中に書いても効かない（usage.md「With comments」）。
実測では、`- uses: actions/checkout@v4 # zizmor: ignore[artipacked]` で artipacked が ignored になった。

### B-5. サンプルへの実行結果（plain 形式、確認済み）

サンプルは次の3ファイル。
- [ci.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/b/.github/workflows/ci.yml)：`actions/checkout@v4`、persist-credentials 未設定、permissions なし、`${{ github.event.pull_request.title }}` を run に埋め込み
- [action.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/b/.github/actions/hello/action.yml)：composite action
- [dependabot.yml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/b/.github/dependabot.yml)：cooldown なし

コマンド：`uvx zizmor@1.31.1 --offline --no-progress --color=never --show-audit-urls=never --render-links=never .`（設定ファイルを置く前、ignore コメントなし）
```
error[template-injection]: code injection via template expansion
  --> ./.github/actions/hello/action.yml:12:28
error[template-injection]: code injection via template expansion
  --> ./.github/actions/hello/action.yml:12:46
error[unpinned-uses]: unpinned action reference
  --> ./.github/actions/hello/action.yml:10:13   (action is not pinned to a hash (required by blanket policy))
warning[dependabot-cooldown]: insufficient cooldown in Dependabot updates
 --> ./.github/dependabot.yml:3:5   (insufficient implicit default-days (less than 7))
warning[artipacked]: credential persistence through GitHub Actions artifacts
 --> ./.github/workflows/ci.yml:8:9   (does not set persist-credentials: false)   = note: audit confidence → Low
warning[excessive-permissions]: overly broad permissions
  --> ./.github/workflows/ci.yml:5:3   (default permissions used due to no permissions: block)
error[template-injection]: code injection via template expansion
  --> ./.github/workflows/ci.yml:10:24
error[unpinned-uses]: unpinned action reference
 --> ./.github/workflows/ci.yml:8:15
11 findings (3 suppressed, 1 safe fixes, 4 unsafe fixes): 0 informational, 0 low, 3 medium, 5 high
exit=14
```
`--persona=pedantic` を付けると、さらに `excessive-permissions`（ワークフロー単位、Pedantic）、`anonymous-definition`（Informational）、`concurrency-limits`（Low）が出た。

`--format=github` の出力例：
```
::error file=.github/actions/hello/action.yml,line=12,title=template-injection::action.yml:12: code injection via template expansion: may expand into attacker-controllable code
```

### B-6. composite action と dependabot.yml も監査するか（確認済み）

どちらも監査する。上の実行で `action.yml`（composite）と `dependabot.yml` の両方に指摘が出ており、ログにも次の行が出た。
```
registering action input ... action.yml
registering dependabot config input ... dependabot.yml
```
加えて `--collect=pre-commit` を指定すると、`.pre-commit-config.yml` と `.pre-commit-hooks.yml` も対象になる（help の記述）。

---

## C. yamllint 1.38.0

### C-1. ルール一覧（確認済み）

`yamllint.rules._RULES` を出力した結果と、https://yamllint.readthedocs.io/en/stable/rules.html （WebFetch）の内容が一致した。全部で **23 ルール**。

`anchors, braces, brackets, colons, commas, comments, comments-indentation, document-end, document-start, empty-lines, empty-values, float-values, hyphens, indentation, key-duplicates, key-ordering, line-length, new-line-at-end-of-file, new-lines, octal-values, quoted-strings, trailing-spaces, truthy`

主なルールの既定オプション（ソースの `DEFAULT` を出力した、確認済み）：
- `truthy`: `allowed-values: ['true','false']`, `check-keys: True`
- `indentation`: `spaces: 'consistent'`, `indent-sequences: True`, `check-multi-line-strings: False`
- `line-length`: `max: 80`, `allow-non-breakable-words: True`
- `comments`: `require-starting-space: True`, `min-spaces-from-content: 2`
- `quoted-strings`: `quote-type: 'any'`, `required: True`（`only-when-needed` も指定できる）
- `key-duplicates`: `forbid-duplicated-merge-keys: False`
- `anchors`: `forbid-undeclared-aliases: True`, `forbid-duplicated-anchors: False`, `forbid-unused-anchors: False`
- `octal-values` / `float-values` / `quoted-strings` / `key-ordering` / `empty-values` / `document-end` は、`extends: default` では disable になっている（conf/default.yaml）。
- default.yaml では `comments`、`comments-indentation`、`document-start`、`truthy` が `level: warning`。

### C-2. インライン無効化（確認済み）

出典は https://yamllint.readthedocs.io/en/stable/disable_with_comments.html と実測。

- `# yamllint disable-line rule:truthy`：同じ行の末尾に書いても、1行上に書いても効く（実測で両方効いた）。
- `# yamllint disable rule:truthy` 〜 `# yamllint enable rule:truthy`：範囲を指定して無効にする。`rule:` は空白区切りで並べられる。
- `# yamllint disable` 〜 `# yamllint enable`：全ルールを無効にする（ドキュメントは非推奨としている）。
- `# yamllint disable-file`：**ファイルの1行目**に書く必要がある。

### C-3. 出力形式と終了コード（確認済み）

`-f {parsable,standard,colored,github,auto}` から選べる。`-s/--strict` を付けると warning でも非0になる。`--no-warnings` を付けると error だけを出す。

| 状況 | 終了コード | 根拠 |
|---|---|---|
| 問題なし、または warning のみ（strict なし） | 0 | cli.py 249〜250行目、実測 |
| error あり | 1 | cli.py 245〜246行目、実測 |
| warning のみ + `--strict` | 2 | cli.py 247〜248行目（`return_code = 2 if args.strict else 0`）、実測 `exit=2` |
| 設定が不正、ファイルが無い | 255（`sys.exit(-1)`） | 実測：`invalid config: no such rule …` → `exit=255` |

設定ファイルの探索順は、`-d`/`-c` の指定 → カレントから親ディレクトリへ `.yamllint` / `.yamllint.yaml` / `.yamllint.yml` → `$YAMLLINT_CONFIG_FILE` → `$XDG_CONFIG_HOME/yamllint/config`（無ければ `~/.config/yamllint/config`）。cli.py の 133〜200 行目で確認した。

### C-4. GitHub Actions 向けの厳格な設定（実測で動作を確認済み）

まず、既定の設定のままだと何が起きるかを確かめた。正しいワークフローでも `on:` が truthy として、`@sha # v4.3.0`（コメント前の空白が1つ）が comments として warning になり、`--strict` を付けると exit 2 で落ちる。

```
$ uvx yamllint@1.38.0 -d default --strict -f parsable .github/workflows/good.yml
good.yml:1:1: [warning] missing document start "---" (document-start)
good.yml:2:1: [warning] truthy value should be one of [false, true] (truthy)
good.yml:13:73: [warning] too few spaces before comment: expected 2 (comments)
exit=2
```

これを踏まえて作った設定が [y/.yamllint.yaml](/private/tmp/claude-501/-Users-opm008761-Documents-project-practice/f475fdbf-dad8-426f-919e-790ae151d81a/scratchpad/tools-probe/y/.yamllint.yaml) である。
```yaml
---
extends: default
rules:
  document-start: disable
  truthy: {allowed-values: ["true", "false"], check-keys: false, level: error}
  line-length: {max: 120, level: error}
  indentation: {spaces: 2, indent-sequences: true}
  comments: {min-spaces-from-content: 1, level: error}   # pinact/Dependabot の "@sha # vX" 形式に合わせる
  comments-indentation: {level: error}
  key-duplicates: {forbid-duplicated-merge-keys: true}
  quoted-strings: {quote-type: double, required: only-when-needed}
  empty-values: {forbid-in-block-mappings: false}
  octal-values: enable
  float-values: enable
  anchors: {forbid-unused-anchors: true, forbid-duplicated-anchors: true}
```
- `good.yml`（`on:`、`workflow_dispatch:` の null 値、`@sha # v4.3.0` を含む）→ `--strict -f parsable` で `exit=0`。
- `bad.yml` → `exit=1`。次の指摘が出た：
```
bad.yml:1:7: [error] string value is redundantly quoted with double quotes (quoted-strings)
bad.yml:3:5: [error] wrong indentation: expected 2 but found 4 (indentation)
bad.yml:7:24: [error] truthy value should be one of [false, true] (truthy)
bad.yml:8:5: [error] duplication of key "runs-on" in mapping (key-duplicates)
bad.yml:10:5: [error] wrong indentation: expected 6 but found 4 (indentation)
bad.yml:10:19: [error] trailing spaces (trailing-spaces)
bad.yml:11:121: [error] line too long (136 > 120 characters) (line-length)
bad.yml:12:5: [error] no new line character at the end of file (new-line-at-end-of-file)
```

---

## D. PyYAML 6.0.3 の `yaml.compose()`（確認済み）

コマンド：`uv run --no-project --with pyyaml==6.0.3 python -I -c '...'`（Python 3.14.5 と 3.9.6 の両方で実行した）

```
pyyaml 6.0.3 python 3.14.5 libyaml True
'name' tag:yaml.org,2002:str  start_mark.line= 0 col= 0 -> value node ScalarNode
'on'   tag:yaml.org,2002:bool start_mark.line= 1 col= 0 -> value node MappingNode
'jobs' tag:yaml.org,2002:str  start_mark.line= 4 col= 0 -> value node MappingNode
safe_load keys: ['name', True, 'jobs']
CSafeLoader compose: [('name', 'tag:yaml.org,2002:str', 0), ('on', 'tag:yaml.org,2002:bool', 1), ('jobs', 'tag:yaml.org,2002:str', 4)]
```
結果から分かることは4点ある。

1. `yaml.compose()` が返すノードには `start_mark.line` と `end_mark.line` がある。値は **0 始まり**なので、エディタの行番号にするには +1 する。
2. キー `on` のスカラーノードの `.value` は、生の文字列 `'on'` のまま残る。
3. ただし `tag` は compose の段階で既に `tag:yaml.org,2002:bool` に解決されている。依頼文の「bool になるのは construction 時だけ」という理解は、**値（`.value`）については正しいが、tag については正しくない**。`True` に変わるのは `safe_load`（construct）のときである。
4. クォートした `"on"` は `tag:...:str`、`style='"'` になる。また compose は重複キーをエラーにせず、すべてノードとして保持する（`safe_load` では後勝ちになる）。
```
[('on', 'tag:yaml.org,2002:str', '"', 0, 0), ('on', 'tag:yaml.org,2002:bool', None, 1, 1), ('on', 'tag:yaml.org,2002:bool', None, 2, 2)]
safe_load: {'on': 1, True: 3}
```

---

## E. 代替・補完ツール（存在と最新版のみ）

| ツール | 最新の安定タグ | 根拠 | 状態 |
|---|---|---|---|
| zizmorcore/zizmor-action | v0.7.1 | `git ls-remote --tags https://github.com/zizmorcore/zizmor-action` → `v0.7.0, v0.7.1` | 確認済み |
| suzuki-shunsuke/ghalint | v1.5.6（ほかに `v1.5.7-0`, `v1.5.7-1` というタグもある） | `git ls-remote --tags` | 確認済み（`-0`/`-1` がプレリリースかどうかは未確認） |
| suzuki-shunsuke/pinact | v5.0.1 | `git ls-remote --tags` → `v5.0.0, v5.0.1` | 確認済み |

- **zizmor-action**（https://raw.githubusercontent.com/zizmorcore/zizmor-action/main/README.md 、確認済み）
  - inputs は `inputs`, `collect`, `online-audits`（既定 `true`。CLI とは既定が逆）, `persona`, `min-severity`, `min-confidence`, `version`（既定 `latest`）, `token`（既定 `${{ github.token }}`）, `advanced-security`（既定 `true`。SARIF を Advanced Security にアップロードする）, `annotations`（既定 `false`）, `color`, `config`, `fail-on-no-inputs`。
  - zizmor は PyPI から取得するため、ランナーに Python が必要。
- **ghalint**（https://raw.githubusercontent.com/suzuki-shunsuke/ghalint/main/README.md 、確認済み）
  - Workflow 向けポリシー：`job_permissions`, `deny_read_all_permission`, `deny_write_all_permission`, `deny_inherit_secrets`, `workflow_secrets`, `job_secrets`, `deny_job_container_latest_image`, `action_ref_should_be_full_length_commit_sha`, `github_app_should_limit_repositories`, `github_app_should_limit_permissions`, `job_timeout_minutes_is_required`, `checkout_persist_credentials_should_be_false`
  - Action 向けポリシー：`action_ref_should_be_full_length_commit_sha`, `github_app_should_limit_repositories`, `github_app_should_limit_permissions`, `action_shell_is_required`, `checkout_persist_credentials_should_be_false`
  - コマンドは `ghalint run`（workflow）と `ghalint run-action` / `ghalint act`（action.yaml）。設定ファイルは `^(\.|\.github/)?ghalint\.ya?ml$`。
  - zizmor に無い観点として `job_timeout_minutes_is_required`（timeout-minutes を必須にする）と `action_shell_is_required` がある。
  - 実行はしていない（未確認）。
- **pinact**（https://raw.githubusercontent.com/suzuki-shunsuke/pinact/main/README.md 、確認済み）
  - action と reusable workflow を SHA で固定し、バージョンコメントを付ける CLI。
  - `pinact run --check`（編集せずに検査）、`--no-api`（オフライン検査）、`--verify-comment`、SARIF 出力などがある。
  - 実行はしていない（未確認）。

---

## 未確認・注意事項のまとめ

- zizmor のオンライン専用監査5種は、トークンが無いため**実際の出力を観測していない**（未確認）。
- zizmor の終了コード 2 と 3 は実測していない（ドキュメント上は確認済み）。
- zizmor の severity / persona は指摘ごとに変わる。B-3 の表はテストデータで観測した値であり、網羅を保証しない。
- ドキュメントと実装の食い違いが2点あった。
  - `ref-version-mismatch` は表では offline ✅ だが、実装ではオンライン専用。
  - composite action の ignore は「できない」と書かれているが、実際にはベース名 `action.yml` による一括抑止になる。
- actionlint-py は sdist のため、インストール時に GitHub のリリースページへアクセスする。ネットワークが制限された CI では失敗しうる（ネットワーク制限下での動作は未確認）。
- 依頼文にあった「SC2086 の検出例 `[ $VAR = x ]`」は、同じスクリプト内で定数を代入した変数では検出されない。`env:` 由来の変数を使う必要がある。
