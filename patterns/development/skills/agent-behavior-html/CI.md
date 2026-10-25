# ZIP単体でのCI検証

この文書と`ci.json`、`scripts/verify-ci.sh`は、このパターン集のCIへ接続するための追加ファイルです。元の`claude-codex-cli`の60ファイルは変更せずに収録しています。元のREADMEにある利用・開発手順に加え、展開先での検証には以下を使えます。

## 環境と実行

macOSまたはLinuxで、Python 3.12、Node.js 22、bash、makeを用意します。Pythonの外部パッケージは不要です。ZIPを展開した`agent-behavior-html/`で実行してください。サイトの依存関係やリポジトリ外のファイルは使いません。

```bash
python3 --version
node --version
make --version
bash scripts/verify-ci.sh
```

共通CIは`ci.json`の`pythonVersion`に従ってPythonを用意し、`command`の配列をZIP展開先で実行します。Node.jsとmakeは共通runnerの環境を使います。

## 準備と検証の流れ

元の設定は移行前の絶対パスを含み、ZIPにはCodex用のシンボリックリンクが入っていません。検証スクリプトは一時コピーを作り、そのコピーだけで古い行動記録handlerを取り除いて、既存の`install.py --in-place --apply`により現在のパスへ再接続します。他のhookと設定は残し、`impl`と`review`のCodex入口も相対リンクで作ります。配布ファイル、プロジェクトの設定、ユーザー全体の設定、Codexのhook信頼は変更しません。

準備に成功すると、元の`make check`、`make demo`、`make probes`、最終`rules_check.py`を順に実行します。どの段階でも失敗したら後続を止め、非0で終了します。一時コピーは終了時に削除します。

期待結果は、品質・契約テスト19件・DOMスタブ・guard・規則の検査が成功し、合成デモを生成し、違反例21件と検査への組み込み3件を検出したうえで、最終の24規則にエラー・警告がないことです。検査や規則を緩めず、今回生成したprobe結果を最終検査に使います。

この検証は実製品のhook発火、Codexの信頼操作、実ブラウザーでの操作、独立作者の収束試験を行いません。それらは元READMEと設計資料の範囲に従い、別に確認してください。
