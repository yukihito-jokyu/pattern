import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { readFile, mkdir } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';
const { values } = parseArgs({ options: { output: { type: 'string' } } });
if (!values.output) throw Error('--outputでPNGの出力先を指定してください。');
const site = path.resolve(fileURLToPath(new URL('../build/', import.meta.url)));
const output = path.resolve(values.output);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };
const server = http.createServer(async (req, res) => {
    try {
        const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
        let file = path.resolve(site, '.' + pathname);
        if (!file.startsWith(site + path.sep) && file !== site)
            throw Error('path');
        if (!path.extname(file))
            file = path.join(file, 'index.html');
        res.setHeader('Content-Type', types[path.extname(file)] ?? 'application/octet-stream');
        res.end(await readFile(file));
    }
    catch {
        res.statusCode = 404;
        res.end('Not found');
    }
});
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(4188, '127.0.0.1', resolve); });
let browser;
try {
    await mkdir(output, { recursive: true });
    browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1, colorScheme: 'light', locale: 'ja-JP' });
    const page = await context.newPage();
    await page.goto('http://127.0.0.1:4188/', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: '知識と手順を、読める形に。' })).toBeVisible();
    await page.screenshot({ path: path.join(output, 'home-desktop.png') });
    await page.goto('http://127.0.0.1:4188/docs/guide/writing', { waitUntil: 'networkidle' });
    await expect(page.getByRole('img', { name: /公開までの流れ/ })).toHaveJSProperty('naturalWidth', 900);
    await page.screenshot({ path: path.join(output, 'document-desktop.png') });
    await page.getByRole('button', { name: '文書を検索', exact: true }).click();
    await page.getByRole('combobox').fill('設定');
    await expect(page.getByRole('option').first()).toBeVisible();
    await page.screenshot({ path: path.join(output, 'search-results.png') });
    await page.getByRole('combobox').press('Escape');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'document-mobile.png'), fullPage: true });
    console.log('画面PNGを4枚撮影: ' + output);
}
finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
}
