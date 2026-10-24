# 取り込み先との接続

対象はyukihito-jokyu/design-systemのdevelop、調査時点8acdfd958cd0de9ce4ea0de3805720f6ba81b4d9。現在の実装は作業開始時に再確認する。同じアプリでnew-yorkとcobaltを併用しない。原本・Registry・Story・利用スキルが既にあるので、別のデザインシステムを生成しない。

| 項目 | cobalt | new-york |
|---|---|---|
| 正本 | registry/cobalt/styles/registry.json | registry/new-york/styles/registry.json |
| 項目 | cobalt-design-system-styles | design-system-styles |
| 時間 | press90 / selection180 / feedback280 / entry300 / menu220 / expand260 / celebrate360ms | fast120 / normal180 / feedback240ms |
| 曲線 | --cobalt-ease-out | --ds-ease-standard |
| 設定 | MotionProvider、useDesignMotion、motion=inherit/on/off | cobaltのmotion prop/APIは存在しない。既存CSSのOS reduceを維持 |
| Portal | 既存ThemePortal/各OverlayのProviderを維持 | 既存DesignThemeProviderの継承を維持 |

数値は快適さの証明ではなく、調査時点の実装値。assets/profiles.jsonはこの値への対応表であり、実行中に正本を置き換えない。生成motion.cssは同じ名前を参照するだけで、アニメーションやReact部品をインストールしない。

Cobaltでは最も近い明示指定を使い、子onは親offを上書きできる。OS reduceは全指定に勝つ。Dialog/Sheet/AlertDialog/Select/Popover/TooltipはRootのmotionを使う。ContentやTriggerに同じPropがあるとは推測しない。DOM属性を置くだけではReact Contextは子へ渡らない。

停止はCSSとWAAPIの両方へ反映し、値・選択・フォーカス・処理結果は維持する。ON復帰だけでは登場・成功を再演しない。Spinner/不定Progressの再開は既存の処理状態に従う。停止中もラベルとaria-busy/状態通知を残す。

調査時点のCobaltは閉鎖時に即座に見た目を消す。この既存挙動は、今回の「開閉の動きを残して次の操作を待たせない」という目標を満たさない。適用時は閉鎖の論理状態・フォーカス・入力の受付と、退出する表示の存在管理を分ける。既存APIで表現できない場合は原本の存在管理を修正し、Story・Registry・利用スキルへ反映する。公開APIや静止時の寸法、既存Tokenは維持する。参照デモはモーダルではないため、Overlayのフォーカストラップやスクロール制御まで再現した例として扱わない。

Tabsは表示中の位置から次へ、リスト・ステップは前の再生を止めて最新操作へ進む。全てを「速度まで連続するばね」と呼ばない。cobaltの600px以下では距離が変わるため、600/601px前後も確認する。

本体repoは設計履歴・検証アプリの保存を制限している。アプリ/静的出力/画像は外部一時ディレクトリへ置き、既存運用手順で配布物を再生成する。public/rはそのrepoではGit管理されるため、本pattern repoの生成物規則を誤って適用しない。

[既存Motion仕様](https://github.com/yukihito-jokyu/design-system/blob/8acdfd958cd0de9ce4ea0de3805720f6ba81b4d9/skills/cobalt-design-system/references/motion.md)、[検証](https://github.com/yukihito-jokyu/design-system/blob/8acdfd958cd0de9ce4ea0de3805720f6ba81b4d9/skills/cobalt-design-system/references/validation.md)、[作業方針](https://github.com/yukihito-jokyu/design-system/blob/8acdfd958cd0de9ce4ea0de3805720f6ba81b4d9/AGENTS.md)を根拠にする。
