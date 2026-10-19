import path from 'node:path';
import {patternPaths} from './lib/patterns.mjs';
import {readFile} from 'node:fs/promises';
import {catalog, requireValid, filesIn, cliOptions, main} from './lib/project.mjs';

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

export async function patternMatrix(root) {
  const {ids} = requireValid(await catalog(root));
  const include = [];
  for (const id of ids) {
    const config = await readPatternCI(root, id);
    include.push({id, goVersionFile: config.goVersionFile ? `${patternPaths(id).implementation}/${config.goVersionFile}` : '', pythonVersion: config.pythonVersion ?? ''});
  }
  return {include};
}

main(import.meta.url, async () => console.log(JSON.stringify(await patternMatrix(cliOptions().root))));
