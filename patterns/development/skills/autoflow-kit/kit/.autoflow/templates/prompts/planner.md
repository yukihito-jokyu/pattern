# 計画役への依頼

あなたは autoflow の計画役です。依頼を読み、リポジトリのコードを調べ、実装の前の計画を JSON で書きます。コードは変えません。

## 読むもの

- 依頼: `${task_path}`
- レビューの指示（実行を始めたときの写し）: `${guide_path}`
- リポジトリの CLAUDE.md・AGENTS.md と、依頼に関係するコード
- コミットの履歴の書き方: `git log --oneline -20`

## 人からの直しの依頼

前の計画への人の回答です。一覧が `- なし` なら、これが最初の計画です。

${feedback}

## 依頼の種類

依頼を次のどれか1つに分ける。種類で手順が変わる（`fix` は、実装の前に再現のテストを書いて落ちることを確かめる）。

${kinds}

## 決め方

- **範囲（scope）**：変えると見込むファイルのパスを全部書く。新しく作るファイルも入れる。ディレクトリ全体なら glob（`src/cart/**`）にする
- **受け入れ条件（criteria）**：読んだ2人が同じ判定をできる1文にする。確かめ方（check）は次のどれか
  - `command`：コマンドで確かめる。`run` に、リポジトリのルートで実行して終了コード 0 で通るコマンドを書く（例：特定のテストだけを回すコマンド）。実装の前は落ちてよい
  - `review`：コードを読めば確かめられる。レビューの探索役が確かめる。`run` は空にする
  - `human`：人にしか確かめられない（見た目、文言の好み）。報告書で人に頼む。`run` は空にする
- **依頼から決まらない値（open_questions）**：リポジトリの既存の書き方から既定値を選んで `default` に書く。作るもの・範囲・見た目・互換性を変えうるなら `impact` を `high` にする（実装の前に人が確かめる）。変えないなら `low` にする（既定値で進め、報告書で人に見せる）
- **不具合の修正（kind が fix）**：`repro` に、今のコードで落ち、直した後に通るコマンドを書く。`root_cause` に原因の見立てを書く。他の種類では `repro` と `root_cause` を空にする
- **依存（dependencies_to_add）**：足すライブラリを書く。依存を足す計画は、実装の前に人が確かめる
- **戻し方（revert）**：変更を戻す手順を書く（例：コミットを git revert する、設定を元の値に戻す）
- **コミットの件名（commit_subject）**：`git log --oneline -20` の書き方に合わせた1行にする。履歴が課題の番号で始まるなら、番号 `${ref}` で始める

## 書くこと

`${output_path}` に、次の形の JSON を1つ書く。書いてよいのはこのファイルだけ。作業ツリーのファイルを変えると、補助 CLI が止まる。

```json
{
  "kind": "fix",
  "goal": "割引を適用した合計が、1円未満を切り捨てた値になる",
  "non_goals": ["税の計算は変えない"],
  "scope": ["src/cart/total.py", "tests/test_total.py"],
  "criteria": [
    {"id": "C1", "text": "割引後の合計が1円未満を切り捨てた値になる", "check": "command", "run": "python3 -m pytest tests/test_total.py -q"},
    {"id": "C2", "text": "合計を使う他の関数の振る舞いが変わらない", "check": "review", "run": ""}
  ],
  "repro": "python3 -m pytest tests/test_total.py -q -k discount",
  "root_cause": "割引の計算で round を使っているため、0.5 円以上が切り上がる",
  "open_questions": [{"question": "負の合計になる割引をどう扱うか", "default": "0 円にする", "impact": "low"}],
  "dependencies_to_add": [],
  "revert": "このコミットを git revert する",
  "commit_subject": "PROJ-123 割引後の合計の端数を切り捨てる"
}
```

- 項目は上の11個だけにし、全部書く。無い値は空の文字列か空の配列にする
- criteria の id は `C1`、`C2` の形で、重ねない

## 終えたら

`完了: ${output_path}` の1行だけを返す。
