import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {cp, rm} from 'node:fs/promises';
import {project, put, cli} from '../helpers/temporary-project.mjs';
import {changedFiles, patternMatrix} from '../../scripts/pattern-ci.mjs';

function git(root, ...args) {
  return execFileSync('git', ['-c', 'user.name=CI Test', '-c', 'user.email=ci@example.test', '-c', 'commit.gpgSign=false', '-c', 'core.hooksPath=/dev/null', '-C', root, ...args], {encoding: 'utf8', env: {...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1'}}).trim();
}
async function repository(t) {
  const root = await project(t);
  await put(root, 'patterns/sample/basic/hello/ci.json', JSON.stringify({command: ['node', '--test', 'hello.test.mjs']}));
  git(root, 'init', '--initial-branch=main');
  git(root, 'add', '.');
  git(root, 'commit', '-m', 'initial');
  return root;
}
function commit(root) {
  git(root, 'add', '-A');
  git(root, 'commit', '-m', 'change');
  return git(root, 'rev-parse', 'HEAD');
}

test('PRでは共通祖先からの全差分を使い、比較先ブランチだけの変更は含めない', async t => {
  const root = await repository(t);
  git(root, 'checkout', '-b', 'feature');
  await put(root, 'patterns/sample/basic/hello/hello.mjs', 'changed');
  commit(root);
  await put(root, 'docs/project/guide.md', '# Later PR commit');
  const head = commit(root);
  git(root, 'checkout', 'main');
  await put(root, 'base-only.txt', 'base branch only');
  const base = commit(root);
  git(root, 'checkout', 'feature');
  const files = await changedFiles(root, {base, head, mergeBase: true});
  assert.deepEqual(files, ['docs/project/guide.md', 'patterns/sample/basic/hello/hello.mjs']);
  const matrix = await patternMatrix(root, {files});
  assert.deepEqual(matrix.include.map(item => item.id), ['sample/basic/hello']);
  const result = cli('pattern-ci.mjs', root, ['--base', base, '--head', head, '--merge-base']);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), matrix);
});

test('pushは前後の差分を使い、改名の両側と改行を含むファイル名も保持する', async t => {
  const root = await repository(t);
  const base = git(root, 'rev-parse', 'HEAD');
  await put(root, 'patterns/sample/basic/hello/odd\nfile.txt', 'example');
  for (const kind of ['docs', 'patterns']) {
    await cp(path.join(root, kind, 'sample/basic/hello'), path.join(root, kind, 'sample/basic/renamed'), {recursive: true});
    await rm(path.join(root, kind, 'sample/basic/hello'), {recursive: true});
  }
  const head = commit(root);
  const files = await changedFiles(root, {base, head});
  assert.ok(files.includes('patterns/sample/basic/hello/hello.mjs'));
  assert.ok(files.includes('patterns/sample/basic/renamed/hello.mjs'));
  assert.ok(files.includes('patterns/sample/basic/renamed/odd\nfile.txt'));
  assert.deepEqual((await patternMatrix(root, {files})).include.map(item => item.id), ['sample/basic/renamed']);
});

test('文書だけ・削除だけの変更では実行対象を作らず、比較失敗はエラーにする', async t => {
  const root = await repository(t);
  const base = git(root, 'rev-parse', 'HEAD');
  const unchanged = cli('pattern-ci.mjs', root, ['--base', base, '--head', base]);
  assert.equal(unchanged.status, 0, unchanged.stderr);
  assert.deepEqual(JSON.parse(unchanged.stdout), {include: []});
  await put(root, 'docs/project/guide.md', '# Changed');
  const docsHead = commit(root);
  assert.deepEqual(await patternMatrix(root, {files: await changedFiles(root, {base, head: docsHead})}), {include: []});
  for (const kind of ['docs', 'patterns']) await rm(path.join(root, kind, 'sample'), {recursive: true});
  const head = commit(root);
  assert.deepEqual(await patternMatrix(root, {files: await changedFiles(root, {base, head})}), {include: []});
  await assert.rejects(changedFiles(root, {base: 'missing-ref', head}), /取得に失敗/);
  assert.equal(cli('pattern-ci.mjs', root, ['--base', 'missing-ref']).status, 1);
  assert.equal(cli('pattern-ci.mjs', root, ['--merge-base']).status, 1);
});
