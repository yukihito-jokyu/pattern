import {execFileSync} from 'node:child_process';
import {appendFile, readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

export const marker = '<!-- ci-timing-report -->';
const labels = {
  success: '✅ 成功', failure: '❌ 失敗', skipped: '⏭ スキップ',
  cancelled: '🛑 キャンセル', timed_out: '⌛ 時間切れ',
  action_required: '確認待ち', neutral: '中立', stale: '期限切れ',
  queued: '待機中', in_progress: '実行中', completed: '完了',
};

export function duration(item) {
  if (item.conclusion === 'skipped' || !item.started_at || !item.completed_at) return null;
  const seconds = (Date.parse(item.completed_at) - Date.parse(item.started_at)) / 1000;
  return Number.isFinite(seconds) && seconds >= 0 ? Math.round(seconds) : null;
}

function elapsed(seconds) {
  if (seconds === null) return '—';
  return seconds >= 60 ? `${Math.floor(seconds / 60)}分${String(seconds % 60).padStart(2, '0')}秒` : `${seconds}秒`;
}

function escape(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/@/g, '&#64;').replace(/[\\`*_[\]{}|]/g, '\\$&').replace(/[\r\n]+/g, ' ');
}

function result(item) {
  const value = item.conclusion || item.status || '不明';
  return labels[value] || escape(value);
}

export function renderReport({jobs, runUrl, headSha, runNumber, attempt, includeDetails = true}) {
  const sorted = [...jobs].sort((a, b) => (duration(b) ?? -1) - (duration(a) ?? -1));
  const lines = [marker, `<!-- ci-timing-report-run:${runNumber}:${attempt} -->`,
    '## ⏱ CI実行時間レポート', '',
    `対象コミット: \`${headSha}\` / 実行 #${runNumber} / 試行 ${attempt}`, '',
    `[Actions実行結果](${runUrl})`, '',
    '時間は各Job・Stepの開始から終了までです。並列Jobの合計はCIの待ち時間を表しません。',
    'スキップ・時刻欠落などで計測できない時間は「—」です。', '',
    '| Job | 実行時間 | 結果 |', '|---|---:|---|'];
  for (const job of sorted) {
    lines.push(`| ${escape(job.name)} | ${elapsed(duration(job))} | ${result(job)} |`);
  }
  if (!jobs.length) lines.push('| 対象Jobなし | — | — |');

  const steps = jobs.flatMap(job => (job.steps || []).map(step => ({job, step, seconds: duration(step)})))
    .filter(item => item.seconds !== null).sort((a, b) => b.seconds - a.seconds);
  lines.push('', '### 時間がかかったStep TOP 10', '',
    '| Job | Step | 実行時間 | 結果 |', '|---|---|---:|---|');
  for (const {job, step, seconds} of steps.slice(0, 10)) {
    lines.push(`| ${escape(job.name)} | ${escape(step.name)} | ${elapsed(seconds)} | ${result(step)} |`);
  }
  if (!steps.length) lines.push('| — | 計測可能なStepなし | — | — |');

  if (includeDetails) {
    lines.push('', '### Job別の全Step詳細');
    for (const job of sorted) {
      lines.push('', '<details>', `<summary>${escape(job.name)}：${elapsed(duration(job))} / ${result(job)}</summary>`, '',
        '| Step | 実行時間 | 結果 |', '|---|---:|---|');
      for (const step of [...(job.steps || [])].sort((a, b) => a.number - b.number)) {
        lines.push(`| ${escape(step.name)} | ${elapsed(duration(step))} | ${result(step)} |`);
      }
      if (!job.steps?.length) lines.push('| Step情報なし | — | — |');
      lines.push('', '</details>');
    }
  }
  return lines.join('\n') + '\n';
}

// gh handles authentication and pagination. JSON bodies travel through stdin, never a shell.
export function githubApi(endpoint, {method = 'GET', body, paginate = false} = {}) {
  const args = ['api', '--method', method, endpoint];
  if (paginate) args.push('--paginate', '--slurp');
  if (body !== undefined) args.push('--input', '-');
  const output = execFileSync('gh', args, {
    input: body === undefined ? undefined : JSON.stringify(body), encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe'],
  });
  return JSON.parse(output);
}

function rows(pages, key) {
  return pages.flatMap(page => key ? page[key] : page);
}

export async function reportTiming({env = process.env, api = githubApi, summary = appendFile, event} = {}) {
  event ??= JSON.parse(await readFile(env.GITHUB_EVENT_PATH, 'utf8'));
  const pr = event.pull_request;
  if (env.GITHUB_EVENT_NAME !== 'pull_request' || !pr || pr.head.repo?.full_name !== env.GITHUB_REPOSITORY ||
      env.GITHUB_ACTOR === 'dependabot[bot]' || pr.user?.login === 'dependabot[bot]') return {posted: false, reason: '対象外のPR'};

  const repo = env.GITHUB_REPOSITORY;
  const runId = Number(env.GITHUB_RUN_ID);
  const attempt = Number(env.GITHUB_RUN_ATTEMPT);
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !Number.isSafeInteger(runId) || runId <= 0 ||
      !Number.isSafeInteger(attempt) || attempt <= 0 || !Number.isSafeInteger(pr.number) ||
      !/^[a-f\d]{40,64}$/i.test(pr.head.sha)) throw new Error('実行情報が不正です。');

  const base = `repos/${repo}`;
  const run = await api(`${base}/actions/runs/${runId}`);
  const runUrl = `${env.GITHUB_SERVER_URL}/${repo}/actions/runs/${runId}/attempts/${attempt}`;
  const jobs = rows(await api(`${base}/actions/runs/${runId}/jobs?filter=latest&per_page=100`, {paginate: true}), 'jobs')
    .filter(job => job.name !== 'CI Timing Report' && job.name !== 'deploy');
  // needs waits for the whole matrix; never present an incomplete API snapshot as a final report.
  if (jobs.some(job => job.status !== 'completed')) throw new Error('未完了のJobがあるため集計を中止しました。');
  const options = {jobs, runUrl, headSha: pr.head.sha, runNumber: run.run_number, attempt};
  const report = renderReport(options);
  await summary(env.GITHUB_STEP_SUMMARY, report);

  const currentPr = await api(`${base}/pulls/${pr.number}`);
  if (currentPr.state !== 'open' || currentPr.head.sha !== pr.head.sha) return {posted: false, reason: 'PRが終了済み、または古いコミット'};
  if (run.run_attempt !== attempt) return {posted: false, reason: '古い再実行'};
  const runs = rows(await api(`${base}/actions/workflows/${run.workflow_id}/runs?event=pull_request&head_sha=${pr.head.sha}&per_page=100`, {paginate: true}), 'workflow_runs');
  if (runs.some(other => other.head_branch === run.head_branch && other.head_repository?.id === run.head_repository?.id &&
      other.run_number > run.run_number)) return {posted: false, reason: '新しいCI実行が存在'};

  const comments = rows(await api(`${base}/issues/${pr.number}/comments?per_page=100`, {paginate: true}));
  const comment = comments.find(item => item.user?.login === 'github-actions[bot]' && item.body?.startsWith(marker + '\n'));
  const previous = comment?.body.match(/<!-- ci-timing-report-run:(\d+):(\d+) -->/);
  if (previous && (Number(previous[1]) > run.run_number ||
      (Number(previous[1]) === run.run_number && Number(previous[2]) > attempt))) return {posted: false, reason: '新しいレポートが存在'};

  // Very large matrices may exceed GitHub's comment limit; Summary always retains every step.
  const body = report.length <= 60000 ? report : renderReport({...options, includeDetails: false}).slice(0, 58000) +
    `\n\nコメントの文字数上限を避けるため詳細を省略しました。[全StepをActions Summaryで確認](${runUrl}#summary)\n`;
  const response = await api(comment ? `${base}/issues/comments/${comment.id}` : `${base}/issues/${pr.number}/comments`, {
    method: comment ? 'PATCH' : 'POST', body: {body},
  });
  return {posted: true, url: response.html_url};
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(JSON.stringify(await reportTiming()));
  } catch (error) {
    console.error(error.stderr?.toString().trim() || error.message);
    process.exitCode = 1;
  }
}
