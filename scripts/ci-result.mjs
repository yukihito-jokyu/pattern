import {appendFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {reportTiming} from './ci-timing-report.mjs';

// Use needs, rather than the eventually consistent Jobs API, for the quality gate.
export function evaluateNeeds(needs) {
  const failures = [];
  for (const id of ['verify', 'discover-patterns']) {
    if (needs?.[id]?.result !== 'success') failures.push(`${id}: ${needs?.[id]?.result ?? 'missing'}`);
  }
  const hasPatterns = needs?.['discover-patterns']?.outputs?.['has-patterns'];
  const patterns = needs?.patterns?.result;
  if (hasPatterns === 'true') {
    if (patterns !== 'success') failures.push(`patterns: ${patterns ?? 'missing'} (expected success)`);
  } else if (hasPatterns === 'false') {
    if (patterns !== 'skipped') failures.push(`patterns: ${patterns ?? 'missing'} (expected skipped)`);
  } else {
    failures.push('discover-patterns: has-patterns must be true or false');
  }
  return {ok: failures.length === 0, failures};
}

export async function reportCI({env = process.env, timing = reportTiming, summary = appendFile,
  warn = message => console.log(`::warning::${message.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A')}`)} = {}) {
  const result = evaluateNeeds(JSON.parse(env.NEEDS));
  await summary(env.GITHUB_STEP_SUMMARY,
    `## CI検証結果\n\n${result.ok ? '✅ 成功' : '❌ 失敗'}\n\n` +
    (result.failures.length ? result.failures.map(item => `- ${item}`).join('\n') + '\n' : '') +
    '\n合否はサイト検証・対象判定・ZIP検証で決まります。時間コメントとPages公開の結果は別に確認します。\n');
  // Reporting is optional; neither API permissions nor stale API results decide quality.
  try {
    result.timing = await timing({env});
  } catch (error) {
    warn(`時間レポートを作成できませんでした。検証の合否は変わりません: ${error.stderr?.toString().trim() || error.message}`);
    await summary(env.GITHUB_STEP_SUMMARY, '\n⚠️ 時間レポートの取得・投稿に失敗しました。ログの警告を確認してください。\n');
    result.timing = {posted: false, reason: '時間レポートの取得・投稿失敗'};
  }
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const result = await reportCI();
    console.log(JSON.stringify(result));
    if (!result.ok) process.exitCode = 1;
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
