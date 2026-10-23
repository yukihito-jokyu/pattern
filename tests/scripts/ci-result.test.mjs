import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, chmod, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {parse} from 'yaml';
import {evaluateNeeds, reportCI} from '../../scripts/ci-result.mjs';
import {reportTiming} from '../../scripts/ci-timing-report.mjs';

const workflow = parse(await readFile(new URL('../../.github/workflows/ci.yml', import.meta.url), 'utf8'));
function needs({verify = 'success', discovery = 'success', patterns = 'success', hasPatterns = 'true'} = {}) {
  return {verify: {result: verify}, 'discover-patterns': {result: discovery, outputs: {'has-patterns': hasPatterns}},
    patterns: {result: patterns}, deploy: {result: 'skipped'}};
}

// Evaluate only trusted, repository-owned expressions; no PR data is interpreted as code.
function condition(expression, {github, upstream, cancelled = false}) {
  return Function('github', 'needs', 'cancelled', 'always', 'steps',
    `return (${expression.replace(/^\$\{\{\s*|\s*\}\}$/g, '')
      .replace(/\.([a-z]+(?:-[a-z]+)+)/g, "['$1']")});`)(github, upstream, () => cancelled, () => true, {});
}

test('検証の失敗・時間切れ・キャンセル・不正なスキップをreportと公開の両方で拒否する', () => {
  const states = ['success', 'failure', 'timed_out', 'cancelled', 'skipped', undefined];
  for (const verify of states) for (const discovery of states) for (const patterns of states) {
    for (const flag of ['true', 'false', '', 'invalid', undefined]) {
      const upstream = needs();
      upstream.verify.result = verify;
      upstream['discover-patterns'] = {result: discovery, outputs: {'has-patterns': flag}};
      upstream.patterns.result = patterns;
      const expected = verify === 'success' && discovery === 'success' &&
        ((flag === 'true' && patterns === 'success') || (flag === 'false' && patterns === 'skipped'));
      assert.equal(evaluateNeeds(upstream).ok, expected, JSON.stringify(upstream));
      assert.equal(condition(workflow.jobs.deploy.if, {upstream,
        github: {event_name: 'push', ref: 'refs/heads/main'}}), expected, JSON.stringify(upstream));
    }
  }
  for (const incomplete of [null, {}, {verify: {result: 'success'}}]) assert.equal(evaluateNeeds(incomplete).ok, false);
});

test('全PRでreportを実行し、PRとmainを別グループにしてPRだけ古い実行を止める', () => {
  for (const actor of ['person', 'dependabot[bot]']) for (const repo of ['sample/repo', 'fork/repo']) {
    const github = {event_name: 'pull_request', actor,
      event: {pull_request: {number: 23, head: {repo: {full_name: repo}}}}};
    assert.equal(condition(workflow.jobs.report.if, {github}), true);
    assert.equal(condition(workflow.concurrency['cancel-in-progress'], {github}), true);
    assert.equal(condition(workflow.jobs.deploy.if, {github, upstream: needs()}), false);
  }
  assert.equal(condition(workflow.jobs.report.if, {github: {}, cancelled: true}), false);
  assert.equal(condition(workflow.concurrency['cancel-in-progress'], {github: {event_name: 'push'}}), false);
  assert.equal(workflow.concurrency.group, '${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}');
  assert.equal(workflow.jobs.deploy.concurrency['cancel-in-progress'], false);
});

test('コメントAPIの失敗は警告に分け、品質検証の失敗を成功へ変えない', async () => {
  for (const verify of ['success', 'failure']) {
    const summaries = [];
    const warnings = [];
    const result = await reportCI({env: {NEEDS: JSON.stringify(needs({verify})), GITHUB_STEP_SUMMARY: 'summary'},
      timing: async () => {throw new Error('403 Resource not accessible by integration');},
      summary: async (_, body) => summaries.push(body), warn: message => warnings.push(message)});
    assert.equal(result.ok, verify === 'success');
    assert.equal(result.timing.posted, false);
    assert.match(summaries[0], verify === 'success' ? /✅ 成功/ : /❌ 失敗/);
    assert.match(summaries[1], /時間レポート/);
    assert.match(warnings[0], /403/);
  }
});

test('Fork・Dependabot・pushでも合否を判定するがコメントAPIは呼ばない', async () => {
  for (const eventName of ['pull_request', 'push']) for (const actor of ['person', 'dependabot[bot]']) {
    for (const repo of ['sample/repo', 'fork/repo']) for (const verify of ['success', 'failure']) {
      const event = {pull_request: {head: {repo: {full_name: repo}}, user: {login: actor}}};
      const env = {NEEDS: JSON.stringify(needs({verify})), GITHUB_EVENT_NAME: eventName,
        GITHUB_REPOSITORY: 'sample/repo', GITHUB_ACTOR: actor};
      if (eventName === 'pull_request' && actor === 'person' && repo === 'sample/repo') continue;
      const result = await reportCI({env, summary: async () => {},
        timing: input => reportTiming({...input, event, api: () => assert.fail('APIを呼んだ')})});
      assert.equal(result.ok, verify === 'success');
      assert.equal(result.timing.posted, false);
    }
  }
});

