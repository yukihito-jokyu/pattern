# 学習項目の制作手順

このスキルのscripts/learning.mjsはNode22以上の標準ライブラリだけで動く。スライドの生成・実測にはPython3.14、uv、Google Chromeが必要。閲覧はブラウザだけでよい。

## 対象技術と資料を保存する

profile.jsonの全キーを次の形で用意する。versionは制作対象、sources.versionは資料が扱う版、checkedAtは実際に本文を確認した日である。CLIはその日付の事実までは証明しない。

```json
{
  "schemaVersion": 1,
  "id": "go",
  "title": "Goの基本を順に学ぶ",
  "technology": "Go",
  "version": "1.27",
  "goal": "値と制御と関数の流れを説明できる",
  "audience": "Goを初めて読む人",
  "officialHosts": ["go.dev"],
  "sources": [
    {
      "id": "variables",
      "title": "Variable declarations",
      "url": "https://go.dev/ref/spec#Variable_declarations",
      "version": "go1.27",
      "checkedAt": "2026-10-24"
    }
  ],
  "curriculum": [
    {
      "id": "variables",
      "title": "変数と型",
      "goal": "宣言と代入を区別できる",
      "dependsOn": []
    }
  ]
}
```

これは形の例でありGoへの限定ではない。別の技術では全ての固有値を実際に調べて置き換える。公式hostはhost名だけで登録する。dependsOnは先に並んだ項目だけを参照できる。

## html-deckで各項目を作る

コース内はlessons/<id>/lesson.jsonとdeck/を1組にする。以下のdeck CLIはこのスキルのvendor/html-deck/toolsを参照する。

```sh
uv run --locked --python 3.14 --project "<このスキル>/vendor/html-deck/tools" html-deck-init "<course>/lessons/<id>/deck" --title "学習項目の題名"
```

作る前にhtml-deck/SKILL.mdと品質契約を読む。deck.mdに確定済みのgoal/audience/situation/constraintsと利用できるスキルを記録する。スライドは1枚1主張とし、図や短い例で全体像を示す。詳細を詰め込まず外側へ回す。theme.cssは独立スライドで使い、学習ページ側のCSSをコピーしない。

注目したい要素へ `data-learning-target="declaration"` のような安定IDを付ける。対象は各スライドで1要素にだけ付ける。スライドのscriptを許可する必要はない。

## 外側の説明をlesson.jsonへ書く

必須キーはschemaVersion,id,title,goal,prerequisites,explanation,exercise,sources,slides。titleとgoalはcurriculumと一致させる。

- prerequisites：前提知識を説明する文字列の配列。単なる用語名で済ませない。
- explanation：{title,body,code,output}の配列。前提→処理→結果→次との関係を文章でつなぐ。コードがない節ではcode/outputを空文字にする。
- exercise：{prompt,answer}。手を動かす問いと、そうなる理由を示す。
- sources：profileにある出典ID配列。
- slides：{file,title,notes}配列。fileは01.htmlのようなdeck/slides内のHTMLファイル名。
- notes：{id,target,side,title,body}配列。sideはleft/right。targetはdata-learning-targetの値。説明は「この行が何を受け取り、どう変わり、次へ何を渡すか」を書く。

notesのid/targetは1枚内で重複させない。スライドを修正したら参照先と説明も同時に更新する。

## 検査と閲覧

html-deck-checkはindex.htmlを同期し、.loopへ実測を出す。検証ではdeckをOS一時ディレクトリへコピーしてから実行し、元の教材を変更しない。

```sh
uv run --locked --python 3.14 --project "<このスキル>/vendor/html-deck/tools" html-deck-check "<一時コピーのdeck>"
```

終了0はblockなしを示す。review所見と意味の正しさは別途確認する。通常motion、縮小、スライド切替後の注目位置は学習ページ側でも確認する。

checkとbuild後は出力先をHTTPサーバーで配信する。キットのtools/serve.mjsを利用するか、利用先の静的サーバーを使う。出力先には所有マーカーが付き、再生成では記録された生成物だけを更新する。手編集された生成物や利用者ファイルとの衝突では失敗するため、編集はprofile/lesson/deckへ戻す。

## 資料を更新する

同じ公式URLと対象版を再取得し、release notesを読む。URL移動、本文取得不能、対象版との違いを区別する。影響する本文・コード・出力・注目点を更新し、check/buildと実測検査を繰り返す。sync-skillで生成スキルの資料一覧も更新する。
