import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {cli, project, put} from '../helpers/temporary-project.mjs';

const doc = 'docs/sample/basic/hello/index.md';
async function change(root, from, to) {
  await put(root, doc, (await readFile(path.join(root, doc), 'utf8')).replace(from, to));
}

test('ZIP生成前でも正しい文書を確認でき、任意の注意点の節は不要', async t => {
  const result = cli('check-docs.mjs', await project(t));
  assert.equal(result.status, 0, result.stderr);
});

for (const [name, from, to, expected] of [
  ['画像欠落', 'images/example.png', 'images/missing.png', /画像がありません/],
  ['別のZIP', 'sample/basic/hello.zip', 'sample/basic/other.zip', /ZIPリンク/],
  ['リンク欠落', '[実装をダウンロード](/downloads/patterns/sample/basic/hello.zip)', '', /ダウンロードリンク/],
  ['画像配置', './images/example.png', '../example.png', /images\/配下/],
  ['代替テキスト', '![処理の例]', '![]', /代替テキスト/],
  ['メタデータ', 'description: 管理基盤のテスト専用サンプル。', '', /description/],
  ['未記入欄', '入力された名前', '{{ここに記入}}', /記入欄/],
  ['メタデータの未記入欄', 'title: Helloのパターン', 'title: "{{パターン名}}"', /title.*記入欄/],
]) test(name, async t => {
  const root = await project(t);
  await change(root, from, to);
  const result = cli('check-docs.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stderr, expected);
});

test('拡張子だけPNGのファイルを拒否する', async t => {
  const root = await project(t);
  await put(root, 'docs/sample/basic/hello/images/example.png', Buffer.from([255,216,255,224]));
  assert.match(cli('check-docs.mjs', root).stderr, /PNG形式/);
});

test('コード例のリンクを実参照と誤認しない', async t => {
  const root = await project(t);
  await change(root, '# Helloのパターン', '# Helloのパターン\n\n```md\n![例](./missing.png)\n[ZIP](/wrong.zip)\n{{ここに記入}}\n```');
  assert.equal(cli('check-docs.mjs', root).status, 0);
});

test('参照形式の画像とリンクも検査する', async t => {
  const root = await project(t);
  await change(root, '![処理の例](./images/example.png)', '![処理の例][image]\n\n[image]: ./images/missing.png');
  assert.match(cli('check-docs.mjs', root).stderr, /画像がありません/);
});
