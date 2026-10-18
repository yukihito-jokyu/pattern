import path from 'node:path';
import {mkdir, mkdtemp, readFile, writeFile, rename, rm, lstat} from 'node:fs/promises';
import {zipSync, unzipSync} from 'fflate';
import {checkDir} from './check-dir.mjs';
import {cliOptions, exists, filesIn, main} from './lib/project.mjs';

export async function buildDownloads(root) {
  const {ids} = await checkDir(root);
  const parent = path.join(root, 'static', 'downloads');
  for (const directory of [path.join(root, 'static'), parent, path.join(parent, 'patterns')]) {
    if (await exists(directory) && (await lstat(directory)).isSymbolicLink()) throw new Error(`${directory}: 生成先にシンボリックリンクは使えません。`);
  }
  await mkdir(parent, {recursive: true});
  const stage = await mkdtemp(path.join(parent, '.patterns-'));
  const output = path.join(parent, 'patterns');
  const backup = `${stage}-previous`;
  let backedUp = false;
  try {
    for (const id of ids) {
      const source = path.join(root, 'patterns', id);
      const entries = Object.create(null);
      for (const file of await filesIn(source)) {
        const key = `${path.posix.basename(id)}/${path.relative(source, file).split(path.sep).join('/')}`;
        entries[key] = await readFile(file);
      }
      const archive = zipSync(entries, {level: 6, mtime: new Date('1980-01-01T00:00:00Z')});
      const restored = unzipSync(archive);
      for (const [key, value] of Object.entries(entries)) {
        if (!Buffer.from(restored[key]).equals(value)) throw new Error(`${id}: ZIP収録内容の確認に失敗しました: ${key}`);
      }
      const target = path.join(stage, `${id}.zip`);
      await mkdir(path.dirname(target), {recursive: true});
      await writeFile(target, archive);
    }
    if (await exists(output)) {await rename(output, backup); backedUp = true;}
    try {await rename(stage, output);} catch (error) {if (backedUp) await rename(backup, output); throw error;}
    if (backedUp) await rm(backup, {recursive: true});
  } finally {
    await rm(stage, {recursive: true, force: true});
  }
  return {ids, output};
}

main(import.meta.url, async () => {
  const {ids} = await buildDownloads(cliOptions().root);
  console.log(`ZIP生成: ${ids.length}件。検証対象0件は実パターンの動作確認を意味しません。`);
});
