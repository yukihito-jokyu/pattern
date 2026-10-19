import test from 'node:test';
import assert from 'node:assert/strict';
import { appendFile, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { temporarySite, build } from './helpers/temporary-site.mjs';
test('存在しない記事へのリンクでビルドが失敗する', { timeout: 180000 }, async (t) => { const site = await temporarySite(); t.after(site.cleanup); await appendFile(path.join(site.temp, 'docs/intro.md'), '\n[不正リンク](./missing-document.md)\n'); const result = build(site.temp); assert.notEqual(result.status, 0); assert.match(result.stdout + result.stderr, /missing-document|Broken link/); });
test('検索を無効にしてビルドでき、検索データを生成しない', { timeout: 180000 }, async (t) => { const site = await temporarySite(); t.after(site.cleanup); const f = path.join(site.temp, 'site.settings.json'); const settings = JSON.parse(await readFile(f)); settings.custom.search.enabled = false; await writeFile(f, JSON.stringify(settings)); const result = build(site.temp); assert.equal(result.status, 0, result.stdout + result.stderr); const html = await readFile(path.join(site.temp, 'build/index.html'), 'utf8'); assert.ok(!html.includes('aria-label="文書を検索"')); });
