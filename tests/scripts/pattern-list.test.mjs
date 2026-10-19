import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {cp, readFile, rm} from 'node:fs/promises';
import {project, put, cli} from '../helpers/temporary-project.mjs';
import {patternList} from '../../scripts/lib/pattern-list.mjs';

const id = 'sample/basic/hello';
const file = `docs/${id}/index.md`;
async function change(root, from, to) {
  await put(root, file, (await readFile(path.join(root, file), 'utf8')).replace(from, to));
}

test('文書・カテゴリ・公開slugから一覧を作り、ZIPはIDから導出する', async t => {
  const root = await project(t);
  await put(root, 'docs/sample/_category_.json', JSON.stringify({label: 'サンプル'}));
  await change(root, 'slug: /sample/basic/hello', 'slug: /published/hello');
  const [entry] = await patternList(root);
  assert.equal(entry.title, 'Helloのパターン');
  assert.equal(entry.description, '管理基盤のテスト専用サンプル。');
  assert.deepEqual(entry.category, ['サンプル', 'basic']);
  assert.equal(entry.to, '/docs/published/hello');
  assert.equal(entry.downloadPath, '/downloads/patterns/sample/basic/hello.zip');
  assert.equal(entry.preview.src, '@site/docs/sample/basic/hello/images/example.png');
});

test('文書と実装の追加・削除が一覧へ反映され、同名も別カードになる', async t => {
  const root = await project(t);
  for (const kind of ['docs', 'patterns']) await cp(path.join(root, kind, 'sample/basic/hello'), path.join(root, kind, 'sample/other/hello'), {recursive: true});
  let entries = await patternList(root);
  assert.equal(entries.length, 2);
  assert.equal(new Set(entries.map(item => item.id)).size, 2);
  assert.equal(new Set(entries.map(item => item.downloadPath)).size, 2);
  for (const kind of ['docs', 'patterns']) await rm(path.join(root, kind, 'sample/basic/hello'), {recursive: true});
  entries = await patternList(root);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].downloadPath, '/downloads/patterns/sample/other/hello.zip');
});

test('一覧専用設定の省略時は文書情報を使い、draft・unlistedは掲載しない', async t => {
  const root = await project(t);
  const original = await readFile(path.join(root, file), 'utf8');
  await put(root, file, original.replace(/^pattern:\n(?:[ \t].*\n)*/m, ''));
  assert.deepEqual((await patternList(root))[0].features, []);
  for (const key of ['draft', 'unlisted']) {
    await put(root, file, original.replace('slug:', `${key}: true\nslug:`));
    assert.deepEqual(await patternList(root), []);
  }
});

test('不正な紹介設定や画像を文書確認で検出する', async t => {
  const root = await project(t);
  const original = await readFile(path.join(root, file), 'utf8');
  for (const config of [
    {position: 'first'},
    {features: [{label: '同名', value: 'A'}, {label: '同名', value: 'B'}]},
    {preview: {src: '../outside.png', alt: '画像', width: 1, height: 1, caption: '例'}},
    {preview: {src: './images/missing.png', alt: '画像', width: 1, height: 1, caption: '例'}},
  ]) {
    await put(root, file, original.replace(/^pattern:\n(?:[ \t].*\n)*/m, `pattern: ${JSON.stringify(config)}\n`));
    assert.equal(cli('check-docs.mjs', root).status, 1);
    await assert.rejects(patternList(root));
  }
});
