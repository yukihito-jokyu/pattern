import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {duration, marker, renderReport, reportTiming} from '../../scripts/ci-timing-report.mjs';

const sha = 'a'.repeat(40);
const env = {
  GITHUB_EVENT_NAME: 'pull_request', GITHUB_REPOSITORY: 'sample/repo', GITHUB_ACTOR: 'person',
  GITHUB_RUN_ID: '100', GITHUB_RUN_ATTEMPT: '1', GITHUB_SERVER_URL: 'https://github.com',
  GITHUB_STEP_SUMMARY: 'summary.md',
};
const event = {pull_request: {number: 23, head: {sha, repo: {full_name: 'sample/repo'}}, user: {login: 'person'}}};
function timed(name, seconds, extra = {}) {
  return {name, status: 'completed', conclusion: 'success', started_at: '2026-10-23T00:00:00Z',
    completed_at: new Date(Date.parse('2026-10-23T00:00:00Z') + seconds * 1000).toISOString(), ...extra};
}
const job = timed('verify', 120, {steps: [timed('npm ci', 30, {number: 1}), timed('npm test', 60, {number: 2})]});

function harness({jobs = [[job]], comments = [[]], pr = {state: 'open', head: {sha}},
  run = {}, runs = [[]], failWrite = false, details = {}, finishOnRetry = false} = {}) {
  const calls = [];
  const summaries = [];
  const waits = [];
  let jobReads = 0;
  const input = {env, event,
    pause: async milliseconds => waits.push(milliseconds),
    summary: async (file, content) => summaries.push({file, content}),
    api: async (endpoint, options = {}) => {
      calls.push({endpoint, ...options});
      if (options.method) {
        if (failWrite) throw new Error('403 Resource not accessible by integration');
        return {html_url: 'https://github.com/sample/repo/pull/23#issuecomment-1'};
      }
      if (endpoint.endsWith('/actions/runs/100')) return {run_number: 10, run_attempt: 1, workflow_id: 1,
        head_branch: 'feature', head_repository: {id: 1}, ...run};
      if (endpoint.includes('/jobs?')) {
        jobReads++;
        return jobs.map(items => ({jobs: items.map(item => finishOnRetry && jobReads > 1 ? {...item, status: 'completed'} : item)}));
      }
      if (endpoint.includes('/actions/jobs/')) {
        const id = Number(endpoint.split('/').at(-1));
        return details[id] || jobs.flat().find(item => item.id === id);
      }
      if (endpoint.endsWith('/pulls/23')) return pr;
      if (endpoint.includes('/runs?')) return runs.map(items => ({workflow_runs: items}));
      if (endpoint.includes('/comments?')) return comments;
      throw new Error(`想定外のAPI: ${endpoint}`);
    }};
  return {input, calls, summaries, waits, write: () => calls.find(call => call.method)};
}

test('実行時間は0秒・欠落・不正時刻・スキップを区別する', () => {
  assert.equal(duration(timed('step', 0)), 0);
  assert.equal(duration(timed('step', 65)), 65);
  for (const extra of [{started_at: null}, {completed_at: null}, {completed_at: 'invalid'},
    {completed_at: '2026-10-22T00:00:00Z'}, {conclusion: 'skipped'}]) {
    assert.equal(duration(timed('step', 10, extra)), null);
  }
});

test('Jobを時間順、全Stepを実行順に表示し、TOP 10にもJob名と結果を付ける', () => {
  const steps = Array.from({length: 12}, (_, i) => timed(`step-${i}`, i, {number: i})).reverse();
  const report = renderReport({jobs: [job, timed('ZIP (sample/a/b)', 300, {conclusion: 'failure', steps})],
    runUrl: 'https://example.test/run', headSha: sha, runNumber: 10, attempt: 2});
  assert.ok(report.indexOf('| ZIP (sample/a/b) | 5分00秒 | ❌ 失敗 |') < report.indexOf('| verify |'));
  const ranking = report.split('### 時間がかかったStep TOP 10')[1].split('### Job別')[0];
  assert.equal(ranking.split('\n').filter(line => /^\| (verify|ZIP)/.test(line)).length, 10);
  assert.match(ranking, /\| verify \| npm test \| 1分00秒 \| ✅ 成功 \|/);
  const detail = report.split('<details>')[1];
  assert.ok(detail.indexOf('| step-0 |') < detail.indexOf('| step-11 |'));
  assert.match(report, /試行 2/);
  assert.match(report, /並列Jobの合計はCIの待ち時間を表しません/);
});

