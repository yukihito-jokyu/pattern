import path from 'node:path';
import os from 'node:os';
import {mkdtemp, cp, symlink, rm} from 'node:fs/promises';
import {spawn, spawnSync} from 'node:child_process';
import {repository, fixture} from './temporary-project.mjs';

const temp = await mkdtemp(path.join(os.tmpdir(), 'pattern-browser-'));
let child;
let closing = false;
async function cleanup() {
  if (closing) return;
  closing = true;
  child?.kill('SIGTERM');
  if (child && child.exitCode === null) await new Promise(resolve => child.once('exit', resolve));
  await rm(temp, {recursive: true, force: true});
}
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => {cleanup().then(() => process.exit());});
try {
  for (const name of ['package.json', 'docusaurus.config.ts', 'sidebars.ts', 'tsconfig.json', 'src', 'plugins', 'scripts', 'docs', 'patterns']) {
    await cp(path.join(repository, name), path.join(temp, name), {recursive: true});
  }
  await cp(path.join(fixture, 'docs'), path.join(temp, 'docs'), {recursive: true});
  await cp(path.join(fixture, 'patterns'), path.join(temp, 'patterns'), {recursive: true});
  await symlink(path.join(repository, 'node_modules'), path.join(temp, 'node_modules'), 'dir');
  const env = {...process.env, SITE_BASE_URL: '/preview/', NODE_ENV: 'production'};
  const result = spawnSync('npm', ['run', 'build'], {cwd: temp, env, stdio: 'inherit', timeout: 160000});
  if (result.status !== 0) throw new Error('ブラウザー検証用サイトのビルドに失敗しました。');
  child = spawn(process.execPath, [path.join(repository, 'node_modules/@docusaurus/core/bin/docusaurus.mjs'), 'serve', '--host', '127.0.0.1', '--port', '4173', '--no-open'], {cwd: temp, env, stdio: 'inherit'});
  child.on('exit', code => {if (!closing) cleanup().then(() => process.exit(code || 0));});
} catch (error) {
  console.error(error);
  await cleanup();
  process.exitCode = 1;
}
