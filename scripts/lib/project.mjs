import {readdir, readFile, lstat} from 'node:fs/promises';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {pathToFileURL} from 'node:url';

import {namePattern, patternPaths} from './patterns.mjs';
export {namePattern} from './patterns.mjs';
export const ignored = new Set(['node_modules', 'build', 'dist', '.git', '.cache', '.docusaurus', 'coverage', 'test-results', 'playwright-report', '__pycache__', '.venv', '.DS_Store', '.gitkeep']);
export const exists = async (file) => lstat(file).then(() => true, (e) => {if (e.code === 'ENOENT') return false; throw e;});

export async function filesIn(directory) {
  const result = [];
  if (!await exists(directory)) return result;
  for (const entry of await readdir(directory, {withFileTypes: true})) {
    if (ignored.has(entry.name)) continue;
    const file = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`${file}: シンボリックリンクは扱えません。実ファイルを配置してください。`);
    if (entry.isDirectory()) result.push(...await filesIn(file));
    else if (entry.isFile()) result.push(file);
    else throw new Error(`${file}: 通常のファイルを配置してください。`);
  }
  return result.sort();
}

export async function catalog(root) {
  const errors = [];
  const found = {docs: new Set(), patterns: new Set()};
  for (const kind of ['docs', 'patterns']) {
    const base = path.join(root, kind);
    if (!await exists(base)) {errors.push(`${kind}/: ディレクトリがありません。`); continue;}
    async function visit(directory, parts) {
      for (const entry of await readdir(directory, {withFileTypes: true})) {
        const next = [...parts, entry.name];
        const relative = `${kind}/${next.join('/')}`;
        if (entry.name === '.gitkeep') continue;
        if (kind === 'docs' && !parts.length && entry.name === 'project' && entry.isDirectory()) continue;
        if (kind === 'docs' && entry.name === '_category_.json' && entry.isFile()) continue;
        if (!entry.isDirectory() || !namePattern.test(entry.name) || (!parts.length && entry.name === 'project')) {
          errors.push(`${relative}: 配置・命名違反です。${kind}/<分野>/<分類>/<パターン>/ に英小文字とハイフンで配置してください。`);
          continue;
        }
        if (next.length === 3) found[kind].add(next.join('/'));
        else await visit(path.join(directory, entry.name), next);
      }
    }
    await visit(base, []);
  }
  const ids = [...new Set([...found.docs, ...found.patterns])].sort();
  for (const id of ids) {
    const paths = patternPaths(id);
    const doc = path.join(root, paths.document);
    const implementation = path.join(root, paths.implementation);
    if (!found.docs.has(id) || !await exists(doc)) errors.push(`docs/${id}/index.md: 対応する文書がありません。`);
    if (!found.patterns.has(id)) errors.push(`patterns/${id}/: 対応する実装がありません。`);
    else {
      const files = await filesIn(implementation);
      if (!files.includes(path.join(implementation, 'README.md'))) errors.push(`patterns/${id}/README.md: ZIP単体で利用するための手順が必要です。`);
      if (!files.some(f => path.relative(implementation, f) !== 'README.md')) errors.push(`patterns/${id}/: README以外の実ファイルが必要です。`);
    }
  }
  return {ids, errors};
}

export function requireValid(result) {
  if (result.errors.length) throw new Error(result.errors.join('\n'));
  return result;
}

export function cliOptions(extra = {}) {
  const {values} = parseArgs({options: {root: {type: 'string', default: process.cwd()}, ...extra}, strict: true});
  return {...values, root: path.resolve(values.root)};
}

export function main(moduleUrl, action) {
  if (process.argv[1] && moduleUrl === pathToFileURL(path.resolve(process.argv[1])).href) {
    Promise.resolve().then(action).catch(error => {console.error(error.message); process.exitCode = 1;});
  }
}

export const read = file => readFile(file, 'utf8');
