import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {rm, readFile} from 'node:fs/promises';
import {cli, project, put} from '../helpers/temporary-project.mjs';

const entry = 'patterns/sample/basic/hello/hello.test.mjs';
const target = ['--id', 'sample/basic/hello'];
const verify = ['--', process.execPath, '--test', 'hello.test.mjs'];

test('ZIPを別の場所に展開して指定コマンドで検証する', async t => {
  const root = await project(t);
  await put(root, entry, (await readFile(path.join(root, entry), 'utf8')) + `\nassert.ok(!process.cwd().startsWith(${JSON.stringify(root)}));\n`);
  const result = cli('verify-patterns.mjs', root, [...target, ...verify]);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.match(result.stdout, /成功/);
  assert.match(result.stdout, /pass 1/);
});

test('ZIPの収録漏れで展開後に動かなければ失敗する', async t => {
  const root = await project(t);
  await rm(path.join(root, 'patterns/sample/basic/hello/hello.mjs'));
  const result = cli('verify-patterns.mjs', root, [...target, ...verify]);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /失敗[\s\S]*hello.mjs/);
});

test('終了コード2もコマンドの失敗として扱う', async t => {
  const result = cli('verify-patterns.mjs', await project(t), [...target, '--', process.execPath, '-e', 'process.exit(2)']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /失敗\n終了コード2/);
});

test('実行コマンドがなければ未実施とし成功にしない', async t => {
  const result = cli('verify-patterns.mjs', await project(t), [...target, '--', 'pattern-test-missing-executable']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /未実施/);
});

test('無限待機するコマンドを時間制限で止める', async t => {
  const result = cli('verify-patterns.mjs', await project(t), [...target, '--timeout-ms', '100', '--', process.execPath, '-e', 'setInterval(() => {}, 1000)']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /時間切れ/);
});

test('対象・コマンドの欠落や不正な指定を成功にしない', async t => {
  const root = await project(t);
  for (const args of [[], target, verify, ['--id', 'sample/basic/missing', ...verify], ['--id', '../../escape', ...verify], [...target, '--timeout-ms', 'NaN', ...verify], ['--all', ...verify]]) {
    assert.equal(cli('verify-patterns.mjs', root, args).status, 1);
  }
});

test('空白やシェル記号を含む引数をそのまま渡す', async t => {
  const value = 'a b; $(not-a-command)';
  const result = cli('verify-patterns.mjs', await project(t), [...target, '--', process.execPath, '-e', 'console.log(process.argv[1])', value]);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.ok(result.stdout.includes(value));
});
