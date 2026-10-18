import {cp, mkdtemp, rm, mkdir, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

export const repository = fileURLToPath(new URL('../../', import.meta.url));
export const fixture = fileURLToPath(new URL('../fixtures/valid-project/', import.meta.url));

export async function project(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'pattern-test-'));
  t.after(() => rm(root, {recursive: true, force: true}));
  await cp(fixture, root, {recursive: true});
  return root;
}

export async function put(root, name, content) {
  const file = path.join(root, name);
  await mkdir(path.dirname(file), {recursive: true});
  await writeFile(file, content);
}

export function cli(script, root, args = []) {
  return spawnSync(process.execPath, [path.join(repository, 'scripts', script), '--root', root, ...args], {encoding: 'utf8', timeout: 15000});
}
