import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import os from 'node:os';
import {mkdtemp, mkdir, readFile, writeFile, rm, access, cp} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {repository} from '../helpers/temporary-project.mjs';

const template = JSON.parse(await readFile(path.join(repository, '.autoflow/profile.json'), 'utf8'));

async function put(root, file, value) {
  const target = path.join(root, file);
  await mkdir(path.dirname(target), {recursive: true});
  await writeFile(target, typeof value === 'string' ? value : JSON.stringify(value));
}

function git(root, ...args) {
  const result = spawnSync('git', args, {cwd: root, encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function cli(root, ...args) {
  return spawnSync('python3', [path.join(root, '.autoflow/autoflow.py'), ...args], {cwd: root, encoding: 'utf8', timeout: 15000});
}

function python(root, script, ...args) {
  const program = `import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path('.autoflow').resolve()))\nfrom autoflow_kit import proc\n${script}`;
  return spawnSync('python3', ['-B', '-c', program, ...args], {cwd: root, encoding: 'utf8', timeout: 15000});
}

function snapshot(root) {
  const result = python(root, 'print(proc.git_snapshot(Path.cwd()))');
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function commitDelta(root, base, tree, head) {
  return python(root, "print(proc.git_commit_delta(Path.cwd(), *sys.argv[1:], '今回の差分'))", base, tree, head);
}

function ok(root, ...args) {
  const result = cli(root, ...args);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  return result.stdout;
}

async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'pattern-autoflow-'));
  t.after(() => rm(root, {recursive: true, force: true}));
  await cp(path.join(repository, '.autoflow'), path.join(root, '.autoflow'), {
    recursive: true,
    filter: source => !['runs', '__pycache__', 'profile-approval.json'].includes(path.basename(source)),
  });
  await assert.rejects(access(path.join(root, 'patterns')));
  git(root, 'init', '-q', '-b', 'main');
  git(root, 'config', 'user.name', 'autoflow test');
  git(root, 'config', 'user.email', 'autoflow@example.invalid');
  git(root, 'config', 'commit.gpgsign', 'false');
  await put(root, '.gitignore', '.autoflow/runs/\n');
  await put(root, 'AGENTS.md', '開始時点のレビュー基準\n');
  const settings = structuredClone(template);
  settings.verify.commands = [{id: 'baseline', run: 'node -e "process.exit(0)"', timeout_sec: 10}];
  settings.review.guide_files = ['AGENTS.md'];
  await put(root, '.autoflow/profile.json', settings);
  await put(root, '.autoflow/runs/intake.md', '文書へ具体例を追加する。');
  return {root, settings};
}

function commitAll(root) {
  git(root, 'add', '-A');
  git(root, 'commit', '-qm', 'fixture');
}

function start(root) {
  const output = ok(root, 'start', '--source', 'text', '--title', '文書更新', '--body-file', path.join(root, '.autoflow/runs/intake.md'));
  const id = output.match(/^実行: (.+)$/m)?.[1];
  assert.ok(id, output);
  return id;
}

test('Codexの入口はClaude用の権限変更を拒否し、H0未承認・変更後の開始も拒否する', async t => {
  const {root, settings} = await fixture(t);
  assert.equal(cli(root, 'setup-approve', '--answer', 'fixture', '--allow').status, 2);
  await assert.rejects(access(path.join(root, '.claude')));
  assert.equal(cli(root, 'start', '--source', 'text', '--title', 'fixture', '--body-file', path.join(root, '.autoflow/runs/intake.md')).status, 1);
  assert.equal(cli(root, 'setup-approve', '--answer', '').status, 1);
  ok(root, 'setup-approve', '--answer', 'テスト用の承認');
  const approval = JSON.parse(await readFile(path.join(root, '.autoflow/profile-approval.json')));
  assert.equal(approval.answer, 'テスト用の承認');
  settings.limits.fix_attempts += 1;
  await put(root, '.autoflow/profile.json', settings);
  commitAll(root);
  assert.equal(cli(root, 'start', '--source', 'text', '--title', 'fixture', '--body-file', path.join(root, '.autoflow/runs/intake.md')).status, 1);
  assert.equal(git(root, 'branch', '--show-current'), 'main');
});

test('実行はCodex用のレビュー指示を写し、検証前の計画とH1承認前の実装を拒否する', async t => {
  const {root} = await fixture(t);
  ok(root, 'setup-approve', '--answer', 'テスト用の承認');
  commitAll(root);
  const id = start(root);
  const run = path.join('.autoflow/runs', id);
  assert.match(await readFile(path.join(root, run, 'guide.md'), 'utf8'), /開始時点のレビュー基準/);
  assert.equal(cli(root, 'plan-new', '--run', id).status, 1);
  ok(root, 'verify', '--run', id);
  ok(root, 'plan-new', '--run', id);
  await put(root, `${run}/plan/1/plan.json`, {
    kind: 'feature', goal: '具体例を追加する', non_goals: [], scope: ['docs/note.md'],
    criteria: [{id: 'C1', text: '具体例を人が読める', check: 'human', run: ''}],
    repro: '', root_cause: '', dependencies_to_add: [],
    open_questions: [{question: '対象の版をどうするか', default: '現在の版', impact: 'high'}],
    revert: '変更コミットを戻す', commit_subject: '具体例を追加する',
  });
  ok(root, 'plan-check', '--run', id);
  assert.equal(cli(root, 'build-new', '--run', id).status, 1);
  ok(root, 'decide', '--run', id, '--gate', 'H1', '--choice', 'proceed', '--answer', 'テスト用: 現在の版で進める');
  ok(root, 'build-new', '--run', id);
  assert.match(ok(root, 'status', '--run', id), /^job autoflow-builder /m);
});

for (const dirty of [false, true]) test(`補助CLIが開始前の変更を保持して検査・レビュー・H3・コミットへ進む（既存変更: ${dirty}）`, async t => {
  const {root} = await fixture(t);
  await put(root, 'existing.txt', '元の内容\n');
  await put(root, 'deleted.txt', '削除予定\n');
  commitAll(root);
  ok(root, 'setup-approve', '--answer', 'テスト用の承認');
  if (!dirty) commitAll(root);
  if (dirty) {
    await put(root, 'existing.txt', 'ステージ済みの編集\n');
    git(root, 'add', 'existing.txt');
    await put(root, 'existing.txt', '未ステージの追加編集\n');
    await put(root, 'source-kit/input.txt', '移行元\n');
    await rm(path.join(root, 'deleted.txt'));
  }
  const initialStatus = git(root, 'status', '--porcelain', '--untracked-files=all');
  const initialIndex = git(root, 'ls-files', '--stage');
  const head = git(root, 'rev-parse', 'HEAD');
  const id = start(root);
  assert.equal(git(root, 'status', '--porcelain', '--untracked-files=all'), initialStatus);
  assert.equal(git(root, 'ls-files', '--stage'), initialIndex);
  const run = path.join('.autoflow/runs', id);
  const step = name => ok(root, name, '--run', id);
  step('verify');
  step('plan-new');
  await put(root, `${run}/plan/1/plan.json`, {
    kind: 'feature', goal: '具体例を追加する', non_goals: [], scope: ['docs/note.md'],
    criteria: [{id: 'C1', text: '文書が存在する', check: 'command', run: 'node -e "require(\'fs\').accessSync(\'docs/note.md\')"'}],
    repro: '', root_cause: '', dependencies_to_add: [], open_questions: [],
    revert: '変更コミットを戻す', commit_subject: '具体例を追加する',
  });
  step('plan-check');
  step('build-new');
  await put(root, 'docs/note.md', '# 具体例\n');
  await put(root, `${run}/build/1/report.json`, {summary: '具体例を追加した', explanation: '文書を追加した', resolutions: [], blockers: []});
  step('build-check');
  step('verify');
  const evidence = JSON.parse(await readFile(path.join(root, run, 'evidence/2.json')));
  assert.equal(evidence.passed, true);
  assert.equal(evidence.results.length, 2);
  step('risk-new');
  await put(root, `${run}/risk/1/judgment.json`, {tier: 'low', human_required: false, reasons: ['テスト用の小さな文書更新'], attention_files: []});
  step('risk-check');
  step('review-new');
  // 実モデルの代わりに、独立した各役が返すJSONのfixtureを用いる。
  for (const lens of ['correctness', 'intent']) await put(root, `${run}/review/round-1/finder-${lens}.json`, {findings: []});
  step('review-collect');
  step('review-tally');
  step('handoff');
  assert.equal(cli(root, 'commit', '--run', id).status, 1);
  ok(root, 'decide', '--run', id, '--gate', 'H3', '--choice', 'approve', '--answer', 'テスト用の最終承認');
  await put(root, 'docs/note.md', '# 承認後の別の内容\n');
  assert.equal(cli(root, 'commit', '--run', id).status, 1);
  assert.equal(git(root, 'rev-parse', 'HEAD'), head);
  await put(root, 'docs/note.md', '# 具体例\n');
  step('commit');
  assert.notEqual(git(root, 'rev-parse', 'HEAD'), head);
  assert.equal(git(root, 'diff', '--name-only', head, 'HEAD'), 'docs/note.md');
  assert.equal(git(root, 'status', '--porcelain', '--untracked-files=all'), initialStatus);
  if (dirty) {
    assert.equal(await readFile(path.join(root, 'existing.txt'), 'utf8'), '未ステージの追加編集\n');
    assert.equal(git(root, 'show', ':existing.txt'), 'ステージ済みの編集');
    assert.equal(await readFile(path.join(root, 'source-kit/input.txt'), 'utf8'), '移行元\n');
  }
  assert.match(step('status'), /^終了:/m);
});

test('同じファイルの独立した編集を分離し、開始前のステージ済み・未ステージ内容を保つ', async t => {
  const {root} = await fixture(t);
  const lines = Array.from({length: 40}, (_, i) => `元の行 ${i}\n`);
  await put(root, 'shared.txt', lines.join(''));
  commitAll(root);
  const head = git(root, 'rev-parse', 'HEAD');
  const staged = [...lines];
  staged[2] = '利用者のステージ済み編集\n';
  await put(root, 'shared.txt', staged.join(''));
  git(root, 'add', 'shared.txt');
  const working = [...staged];
  working[8] = '利用者の未ステージ編集\n';
  await put(root, 'shared.txt', working.join(''));
  const index = await readFile(path.join(root, '.git/index'));
  const base = snapshot(root);
  assert.deepEqual(await readFile(path.join(root, '.git/index')), index);
  working[35] = '今回の変更\n';
  await put(root, 'shared.txt', working.join(''));
  const result = commitDelta(root, base, snapshot(root), head);
  assert.equal(result.status, 0, result.stderr);
  lines[35] = '今回の変更\n';
  staged[35] = '今回の変更\n';
  assert.equal(git(root, 'show', 'HEAD:shared.txt'), lines.join('').trim());
  assert.equal(git(root, 'show', ':shared.txt'), staged.join('').trim());
  assert.equal(await readFile(path.join(root, 'shared.txt'), 'utf8'), working.join(''));
});

test('既存編集との競合やHEADの移動では、実ファイル・ステージング・HEADを変更しない', async t => {
  const {root} = await fixture(t);
  await put(root, 'shared.txt', '元の内容\n');
  commitAll(root);
  const head = git(root, 'rev-parse', 'HEAD');
  await put(root, 'shared.txt', '利用者の編集\n');
  git(root, 'add', 'shared.txt');
  const base = snapshot(root);
  await put(root, 'shared.txt', 'その編集に重なる今回の変更\n');
  const tree = snapshot(root);
  const index = git(root, 'ls-files', '--stage');
  const result = commitDelta(root, base, tree, head);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /今回の差分を既存変更から分離できません/);
  assert.equal(git(root, 'rev-parse', 'HEAD'), head);
  assert.equal(git(root, 'ls-files', '--stage'), index);
  assert.equal(await readFile(path.join(root, 'shared.txt'), 'utf8'), 'その編集に重なる今回の変更\n');
  git(root, 'commit', '--allow-empty', '-qm', '別の作業のコミット');
  const moved = git(root, 'rev-parse', 'HEAD');
  const afterMove = commitDelta(root, base, tree, head);
  assert.notEqual(afterMove.status, 0);
  assert.match(afterMove.stderr, /HEAD が変わりました/);
  assert.equal(git(root, 'rev-parse', 'HEAD'), moved);
});

