---
name: autoflow-learn
description: このプロジェクトのautoflow実行記録から、差し戻し・インシデントの原因と運用改善案を作る。人が選んだ改善だけを反映する。
---

# autoflow-learn

`python3 .autoflow/autoflow.py metrics`と`learn`で記録を読み、繰り返す失敗、レビューの見逃し、人の修正依頼を確認する。後から見つかった問題の記録依頼なら、`incident --run <ID> --text <受け取った問題>`を実行してから分析する。

各案に実行ID・指摘や回答・変更先・具体的な修正文を添え、人に選んでもらう。作業ルールならAGENTS.mdかpattern-maintenance、説明品質ならdocs/project/review.md、実行条件ならprofile.json、機械的に検出できる失敗なら対象の検査を候補にする。検証に通らないという理由で検査を緩めない。

回答がなければ案の提示で止まり、選択されたものだけを変更する。プロファイルを変えたら`$autoflow-setup`でH0をやり直す。過去のrunsの記録を編集・削除しない。コミット・Issue投稿・公開は別途の明示的な依頼がある場合だけ行う。
