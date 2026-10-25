# draw.ioでドメインモデル図を作成するスキル

業務の説明や具体例から概念・関連・多重度・ルールを整理し、再編集できる `.drawio.png` と判断メモを作るCodex用スキルです。設計モデルを求めた場合は、責務・不変条件・集約候補を概念図と分けて検討します。

図にはモデルの概念・属性・関連・多重度などを描き、目的・範囲・記法の説明・仮定・設計理由・未決事項は図外のMarkdownへまとめます。図への補足が必要な場合は、包含する境界、対象に結び付く短い制約ノート、遷移のガードなどで表します。

```text
skills/drawio-domain-model/
  SKILL.md                         スキルの入口
  references/modeling.md           モデルを選ぶ判断
  references/drawio.md              XML・PNG書き出し・検査
  scripts/validate_drawio.py        PNGと全ページの構造検査
  assets/model-notes.md.template    判断メモのひな形
examples/
  order-cancellation.md             注文キャンセルの判断メモ
  order-cancellation.drawio.png     図データ入りPNG（全3ページ）
tests/test_validate_drawio.py       正常例・代表的な破損例の検査
ci.json                            CIの検査コマンド
```

## 環境と導入

スキルを読み込めるCodex、PNGを描画するdraw.io DesktopのCLI、構造検査用のPython 3.12以上を用意します。追加のPythonライブラリ、サイト側のNode.js依存関係、APIキーは不要です。図はXMLを直接書いてCLIでPNGへ書き出すため、通常の作図にGUI操作は必要ありません。CLIを使えない場合はWeb版またはDesktop版のエディターでの書き出しも利用できます。

ZIPを展開し、このREADMEがあるフォルダーを作業場所にします。利用先プロジェクトのパスを `project_root` へ設定して、スキルのフォルダーをコピーします。

```sh
project_root=/path/to/your-project
mkdir -p "$project_root/.agents/skills"
test ! -e "$project_root/.agents/skills/drawio-domain-model" && \
  cp -R skills/drawio-domain-model "$project_root/.agents/skills/"
```

コピー先が既に存在する場合は上のコマンドでは上書きしません。既存スキルとの違いを確認して、必要な変更だけを取り込んでください。導入後、利用先プロジェクトでCodexを開きます。別のAIツールを使う場合は、そのツールのスキル探索先に合わせて同じフォルダーを配置しますが、専用設定や動作保証はこのパターンには含めません。

## 使用方法

業務の目的・範囲・分かっているルールを伝えます。例えば利用先プロジェクトのCodexに、次のように依頼します。

```text
$drawio-domain-model
注文キャンセルの成立条件を整理する概念モデルを作成してください。
会員が注文し、確定した注文には明細が1件以上あります。
出荷確定前はキャンセルでき、決済済みなら返金が必要です。
再キャンセル要求と返金失敗時の対応はまだ決まっていません。
成果物は docs/models/order-cancellation.drawio.png と
docs/models/order-cancellation.md に保存してください。
```

スキルは不足を質問または未決として示し、未確定の扱いを勝手に決めず、概念図と図外の判断メモを作ります。判断メモではページ名と要素名で図を参照します。設計も必要なら「責務・不変条件・集約候補を別ページで検討して」と加えます。学習用の作例にある仮定は、自分の業務の確定ルールにはしません。

出力の `.drawio.png` は通常の画像として表示できます。draw.ioのFile → Open from → Deviceで開くと、埋め込まれた図形と接続線を編集できます。同梱の `examples/order-cancellation.drawio.png` は、画像としては概念図を表示し、draw.ioでは全3ページを開けます。図の目的・範囲、記法の読み方、仮定と未決事項は、同梱の `examples/order-cancellation.md` を参照してください。

基本の作成手順はXMLの直接作成、CLIの `--embed-diagram` によるPNG書き出し、PNGと全ページXMLの検査です。Desktop CLIの例はスキル内の `references/drawio.md` にあります。GUIで書き出す場合は、File → Export as → PNGで **Include a copy of my diagram** と図全体・全ページを含む設定を選びます。図データ埋め込みを外すと、見た目を残しても図形として再編集できなくなります。どの書き出し手段も利用できない環境では、スキルはPNGの生成を未実施として報告します。

## 検証

展開先のこのREADMEがあるフォルダーで、準備を確認してから検査します。

```sh
python3 --version
python3 skills/drawio-domain-model/scripts/validate_drawio.py examples/order-cancellation.drawio.png
python3 -m unittest discover -s tests -v
```

2つ目のコマンドはPNG画像と埋め込まれた全ページを検査し、`OK: PNG` に続いて画像サイズと `3 pages: 概念モデル, 設計候補, 注文状態遷移` を表示します。テストは同梱作例に加え、一時ファイルへ作った正常例と、CRC不一致・画像破損・図データ欠落・XML破損・参照切れ・累積展開量の超過などを検査し、最後に `OK` を表示します。検査対象ファイルは変更しません。準備や検査が失敗した場合は、後続を成功として扱わず原因を確認します。

`ci.json` はPython 3.12と、同じ `python3 -m unittest discover -s tests -v` を指定します。CIの検査にはdraw.ioのインストールやネットワークアクセスは不要です。図の描画やエディターでの操作を、このCIが行うわけではありません。

検査は静止・非インターレースPNGを対象とし、入力は32MiBまでです。展開量はファイル全体で共有し、PNGの画像データ、図メタデータ、各圧縮ページの展開後のバイト数を合計して64MiBまでに制限します。上限を超える場合は倍率を下げるか図を分割します。これは展開量の上限であり、文字列やXML解析に必要なメモリ使用量そのものの上限ではありません。構造検査後は各ページをCLIで一時PNGへ書き出し、画像の文字・線を確認します。GUIでのコピー上の編集・PNG保存・再読み込みは、利用者が希望する場合などの追加確認です。業務ルールの妥当性は具体例で検証し、業務担当者と確認します。