test('CLIは不正入力・検証失敗で非0を返し、対象0件の正当な省略だけは合格する', async t => {
  const temp = await mkdtemp(path.join(tmpdir(), 'ci-result-'));
  t.after(() => rm(temp, {recursive: true, force: true}));
  const eventPath = path.join(temp, 'event.json');
  await writeFile(eventPath, '{}');
  for (const [input, expected] of [
    [needs(), 0], [needs({hasPatterns: 'false', patterns: 'skipped'}), 0],
    [needs({patterns: 'skipped'}), 1], [needs({verify: 'failure'}), 1], ['invalid-json', 1],
  ]) {
    const result = spawnSync(process.execPath, ['scripts/ci-result.mjs'], {
      cwd: new URL('../../', import.meta.url), encoding: 'utf8',
      env: {...process.env, NEEDS: typeof input === 'string' ? input : JSON.stringify(input),
        GITHUB_EVENT_NAME: 'push', GITHUB_EVENT_PATH: eventPath, GITHUB_STEP_SUMMARY: path.join(temp, 'summary')},
    });
    assert.equal(result.status, expected, result.stderr + result.stdout);
  }
});

test('公開ロック内でmainを再確認し、古いコミットとAPI失敗ではPages APIへ進めない', async t => {
  const temp = await mkdtemp(path.join(tmpdir(), 'ci-deploy-'));
  t.after(() => rm(temp, {recursive: true, force: true}));
  const guard = workflow.jobs.deploy.steps[0];
  assert.equal(guard.id, 'current');
  for (const step of workflow.jobs.deploy.steps.slice(1)) {
    assert.equal(step.if, "${{ steps.current.outputs.current == 'true' }}");
  }
  const sha = 'a'.repeat(40);
  for (const [current, apiStatus, expectedStatus, expectedOutput] of [
    [sha, 0, 0, 'true'], ['b'.repeat(40), 0, 0, 'false'], ['', 1, 1, undefined],
  ]) {
    await writeFile(path.join(temp, 'gh'), '#!/bin/sh\nprintf "%s\\n" "$TEST_CURRENT_SHA"\nexit "$TEST_API_STATUS"\n');
    await chmod(path.join(temp, 'gh'), 0o755);
    const output = path.join(temp, 'output');
    await writeFile(output, '');
    const result = spawnSync('bash', ['-e', '-o', 'pipefail', '-c', guard.run], {encoding: 'utf8', env: {
      ...process.env, PATH: `${temp}:${process.env.PATH}`, GITHUB_REPOSITORY: 'sample/repo', GITHUB_SHA: sha,
      TEST_CURRENT_SHA: current, TEST_API_STATUS: String(apiStatus), GITHUB_OUTPUT: output,
      GITHUB_STEP_SUMMARY: path.join(temp, 'summary'),
    }});
    assert.equal(result.status, expectedStatus, result.stderr);
    assert.equal(await readFile(output, 'utf8'), expectedOutput ? `current=${expectedOutput}\n` : '');
  }
});

test('全ActionをSHA固定し、共通Node版・検査基盤・ZIP検証時間を維持する', async () => {
  assert.equal((await readFile(new URL('../../.nvmrc', import.meta.url), 'utf8')).trim(), '22');
  for (const job of Object.values(workflow.jobs)) {
    assert.equal(job['runs-on'], 'ubuntu-24.04');
    for (const step of job.steps) {
      assert.ok(step.name);
      if (step.uses) assert.match(step.uses, /@[a-f\d]{40}$/);
      if (step.uses?.startsWith('actions/checkout@')) assert.equal(step.with['persist-credentials'], false);
      if (step.uses?.startsWith('actions/setup-node@')) assert.equal(step.with['node-version-file'], '.nvmrc');
    }
  }
  const verify = workflow.jobs.verify.steps;
  assert.equal(verify[0].with['fetch-depth'], 0);
  assert.ok(verify.some(step => /gha\.py check --ratchet/.test(step.run ?? '')));
  assert.equal(workflow.jobs['discover-patterns']['timeout-minutes'], 10);
  assert.equal(workflow.jobs.patterns['timeout-minutes'], 25);
  assert.equal(workflow.jobs.patterns.strategy['fail-fast'], false);
  assert.ok(workflow.jobs.patterns.steps.some(step => /--timeout-ms 1200000/.test(step.run ?? '')));
});
