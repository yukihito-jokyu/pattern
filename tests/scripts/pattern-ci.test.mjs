import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {rm} from 'node:fs/promises';
import {project, put, cli} from '../helpers/temporary-project.mjs';
import {patternMatrix} from '../../scripts/pattern-ci.mjs';

const id = 'sample/basic/hello';
const configFile = `patterns/${id}/ci.json`;
const config = {command: ['node', '--test', 'hello.test.mjs']};

test('パターン追加だけで実行対象が増え、環境設定も読み込まれる', async t => {
  const root = await project(t);
  await put(root, configFile, JSON.stringify(config));
  const second = 'sample/basic/another';
  await put(root, `docs/${second}/index.md`, '# Another');
  await put(root, `patterns/${second}/README.md`, '# Another');
  await put(root, `patterns/${second}/go.mod`, 'module example.com/test\n\ngo 1.27.1\n');
  await put(root, `patterns/${second}/ci.json`, JSON.stringify({...config, goVersionFile: 'go.mod', pythonVersion: '3.12'}));
  assert.deepEqual(await patternMatrix(root), {include: [
    {id: second, goVersionFile: `patterns/${second}/go.mod`, pythonVersion: '3.12'},
    {id, goVersionFile: '', pythonVersion: ''},
  ]});
});

test('欠落・不正な設定や外部のファイルを黙ってスキップしない', async t => {
  const root = await project(t);
  await assert.rejects(patternMatrix(root), /ci.json/);
  for (const value of [{}, {command: 'node test'}, {...config, unexpected: true}, {...config, goVersionFile: '../go.mod'}, {...config, goVersionFile: 'missing.mod'}, {...config, pythonVersion: 'latest'}]) {
    await put(root, configFile, JSON.stringify(value));
    await assert.rejects(patternMatrix(root), /ci.json/);
  }
  await put(root, configFile, JSON.stringify(config));
  await rm(path.join(root, 'docs', id), {recursive: true});
  await assert.rejects(patternMatrix(root), /対応する文書/);
});

test('ci.jsonのコマンドをZIPの展開先で実行し、引数をシェル展開しない', async t => {
  const root = await project(t);
  const value = 'a b; $(not-a-command)';
  await put(root, configFile, JSON.stringify({command: ['node', '-e', 'if(process.cwd().startsWith(process.argv[1])) process.exit(1); console.log(process.argv[2])', root, value]}));
  const result = cli('verify-patterns.mjs', root, ['--id', id, '--ci']);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.ok(result.stdout.includes(value));
  assert.equal(cli('verify-patterns.mjs', root, ['--id', id, '--ci', '--', 'node']).status, 1);
});

test('CIコマンドの失敗を成功にしない', async t => {
  const root = await project(t);
  await put(root, configFile, JSON.stringify({command: ['node', '-e', 'process.exit(7)']}));
  const result = cli('verify-patterns.mjs', root, ['--id', id, '--ci']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /失敗\n終了コード7/);
});

test('変更した実装だけを選び、文書やサイトだけの変更ではZIP検証を省く', async t => {
  const root = await project(t);
  await put(root, configFile, JSON.stringify(config));
  const second = 'sample/basic/another';
  await put(root, `docs/${second}/index.md`, '# Another');
  await put(root, `patterns/${second}/README.md`, '# Another');
  await put(root, `patterns/${second}/ci.json`, JSON.stringify(config));
  assert.deepEqual((await patternMatrix(root, {files: [`patterns/${id}/hello.mjs`]})).include.map(item => item.id), [id]);
  for (const files of [[], [`docs/${id}/index.md`], ['src/components/PatternHome.tsx'], ['scripts/lib/pattern-list.mjs'], [`patterns/${id}-other/file`]]) {
    assert.deepEqual(await patternMatrix(root, {files}), {include: []});
  }
  assert.equal((await patternMatrix(root, {files: ['scripts/build-downloads.mjs']})).include.length, 2);
  assert.equal((await patternMatrix(root, {files: ['.github/workflows/ci.yml']})).include.length, 2);
  assert.equal((await patternMatrix(root, {files: ['package-lock.json']})).include.length, 2);
});

test('対象外でも不正なCI設定を黙って通さない', async t => {
  const root = await project(t);
  await assert.rejects(patternMatrix(root, {files: []}), /ci.json/);
});
