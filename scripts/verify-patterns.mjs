import path from 'node:path';
import os from 'node:os';
import {parseArgs} from 'node:util';
import {spawn} from 'node:child_process';
import {mkdir, mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {unzipSync} from 'fflate';
import {buildDownloads} from './build-downloads.mjs';
import {main} from './lib/project.mjs';

export async function runVerification(directory, command, timeout) {
  return new Promise(resolve => {
    let stdout = '', stderr = '', timedOut = false, settled = false;
    const child = spawn(command[0], command.slice(1), {cwd: directory, detached: process.platform !== 'win32', env: {...process.env, NODE_PATH: '', NODE_OPTIONS: ''}, stdio: ['ignore', 'pipe', 'pipe']});
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
    child.on('error', error => finish({state: error.code === 'ENOENT' ? '未実施' : '失敗', detail: error.message}));
    child.on('close', code => finish({
      state: timedOut ? '失敗' : code === 0 ? '成功' : '失敗',
      detail: timedOut ? `時間切れ (${timeout}ms)` : `終了コード${code}\n${stdout}${stderr}`,
    }));
  });
}

export async function verifyPatterns(root, {id, command, timeout = 120000} = {}) {
  if (!Number.isSafeInteger(timeout) || timeout < 1) throw new Error('timeoutは1以上の整数（ミリ秒）にしてください。');
  if (!id) throw new Error('--idで検証対象を指定してください。');
  if (!Array.isArray(command) || !command.length || command.some(arg => typeof arg !== 'string') || !command[0]) throw new Error('--の後に検証コマンドと引数を指定してください。');
  if (!/^[a-z][a-z0-9-]*\/[a-z][a-z0-9-]*\/[a-z][a-z0-9-]*$/.test(id)) throw new Error(`不正なパターンIDです: ${id}`);
  const {ids, output} = await buildDownloads(root);
  if (!ids.includes(id)) throw new Error(`パターンがありません: ${id}`);
  const results = [];
  for (const target of [id]) {
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
      results.push({id: target, ...await runVerification(directory, command, timeout)});
    } finally {await rm(temp, {recursive: true, force: true});}
  }
  return results;
}

main(import.meta.url, async () => {
  const {values: options, positionals: command} = parseArgs({
    allowPositionals: true,
    options: {root: {type: 'string', default: process.cwd()}, id: {type: 'string'}, 'timeout-ms': {type: 'string', default: '120000'}},
  });
  const results = await verifyPatterns(options.root, {id: options.id, command, timeout: Number(options['timeout-ms'])});
  for (const result of results) console.log(`${result.id}: ${result.state}\n${result.detail}`);
  if (results.some(result => result.state !== '成功')) process.exitCode = 1;
});
