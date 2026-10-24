# 出典と採用範囲

確認日：2026-10-24。以下は一次資料。6原則、recipeの分類、遊び心の制限は本パターンの設計判断であり、出典に同じ分類が存在すると扱わない。

| 資料 | 採用する考え方・仕様 | 境界 |
|---|---|---|
| [Apple HIG Motion](https://developer.apple.com/design/human-interface-guidelines/motion) | 目的、短いフィードバック、操作期待、キャンセル | Webの固定時間・CSS値は規定しない |
| [Material 1 Motion](https://m1.material.io/motion/material-motion.html) | Responsive/Natural/Aware/Intentional、関係の伝達 | 旧版の原則整理 |
| [Material 3 Motion physics](https://m3.material.io/styles/motion/overview/how-it-works) | 2025年からばね方式へ移行、spatial/effectsを区別 | 既存Cobaltへ新方式を強制しない |
| [NN/g Executing UX Animations](https://www.nngroup.com/articles/animation-duration/) | 頻度、距離、時間、easing、過剰な動き | 100〜400msは多くの場合の目安。一般論は100〜500ms |
| [Microsoft旧ガイド](https://learn.microsoft.com/en-us/windows/win32/uxguide/vis-animations) | 開始の速さと操作の阻害を分ける | Windows 7向け。50msをWebの一律基準にしない |
| [Fluent 2 Motion](https://fluent2.microsoft.design/motion) | 機能・自然さ・一貫性・魅力と代替通知 | 本パターンの数値そのものの出典ではない |
| [W3C SC 2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html) | 非本質的な操作起因の動きを止められる | AAAの成功基準。対応だけでWCAG全体への適合を宣言しない |
| [W3C C39](https://www.w3.org/WAI/WCAG22/Techniques/css/C39) | prefers-reduced-motionの利用 | 実現技法の一例 |
| [CSS Transitions](https://www.w3.org/TR/css-transitions-1/#starting) | 現在値からの変更、取消、反転の短縮 | 速度連続の保証はない |
| [CSS Grid track sizing](https://www.w3.org/TR/css-grid-1/#track-sizing) | 同じ構造のトラックリストを補間 | 参照例は0fr/1frとmin-height:0を組み合わせる |
| [HTML inert](https://html.spec.whatwg.org/multipage/interaction.html#inert) | 閉じる内容をフォーカス・操作対象から外す | 視覚的な退出と操作状態を分ける |
| [WAI-ARIA Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) | 開閉ボタンとaria-expanded、Enter/Space | モーダルのフォーカストラップとは別 |
| [Web Animations cancel](https://www.w3.org/TR/web-animations-1/#canceling-an-animation) | cancelによるfinishedのreject | 消費するPromiseで中断を処理 |
| [CSSOM](https://drafts.csswg.org/cssom/#dom-window-getcomputedstyle) | computed styleはlive | cancel前に必要な値を文字列として保存 |
| [CSSOM View MediaQueryList](https://www.w3.org/TR/cssom-view-1/#the-mediaquerylist-interface) | matchMediaのchange購読 | 初期値だけで途中変更を無視しない |
| [HTML rendering](https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering) | rAFはpaintより前 | rAF間隔から画面提示FPSを断定しない |
| [React 19 refs](https://react.dev/blog/2024/12/05/react-19#cleanup-functions-for-refs) | callback refのcleanup | StrictModeの追加setup/cleanupに対称な処理が必要 |
| [useSyncExternalStore](https://react.dev/reference/react/useSyncExternalStore) | 外部設定の購読とSSR snapshot | hydration初回とserverの値を一致させる |
| [useLayoutEffect](https://react.dev/reference/react/useLayoutEffect) | paint前の測定 | 描画をブロックする。全演出の必須Hookにはしない |
| [Tailwind duration](https://tailwindcss.com/docs/transition-duration) / [easing](https://tailwindcss.com/docs/transition-timing-function) | duration-(--token)、ease-(--token) | Tokenが存在するだけで任意のutility名が生成されるとは扱わない |
| [starting-style](https://www.w3.org/TR/css-transitions-2/#defining-before-change-style) | 初回表示のbefore-change style | 最終状態を通常CSSに置き、未対応なら演出を省く |

取り込み先の実装・固定版・採用済みの値は[design-system.md](design-system.md)とassets/profiles.jsonを参照する。指定資料の原則を解説することと、各社の最新製品で同じ動作を保証することは別である。
