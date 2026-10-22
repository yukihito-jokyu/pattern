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

test('補助CLIが検査・レビュー・H3へ進み、承認後の差分変更をコミットしない', async t => {
  const {root} = await fixture(t);
  ok(root, 'setup-approve', '--answer', 'テスト用の承認');
  commitAll(root);
  const head = git(root, 'rev-parse', 'HEAD');
  const id = start(root);
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
  assert.match(step('status'), /^終了:/m);
});
