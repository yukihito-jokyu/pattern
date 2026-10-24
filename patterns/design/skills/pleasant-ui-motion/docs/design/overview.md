# pleasant-ui-motion の設計

既存のデザインシステムに、意味と操作を保つUIモーションを一貫して取り入れるための基盤。指定された6原則を「5つの基本品質＋遊び心」として扱う。アクセシビリティは横断条件。心理学的な単一法則や快適さの採点尺度は主張しない。

主な対象はReact/Tailwindのyukihito-jokyu/design-system。既存new-york/cobaltのToken・API・配布の構成を尊重する。今回このpattern repoへ追加するのはスキル、適用仕様、参照実装、検査と文書である。

[調査](research.md) → [構造](architecture.md) → [ルール](rules.md) → [強制対応表](enforcement-matrix.md) → [ADR](adr/0002-existing-motion-and-contracts.md) → [収束結果](convergence-report.md)の順に読める。使用の入口はREADME。

## 既定値で決めたこと

名称と配置は承認済み計画による。仕様形式はJSON、検査はNode標準＋既存foundationのPython、ブラウザーはPlaywright/Chromium。新規runtime依存は足さない。一般的なhover・開閉へ新たなspringを強制しない。低頻度の確定済み成功以外に遊び心を加えない初期方針は本基盤の判断で、各社の共通必須規格ではない。

## 評価の限界

収束テストは本キットでの適用仕様の作成・変更・横断設計を対象とする。任意のReactアプリの実装一致や利用者の快適さまで保証しない。初版の即時閉鎖はユーザー確認で目標と異なると分かり、開閉の往復補間と、演出中に次の操作を受け付ける方式へ修正した（ADR 0003）。参照例は実処理と演出を分離して示し、対象APIの型照合を別コマンドで行う。
