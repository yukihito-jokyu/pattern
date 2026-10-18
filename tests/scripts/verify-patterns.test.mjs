import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {rm, readFile} from 'node:fs/promises';
import {cli, project, put} from '../helpers/temporary-project.mjs';

const entry = 'patterns/sample/basic/hello/verify.mjs';

test('ZIPを別の場所に展開して検証する', async t => {
  const root = await project(t);
  await put(root, entry, (await readFile(path.join(root, entry), 'utf8')) + `\nassert.ok(!process.cwd().startsWith(${JSON.stringify(root)}));\n`);
  const result = cli('verify-patterns.mjs', root, ['--all']);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.match(result.stdout, /成功/);
  assert.match(result.stdout, /Hello verification passed/);
});

test('収録漏れで展開後に動かなければ失敗する', async t => {
  const root = await project(t);
  await put(root, entry, "import './missing.mjs';");
  const result = cli('verify-patterns.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /失敗[\s\S]*missing.mjs/);
});

test('準備の失敗が後続へ進まず伝わる', async t => {
  const root = await project(t);
  await put(root, entry, "import {spawnSync} from 'node:child_process';\nconst setup = spawnSync(process.execPath, ['-e', 'process.exit(1)']);\nif (setup.status !== 0) process.exit(1);\nconsole.log('verification-should-not-run');");
  const result = cli('verify-patterns.mjs', root);
  assert.equal(result.status, 1);
  assert.doesNotMatch(result.stdout, /verification-should-not-run/);
});

test('入口欠落・未対応環境は未実施としてCIも失敗する', async t => {
  const root = await project(t);
  await rm(path.join(root, entry));
  let result = cli('verify-patterns.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /未実施.*\nverify.mjs/);
  await put(root, entry, "console.error('必要なランタイムがありません'); process.exit(2);");
  result = cli('verify-patterns.mjs', root);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /未実施/);
});

test('無限待機する処理を時間制限で止める', async t => {
  const root = await project(t);
  await put(root, entry, 'setInterval(() => {}, 1000);');
  const result = cli('verify-patterns.mjs', root, ['--timeout-ms', '100']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /時間切れ/);
});

test('不明なIDや不正な時間指定を成功にしない', async t => {
  const root = await project(t);
  for (const args of [['--id', 'sample/basic/missing'], ['--id', '../../escape'], ['--timeout-ms', 'NaN']]) {
    assert.equal(cli('verify-patterns.mjs', root, args).status, 1);
  }
});
