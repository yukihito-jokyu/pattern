import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {rm, rename, mkdir} from 'node:fs/promises';
import {project, cli, put} from '../helpers/temporary-project.mjs';

test('正しい対応と運用文書・画像の例外は通る', async t => {
  const result = cli('check-dir.mjs', await project(t));
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /1パターン/);
});

for (const [file, expected] of [
  ['patterns/sample/basic/hello', /patterns\/sample\/basic\/hello.*実装/],
  ['docs/sample/basic/hello/index.md', /docs\/sample\/basic\/hello\/index.md.*文書/],
  ['patterns/sample/basic/hello/README.md', /README.md.*手順/],
  ['patterns/sample/basic/hello/hello.mjs', /実ファイル/],
]) test(`不足を検出する: ${file}`, async t => {
  const root = await project(t);
  await rm(path.join(root, file), {recursive: true});
  if (file.endsWith('/hello.mjs')) await rm(path.join(root, 'patterns/sample/basic/hello/hello.test.mjs'));
  const result = cli('check-dir.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stderr, expected);
});

test('階層不足の文書を無視しない', async t => {
  const root = await project(t);
  await rename(path.join(root, 'docs/sample/basic/hello'), path.join(root, 'docs/sample/hello'));
  const result = cli('check-dir.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /docs\/sample\/hello\/index.md.*配置/);
});

test('階層が過剰な場合も入口欠落を検出する', async t => {
  const root = await project(t);
  await mkdir(path.join(root, 'docs/sample/basic/hello/extra'));
  await rename(path.join(root, 'docs/sample/basic/hello/index.md'), path.join(root, 'docs/sample/basic/hello/extra/index.md'));
  assert.match(cli('check-dir.mjs', root).stderr, /index.md.*文書/);
});

test('空の初期構成は0件と表示し、実績を偽らない', async t => {
  const root = await project(t);
  await rm(path.join(root, 'docs/sample'), {recursive: true});
  await rm(path.join(root, 'patterns/sample'), {recursive: true});
  await put(root, 'patterns/.gitkeep', '');
  const result = cli('check-dir.mjs', root);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /0パターン/);
});
