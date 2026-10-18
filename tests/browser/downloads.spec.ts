import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {unzipSync} from 'fflate';

test('文書から対応ZIPをダウンロードし、内容まで確認する', async ({page}) => {
  await page.goto('/preview/docs/sample/basic/hello');
  await expect(page.getByRole('link', {name: '実装をダウンロード'})).toHaveAttribute('href', /^\/preview\//);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('link', {name: '実装をダウンロード'}).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/^hello(?:-[a-f0-9]+)?\.zip$/);
  const file = await download.path();
  const entries = unzipSync(await readFile(file!));
  expect(Object.keys(entries)).toContain('hello/README.md');
  expect(Buffer.from(entries['hello/hello.mjs']).toString()).toContain('Hello, ${name}!');
  expect(Object.keys(entries)).toContain('hello/hello.test.mjs');
});