test('今回のバイナリ追加・削除・空白を含むファイル名を既存変更と分離してコミットする', async t => {
  const {root} = await fixture(t);
  await put(root, 'remove me.txt', '削除する\n');
  commitAll(root);
  const head = git(root, 'rev-parse', 'HEAD');
  await put(root, 'untouched.txt', '移行元\n');
  const base = snapshot(root);
  const data = Buffer.from([0, 255, 1, 254, 0]);
  await writeFile(path.join(root, 'new binary.bin'), data);
  await rm(path.join(root, 'remove me.txt'));
  const result = commitDelta(root, base, snapshot(root), head);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(git(root, 'diff', '--name-only', head, 'HEAD'), 'new binary.bin\nremove me.txt');
  assert.deepEqual(spawnSync('git', ['show', 'HEAD:new binary.bin'], {cwd: root}).stdout, data);
  assert.equal(git(root, 'status', '--porcelain'), '?? untouched.txt');
});

test('未追跡の移行元を片付けても、移行先と追跡済みファイルの変更だけをコミットする', async t => {
  const {root} = await fixture(t);
  await put(root, 'tracked-old.txt', '追跡済みで今回削除する\n');
  commitAll(root);
  const head = git(root, 'rev-parse', 'HEAD');
  const source = 'source kit/[input].txt';
  await put(root, source, '移行する実装\n');
  await put(root, 'unrelated/input.txt', '今回の対象外\n');
  const base = snapshot(root);
  await put(root, 'patterns/sample/basic/migrated/input.txt', await readFile(path.join(root, source), 'utf8'));
  await rm(path.join(root, 'source kit'), {recursive: true});
  await rm(path.join(root, 'tracked-old.txt'));
  const result = commitDelta(root, base, snapshot(root), head);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(git(root, 'diff', '--name-only', head, 'HEAD'), 'patterns/sample/basic/migrated/input.txt\ntracked-old.txt');
  assert.equal(git(root, 'show', 'HEAD:patterns/sample/basic/migrated/input.txt'), '移行する実装');
  await assert.rejects(access(path.join(root, 'source kit')));
  assert.equal(await readFile(path.join(root, 'unrelated/input.txt'), 'utf8'), '今回の対象外\n');
  assert.equal(git(root, 'status', '--porcelain', '--untracked-files=all'), '?? unrelated/input.txt');
});
