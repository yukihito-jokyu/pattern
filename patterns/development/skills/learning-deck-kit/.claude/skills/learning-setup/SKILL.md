---
name: learning-setup
description: 学びたいプログラミング言語・フレームワーク・ライブラリの公式資料と学習順序を調べ、対象専用スキルとhtml-deckを埋め込むHTML教材をセットアップする。体系的に学びたい、技術の学習スキルを作りたい、教材を追加・更新したい依頼で使う。
---

# 技術を体系的に学ぶ教材を用意する

単発の解説で終わらず、前提を積み上げる学習順序・公式資料の取得手順・学習項目ごとのページを利用先に残す。スライドは簡潔にし、前提・具体例・流れはその外側へ書く。

## 最初に確定すること

依頼と既存ファイルから、対象技術、対象版、到達目標、前提知識、教材の出力先を確認する。既に分かっている値を聞き直さない。不足して構成が変わる項目だけをまとめて質問する。学習形式は非同期自習、枚数は1項目2枚から始める既定値とし、指定があれば従う。

1. 公式サイト・公式リポジトリ・レジストリの情報を突き合わせ、資料の所有者と対象版を確かめる。URLを記憶で組み立てない。
2. Getting started、言語/API仕様、release notesを実際に取得する。HTML外枠だけ・404・取得拒否は本文取得済みと扱わない。
3. 前提から到達目標までの学習項目を並べる。各項目に1つのgoalと先行項目dependsOnを設定する。
4. [教材データと制作手順](references/authoring.md)の形式でprofile.jsonを作り、同梱CLIを実行する。

```sh
node "<このスキル>/scripts/learning.mjs" setup profile.json learning/<id> .agents/skills
```

Claude Codeへ導入する場合は最後の引数を.claude/skillsにする。これでlearn-idスキル、資料一覧、情報取得・更新手順を生成する。指定したskills-dirにはこのlearning-setupの自己完結コピーも置く。既存の異なるファイルとの衝突では書き込まず停止する。教材本文はこの段階では未作成である。

## 教材を作る

PROC-01：資料取得 → profileと順序 → 各スライド → 外側の説明 → 注目対象 → 検証の順で作る。

生成したlearn-idを読み、[authoring.md](references/authoring.md)に従う。各項目のdeckは必ず同梱 [html-deck](vendor/html-deck/SKILL.md) を使う。html-deckに渡すgoal、audience、situation、枚数は確定済みのprofileと自習条件から引き継ぎ、同じ質問を項目ごとに繰り返さない。スライドの制作・実測・批評はhtml-deckの手順に従う。

取得した公式資料の節を出典に対応付ける。URL形式や日付の検査は資料の内容確認を代行しない。実行例は実際に動かし、実測した出力と期待だけの出力を分けて説明する。

## 検証して渡す

```sh
node "<このスキル>/scripts/learning.mjs" check learning/<id>
node "<このスキル>/scripts/learning.mjs" build learning/<id> learning-site/<id>
node "<このスキル>/scripts/learning.mjs" sync-skill learning/<id> .agents/skills
```

同一originのHTTPで学習ページとスライドを開く。スライド切替、左右の説明、丸枠と矢印、表示ON/OFF、狭い画面、キーボードを確認する。file://での注目表示は対応条件に含めない。

- PROC-02：profile、lesson本文、deck、注目対象、実行結果、生成スキルの対応を照合する。
- OPS-01：取得した本文・対象版と説明を照合し、未取得を確認済みにしない。
- PROC-03：作成先、到達目標に対する範囲、実施検証、失敗・未実施、人間の確認待ちを報告する。
