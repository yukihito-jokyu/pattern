import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {cp, readFile, rm, symlink, rename, chmod, readdir} from 'node:fs/promises';
import {unzipSync} from 'fflate';
import {cli, project, put} from '../helpers/temporary-project.mjs';

const zip = 'static/downloads/patterns/sample/basic/hello.zip';

test('実データ・隠し設定を収録し、依存関係と生成物を除外する', async t => {
  const root = await project(t);
  await put(root, 'patterns/sample/basic/hello/.gitignore', 'build/\n');
  await put(root, 'patterns/sample/basic/hello/node_modules/unwanted.js', 'excluded');
  await put(root, 'patterns/sample/basic/hello/build/unwanted.js', 'excluded');
  await put(root, 'patterns/sample/basic/hello/test-results/trace.zip', 'excluded');
  await put(root, 'patterns/sample/basic/hello/playwright-report/index.html', 'excluded');
  assert.equal(cli('build-downloads.mjs', root).status, 0);
  const files = unzipSync(await readFile(path.join(root, zip)));
  assert.deepEqual(Object.keys(files).sort(), ['hello/.gitignore', 'hello/README.md', 'hello/hello.mjs', 'hello/hello.test.mjs']);
  assert.equal(Buffer.from(files['hello/hello.mjs']).toString(), await readFile(path.join(root, 'patterns/sample/basic/hello/hello.mjs'), 'utf8'));
});

test('同名別分類を分け、削除・改名後に古いZIPを残さない', async t => {
  const root = await project(t);
  for (const kind of ['docs', 'patterns']) await cp(path.join(root, kind, 'sample/basic'), path.join(root, kind, 'sample/other'), {recursive: true});
  await put(root, 'static/keep.txt', 'keep');
  assert.equal(cli('build-downloads.mjs', root).status, 0);
  assert.ok((await readFile(path.join(root, 'static/downloads/patterns/sample/other/hello.zip'))).length);
  for (const kind of ['docs', 'patterns']) {
    await rm(path.join(root, kind, 'sample/other'), {recursive: true});
    await rename(path.join(root, kind, 'sample/basic/hello'), path.join(root, kind, 'sample/basic/renamed'));
  }
  assert.equal(cli('build-downloads.mjs', root).status, 0);
  await assert.rejects(readFile(path.join(root, zip)), {code: 'ENOENT'});
  await assert.rejects(readFile(path.join(root, 'static/downloads/patterns/sample/other/hello.zip')), {code: 'ENOENT'});
  assert.ok((await readFile(path.join(root, 'static/downloads/patterns/sample/basic/renamed.zip'))).length);
  assert.equal(await readFile(path.join(root, 'static/keep.txt'), 'utf8'), 'keep');
});

test('不正な収録対象では既存配布物を置き換えない', async t => {
  const root = await project(t);
  assert.equal(cli('build-downloads.mjs', root).status, 0);
  const original = await readFile(path.join(root, zip));
  await symlink(path.join(root, 'patterns/sample/basic/hello/hello.mjs'), path.join(root, 'patterns/sample/basic/hello/link.mjs'));
  const result = cli('build-downloads.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /シンボリックリンク/);
  assert.deepEqual(await readFile(path.join(root, zip)), original);
});

test('2件目の読込失敗で1件目だけを公開せず、一時生成物も片付ける', {skip: process.getuid?.() === 0}, async t => {
  const root = await project(t);
  for (const kind of ['docs', 'patterns']) await cp(path.join(root, kind, 'sample/basic'), path.join(root, kind, 'sample/second'), {recursive: true});
  assert.equal(cli('build-downloads.mjs', root).status, 0);
  const original = await readFile(path.join(root, zip));
  const secondZip = path.join(root, 'static/downloads/patterns/sample/second/hello.zip');
  const originalSecond = await readFile(secondZip);
  await put(root, 'patterns/sample/basic/hello/hello.mjs', 'changed but must not be published');
  const unreadable = path.join(root, 'patterns/sample/second/hello/hello.mjs');
  await chmod(unreadable, 0);
  const result = cli('build-downloads.mjs', root);
  await chmod(unreadable, 0o644);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /EACCES/);
  assert.deepEqual(await readFile(path.join(root, zip)), original);
  assert.deepEqual(await readFile(secondZip), originalSecond);
  assert.deepEqual(await readdir(path.join(root, 'static/downloads')), ['patterns']);
});