test('Step名による表・折りたたみの破壊とメンションを防ぐ', () => {
  const report = renderReport({jobs: [timed('evil|\n</summary>@all', 0, {
    steps: [timed('[link](url)`<details>', 0)],
  })], runUrl: 'https://example.test', headSha: sha, runNumber: 1, attempt: 1});
  assert.match(report, /evil\\\| &lt;\/summary&gt;&#64;all/);
  assert.ok(!report.includes('</summary>@all'));
  assert.ok(report.includes('\\[link\\](url)\\`&lt;details&gt;'));
});

test('全ページのmatrixを集計し、初回は投稿、Summaryにも同じ内容を保存する', async () => {
  const h = harness({jobs: [[job, timed('report', 10, {status: 'in_progress'})],
    [timed('ZIP (sample/a/b)', 60), timed('deploy', 0, {conclusion: 'skipped'})]]});
  assert.equal((await reportTiming(h.input)).posted, true);
  assert.equal(h.write().method, 'POST');
  assert.equal(h.write().endpoint, 'repos/sample/repo/issues/23/comments');
  assert.match(h.write().body.body, /ZIP \(sample\/a\/b\)/);
  assert.ok(!h.write().body.body.includes('| deploy |'));
  assert.ok(!h.write().body.body.includes('| report |'));
  assert.equal(h.summaries[0].content, h.write().body.body);
  for (const call of h.calls.filter(call => /\?/.test(call.endpoint))) assert.equal(call.paginate, true);
});

test('2ページ目にあるbotの既存コメントだけを更新する', async () => {
  const h = harness({comments: [[{id: 1, user: {login: 'person'}, body: marker + '\n'}],
    [{id: 2, user: {login: 'github-actions[bot]'}, body: '他のレポート'},
      {id: 3, user: {login: 'github-actions[bot]'}, body: marker + '\nold'}]]});
  await reportTiming(h.input);
  assert.equal(h.write().method, 'PATCH');
  assert.equal(h.write().endpoint, 'repos/sample/repo/issues/comments/3');
});

test('CI失敗・ZIP検証なし・Step情報欠落もレポートする', async () => {
  const h = harness({jobs: [[timed('verify', 60, {conclusion: 'failure', steps: [
    timed('test', 50, {conclusion: 'failure', number: 1}),
    timed('build', 0, {conclusion: 'skipped', number: 2}),
    {name: 'missing', number: 3, status: 'completed', conclusion: 'timed_out'},
  ]}), timed('patterns', 0, {conclusion: 'skipped'})]]});
  await reportTiming(h.input);
  assert.match(h.write().body.body, /\| patterns \| — \| ⏭ スキップ \|/);
  assert.match(h.write().body.body, /\| missing \| — \| ⌛ 時間切れ \|/);
  assert.match(h.write().body.body, /❌ 失敗/);
});

test('対象外のイベント・Fork・DependabotはAPIを呼ばない', async () => {
  for (const overrides of [{env: {...env, GITHUB_EVENT_NAME: 'push'}},
    {env: {...env, GITHUB_ACTOR: 'dependabot[bot]'}},
    {event: {pull_request: {...event.pull_request, user: {login: 'dependabot[bot]'}}}},
    {event: {pull_request: {...event.pull_request, head: {sha, repo: {full_name: 'fork/repo'}}}}}]) {
    const h = harness();
    assert.equal((await reportTiming({...h.input, ...overrides})).posted, false);
    assert.equal(h.calls.length, 0);
  }
});

test('新コミット・終了済みPR・新実行・古い再実行では投稿せずSummaryだけ保存する', async () => {
  for (const changes of [{pr: {state: 'open', head: {sha: 'b'.repeat(40)}}},
    {pr: {state: 'closed', head: {sha}}}, {run: {run_attempt: 2}},
    {runs: [[{run_number: 11, head_branch: 'feature', head_repository: {id: 1}}]]},
    {comments: [[{id: 3, user: {login: 'github-actions[bot]'}, body: marker + '\n<!-- ci-timing-report-run:11:1 -->'}]]},
    {comments: [[{id: 3, user: {login: 'github-actions[bot]'}, body: marker + '\n<!-- ci-timing-report-run:10:2 -->'}]]}]) {
    const h = harness(changes);
    assert.equal((await reportTiming(h.input)).posted, false);
    assert.equal(h.write(), undefined);
    assert.equal(h.summaries.length, 1);
  }
});

test('同じコミットの再実行では最新の試行番号で既存コメントを更新する', async () => {
  // API metadata may still show attempt 1 while attempt 2 is already executing.
  for (const runAttempt of [1, 2]) {
    const h = harness({run: {run_attempt: runAttempt}, comments: [[{id: 3, user: {login: 'github-actions[bot]'},
      body: marker + '\n<!-- ci-timing-report-run:10:1 -->'}]]});
    await reportTiming({...h.input, env: {...env, GITHUB_RUN_ATTEMPT: '2'}});
    assert.equal(h.write().method, 'PATCH');
    assert.match(h.write().body.body, /試行 2/);
  }
});

test('未完了のJobやAPIの失敗を成功扱いしない', async () => {
  const h = harness({jobs: [[timed('verify', 1, {id: 123, status: 'in_progress'})]]});
  await assert.rejects(reportTiming(h.input), /未完了/);
  assert.equal(h.write(), undefined);
  assert.deepEqual(h.waits, Array(6).fill(10000));
  const failed = harness({failWrite: true});
  await assert.rejects(reportTiming(failed.input), /403/);
  assert.equal(failed.summaries.length, 1);
});

test('Job一覧の反映が遅れた場合は詳細APIで完了を確認して投稿する', async () => {
  const h = harness({jobs: [[timed('verify', 60, {id: 123, status: 'in_progress'})]],
    details: {123: timed('verify', 65, {id: 123})}});
  assert.equal((await reportTiming(h.input)).posted, true);
  assert.match(h.write().body.body, /\| verify \| 1分05秒/);
  assert.equal(h.waits.length, 0);
});

test('詳細APIも未反映なら待って一覧を再取得し、完了後に投稿する', async () => {
  const h = harness({jobs: [[timed('verify', 60, {id: 123, status: 'in_progress'})]], finishOnRetry: true});
  assert.equal((await reportTiming(h.input)).posted, true);
  assert.deepEqual(h.waits, [10000]);
});

test('大きなmatrixはコメント上限を守り、全StepをSummaryへ残す', async () => {
  const h = harness({jobs: [[timed('huge ZIP', 120, {steps: Array.from({length: 500}, (_, i) =>
    timed(`step-${i}-` + 'x'.repeat(180), 1, {number: i}))})]]});
  await reportTiming(h.input);
  assert.ok(h.write().body.body.length < 60000);
  assert.match(h.write().body.body, /全StepをActions Summaryで確認/);
  assert.match(h.summaries[0].content, /step-499-/);
});

test('Workflowは全PRの失敗・matrix省略後にも判定し、コメント権限と直列化をreportに限定する', async () => {
  const {parse} = await import('yaml');
  const workflow = parse(await readFile(new URL('../../.github/workflows/ci.yml', import.meta.url), 'utf8'));
  const timing = workflow.jobs.report;
  assert.deepEqual(timing.needs, Object.keys(workflow.jobs).filter(id => id !== 'report').sort());
  assert.equal(timing.if, '${{ !cancelled() }}');
  assert.deepEqual(workflow.permissions, {});
  assert.deepEqual(timing.permissions, {actions: 'read', contents: 'read', 'pull-requests': 'write'});
  assert.equal(timing.concurrency['cancel-in-progress'], false);
  assert.match(timing.concurrency.group, /pull_request.number/);
  assert.equal(workflow.jobs.deploy.needs.includes('report'), false);
});
