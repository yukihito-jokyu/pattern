import path from 'node:path';
import {patternPaths} from './lib/patterns.mjs';
import {readFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {catalog, requireValid, filesIn, cliOptions, main} from './lib/project.mjs';

const exec = promisify(execFile);
const sharedVerificationFiles = new Set([
  '.github/workflows/ci.yml', 'package.json', 'package-lock.json',
  'scripts/build-downloads.mjs', 'scripts/check-dir.mjs',
  'scripts/verify-patterns.mjs', 'scripts/pattern-ci.mjs',
  'scripts/lib/project.mjs', 'scripts/lib/patterns.mjs',
]);

export async function changedFiles(root, {base, head = 'HEAD', mergeBase = false}) {
  async function git(...args) {
    const {stdout} = await exec('git', ['-C', root, ...args], {encoding: 'utf8', maxBuffer: 16 * 1024 * 1024});
    return stdout;
  }
  try {
    let baseCommit = (await git('rev-parse', '--verify', '--end-of-options', `${base}^{commit}`)).trim();
    const headCommit = (await git('rev-parse', '--verify', '--end-of-options', `${head}^{commit}`)).trim();
    if (mergeBase) baseCommit = (await git('merge-base', baseCommit, headCommit)).trim();
    // 改名を削除＋追加として扱い、旧・新の両パターンを漏らさない。
    return (await git('diff', '--no-ext-diff', '--name-only', '--no-renames', '-z', baseCommit, headCommit, '--')).split('\0').filter(Boolean);
  } catch (error) {
    throw new Error(`変更ファイルの取得に失敗しました。比較元・履歴を確認してください: ${error.message}`);
  }
}

export async function readPatternCI(root, id) {
  const directory = path.join(root, patternPaths(id).implementation);
  const label = `${patternPaths(id).implementation}/ci.json`;
  const config = JSON.parse(await readFile(path.join(directory, 'ci.json'), 'utf8'));
  const allowed = ['command', 'goVersionFile', 'pythonVersion'];
  if (!config || Array.isArray(config) || typeof config !== 'object' || Object.keys(config).some(key => !allowed.includes(key))) throw new Error(`${label}: 未対応の設定です。`);
  if (!Array.isArray(config.command) || !config.command.length || config.command.some(arg => typeof arg !== 'string' || !arg || arg.includes('\0'))) throw new Error(`${label}: commandには実行ファイルと引数の配列が必要です。`);
  if (config.goVersionFile !== undefined) {
    if (typeof config.goVersionFile !== 'string' || !/^[a-zA-Z0-9_./-]+$/.test(config.goVersionFile) || config.goVersionFile.split('/').some(part => !part || part === '..' || part === '.') || !((await filesIn(directory)).includes(path.join(directory, config.goVersionFile)))) throw new Error(`${label}: goVersionFileにはパターン内の実ファイルを指定してください。`);
  }
  if (config.pythonVersion !== undefined && (typeof config.pythonVersion !== 'string' || !/^3\.\d+$/.test(config.pythonVersion))) throw new Error(`${label}: pythonVersionは3.12などの形式で指定してください。`);
  return config;
}

export async function patternMatrix(root, {files} = {}) {
  if (files !== undefined && (!Array.isArray(files) || files.some(file => typeof file !== 'string'))) throw new Error('変更ファイルは文字列の配列で指定してください。');
  const {ids} = requireValid(await catalog(root));
  const verifyAll = files === undefined || files.some(file => sharedVerificationFiles.has(file));
  const include = [];
  for (const id of ids) {
    const config = await readPatternCI(root, id);
    if (!verifyAll && !files.some(file => file.startsWith(`${patternPaths(id).implementation}/`))) continue;
    include.push({id, goVersionFile: config.goVersionFile ? `${patternPaths(id).implementation}/${config.goVersionFile}` : '', pythonVersion: config.pythonVersion ?? ''});
  }
  return {include};
}

main(import.meta.url, async () => {
  const options = cliOptions({base: {type: 'string'}, head: {type: 'string', default: 'HEAD'}, 'merge-base': {type: 'boolean', default: false}});
  if (options['merge-base'] && !options.base) throw new Error('--merge-baseには--baseが必要です。');
  const files = options.base ? await changedFiles(options.root, {base: options.base, head: options.head, mergeBase: options['merge-base']}) : undefined;
  console.log(JSON.stringify(await patternMatrix(options.root, {files})));
});
