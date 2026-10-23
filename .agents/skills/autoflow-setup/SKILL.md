---
name: autoflow-setup
description: このプロジェクトのCodex用autoflowプロファイルを準備・更新し、検証条件と人が読む範囲の承認を記録する。初回とプロファイル変更時に使う。
---

# autoflow-setup

プロジェクト直下の`.autoflow/`にある実行基盤を設定する。プロファイルの意味は`.autoflow/references/profile-schema.md`を読み、運用は`docs/project/autoflow.md`に従う。

1. ルートで`python3 .autoflow/autoflow.py setup-new`を実行する。既存のプロファイルがあれば保持して読み、明示的な再作成依頼なしで--forceを使わない。
2. `AGENTS.md`、package.json、共通CI、文書の検証規約と照合する。verify.commandsには配置・文書・テスト・型検査・ビルド・E2Eの6検査を維持する。自動修正を入れず、失敗を理由に検査を外さない。
3. risk.always_humanにスキル・実行基盤・運用文書・共通スクリプト・掲載サイト・CIを含める。レビュー指示はpattern-maintenanceと運用文書を指定し、存在を確かめる。paths.testsには個別パターン内のテストも含める。
4. `python3 .autoflow/autoflow.py setup-check`を実行し、エラーや参照先の欠落を直す。検査コマンドと上限、常に人が読むパス、レビュー指示、試行上限、変更理由を人へ提示する。
5. setup-checkが承認済みと示した場合は、そのままstartへ進む。別タスク・別ブランチ・別worktreeでも同じ設定の承認を引き継ぎ、再承認を求めない。現在の設定に対応する承認がない場合だけ、H0として具体的なプロファイルを提示して確認する。承認が得られたときだけ、`python3 .autoflow/autoflow.py setup-approve --answer <人の回答原文>`を実行する。回答がない・空なら未承認として止まる。
6. 承認はGitの共通管理領域へCLIが保存する。従来の承認ファイルは設定が一致するときに原文と日時を保って自動移行する。利用者に承認記録のコミット・削除・持ち運びを求めない。未コミットの編集や未追跡ファイルは保持し、事前のコミットや退避も求めない。開始後の差分と既存変更の切り分けはAIとCLIが行う。

H0は検証条件への承認であり、Codexのサンドボックスや実行権限を変更する許可ではない。元キットの`--allow`は使わず、`.claude/settings.local.json`やCodexの権限設定を生成しない。現在の環境でコマンドの許可が必要になった場合は、その環境の承認手順に従う。
