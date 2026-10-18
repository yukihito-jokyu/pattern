import path from 'node:path';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {mkdir, mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {unzipSync} from 'fflate';
import {buildDownloads} from './build-downloads.mjs';
import {cliOptions, exists, main} from './lib/project.mjs';

export async function runVerification(directory, timeout) {
  const entry = path.join(directory, 'verify.mjs');
  if (!await exists(entry)) return {state: '未実施', detail: 'verify.mjsがありません。'};
  return new Promise(resolve => {
    let stdout = '', stderr = '', timedOut = false, settled = false;
    const child = spawn(process.execPath, [entry], {cwd: directory, detached: process.platform !== 'win32', env: {...process.env, NODE_PATH: '', NODE_OPTIONS: ''}, stdio: ['ignore', 'pipe', 'pipe']});
    const append = (previous, chunk) => (previous + chunk.toString()).slice(-65536);
    child.stdout.on('data', chunk => {stdout = append(stdout, chunk);});
    child.stderr.on('data', chunk => {stderr = append(stderr, chunk);});
    const timer = setTimeout(() => {
      timedOut = true;
      if (process.platform !== 'win32' && child.pid) {
        try {process.kill(-child.pid, 'SIGKILL');} catch {child.kill('SIGKILL');}
      } else child.kill('SIGKILL');
    }, timeout);
    function finish(result) {if (settled) return; settled = true; clearTimeout(timer); resolve(result);}
    child.on('error', error => finish({state: '失敗', detail: error.message}));
    child.on('close', code => finish({
      state: timedOut ? '失敗' : code === 0 ? '成功' : code === 2 ? '未実施' : '失敗',
      detail: timedOut ? `時間切れ (${timeout}ms)` : `終了コード${code}\n${stdout}${stderr}`,
    }));
  });
}

export async function verifyPatterns(root, {id, timeout = 120000} = {}) {
  if (!Number.isSafeInteger(timeout) || timeout < 1) throw new Error('timeoutは1以上の整数（ミリ秒）にしてください。');
  if (id && !/^[a-z][a-z0-9-]*\/[a-z][a-z0-9-]*\/[a-z][a-z0-9-]*$/.test(id)) throw new Error(`不正なパターンIDです: ${id}`);
  const {ids, output} = await buildDownloads(root);
  if (id && !ids.includes(id)) throw new Error(`パターンがありません: ${id}`);
  const results = [];
  for (const target of id ? [id] : ids) {
    const temp = await mkdtemp(path.join(os.tmpdir(), 'pattern-verify-'));
    try {
      const entries = unzipSync(await readFile(path.join(output, `${target}.zip`)));
      const directory = path.join(temp, path.posix.basename(target));
      for (const [name, content] of Object.entries(entries)) {
        const file = path.resolve(temp, name);
        if (!file.startsWith(directory + path.sep)) throw new Error(`${target}: ZIPの展開先が不正です: ${name}`);
        await mkdir(path.dirname(file), {recursive: true});
        await writeFile(file, content);
      }
      results.push({id: target, ...await runVerification(directory, timeout)});
    } finally {await rm(temp, {recursive: true, force: true});}
  }
  return results;
}

main(import.meta.url, async () => {
  const options = cliOptions({id: {type: 'string'}, all: {type: 'boolean'}, 'timeout-ms': {type: 'string', default: '120000'}});
  if (options.id && options.all) throw new Error('--idと--allは同時に指定できません。');
  const results = await verifyPatterns(options.root, {id: options.id, timeout: Number(options['timeout-ms'])});
  for (const result of results) console.log(`${result.id}: ${result.state}\n${result.detail}`);
  if (!results.length) console.log('検証対象0件。実パターンの動作確認は未実施です。');
  if (results.some(result => result.state !== '成功')) process.exitCode = 1;
});
