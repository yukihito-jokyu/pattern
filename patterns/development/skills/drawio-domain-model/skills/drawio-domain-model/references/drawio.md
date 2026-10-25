# 編集できる.drawio.pngを作成する

## ページとセルを作る

成果物は通常のPNG画像として表示でき、draw.ioで開くと図形・接続線・全ページを復元できる `.drawio.png` にする。[公式のPNG書き出し](https://www.drawio.com/docs/manual/export/export-to-png/)では、図のコピーを含める設定と、全ページを含める設定を選べる。PNGの画面に全ページを並べるという意味ではない。

XMLを直接書くことを基本とし、例えば次のように一時 `.drawio` を作る。`mxfile` がファイル、`diagram` がページ、`mxGraphModel/root` 内の `mxCell` が図形や接続線である。ページ内でIDを重複させず、名前を直しても同じ概念のIDを保つ。`0` と、その子のレイヤー `1` を置き、図形はレイヤーを親にする。

```xml
<mxfile>
  <diagram id="conceptual" name="概念モデル">
    <mxGraphModel page="1" pageWidth="1200" pageHeight="800">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="order" value="注文&#xa;注文番号・状態"
                vertex="1" parent="1" style="whiteSpace=wrap;html=0;">
          <mxGeometry x="40" y="40" width="240" height="120" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

この最小例に、必要な概念・属性・関連を加える。関連のセルは `edge="1"`、`source` と `target` に図形IDを指定し、`mxGeometry relative="1" as="geometry"` を置く。通常の関連には `startArrow=none;endArrow=none;` を指定する。多重度は接続線を親にした独立したラベルセルにすると、線との対応を保ちやすい。通常の図形には幅・高さ、関連ラベルには相対座標を与える。

XML属性では `&` を `&amp;`、`<` を `&lt;`、引用符を `&quot;` としてエスケープする。HTMLラベルを使う場合は、その中のHTMLもXML属性の値としてエスケープする。色だけで確定・仮定・未決・設計候補を区別しない。

図の目的・範囲・用語の説明・凡例・判断理由・仮定・未決事項の一覧は外部の判断メモに置く。図は概念名、属性名、関連名、多重度、境界、状態、遷移などで構成し、説明用の文章枠は作らない。補足を加えるときは、何をどの対象との関係で伝えるかを決め、包含や接続、境界、短いガードで表す。必要な制約ノートは対象へ破線で結び付ける。文章を別のdraw.ioページへ移すだけで説明を分離したことにしない。

箱の幅と文字サイズをそろえ、関連ラベルと多重度が線のどちらの端に対応するかを読める間隔にする。説明を外へ移した後に大きな空白を残さず、図の構造に合わせて配置と外周の余白を整える。

## 実際に描画して書き出す

Desktop CLIの実行ファイルを確認して次の形式で書き出す。`DRAWIO_BIN` は利用環境のdraw.io実行ファイル、入力XMLは作業用の一時ファイルである。これはPNGを描画するためのコマンドであり、GUI画面を操作して図を作る手順ではない。

```sh
"$DRAWIO_BIN" --export --format png --embed-diagram --border 24 \
  --scale 1.5 --timeout 60 \
  --output output/domain-model.drawio.png /tmp/domain-model.drawio
```

`--embed-diagram` が再編集用の図データを含める指定である。画像は既定で先頭ページを描画する。`--page-index 2` なら2ページ目を画像にするが、埋め込みデータの全ページ保持は最終PNGを開いて確認する。`--all-pages` はPDF/HTML用なのでPNGには使わない。CLIの有無や場所は環境によって異なるため、固定のOSパスをスキルに埋め込まない。

CLIを利用できない場合や利用者がGUI操作を希望する場合は、作業XMLをエディターで開き、File → Export as → PNGから **Include a copy of my diagram** と図全体・全ページを含む設定を選び、`.drawio.png` として保存する。設定名や表示位置は版や言語で変わりうるので、保存したPNGの埋め込みデータを検査する。図データを含めない通常のPNG書き出しでは、図形としての再編集ができない。

## 構造検査と表示の確認を分ける

```sh
python3 scripts/validate_drawio.py output/domain-model.drawio.png
```

これはスキルのフォルダーで実行する例である。別の場所からはスクリプトを絶対パス等で指定する。正常なら画像サイズ、ページ数、ページ名を表示して終了コード0を返す。不正なら理由を標準エラーへ表示して終了コード1を返す。ファイルの書き換えやネットワーク通信はしない。

検査は、PNGのチャンクとCRC、画像データの展開・行サイズ・フィルター番号、図データの抽出、全ページのXML、セルID・親・接続先・ジオメトリを確認する。draw.ioの通常の `mxGraphModel` テキストチャンク（tEXt/zTXt/iTXt）と、非圧縮またはbase64＋raw DEFLATEのページを扱う。静止PNGを対象とし、インターレース画像やアニメーションPNGは対象外である。入力は32MiBまでとする。PNGの画像データ、図メタデータ、各圧縮ページの展開後のバイト数を合計し、ファイル全体で64MiBまでに制限する。重複した図メタデータは展開前に拒否する。上限を超える図は、画像の倍率を下げるか、意味を保って図を分割してから確認する。文字列やXML解析にもメモリを使うため、展開量の制限がプロセスのメモリ使用量そのものの上限を示すわけではない。

構造検査は画素と図データの意味の一致や文字の読みやすさを証明しない。各ページをCLIでPNGへ書き出し、画像として文字と線を確認する。利用者が希望する場合などの追加確認として、draw.ioのGUIで全ページを開き、コピー上で図形・接続線を編集して、PNG保存・再読み込み後に変更と全ページが残ることを確かめる。通常の作図完了にGUI操作を必須としない。プレビューだけを変更して古いXMLを埋め直す方法は採らない。

参考：[XMLソースの編集](https://www.drawio.com/docs/manual/advanced/diagram-source-edit/)、[PNG内の図データ](https://www.drawio.com/docs/manual/export/xml-in-png/)、[公式Desktop CLI](https://github.com/jgraph/drawio/wiki/Desktop-App)。
