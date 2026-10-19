import {test, expect} from '@playwright/test';

test('ヘッダー・サイドバーから対象文書へ移動する', async ({page}, testInfo) => {
  await page.goto('/pattern/');
  await page.screenshot({path: testInfo.outputPath('home.png'), fullPage: true});
  await page.getByRole('navigation').getByRole('link', {name: 'ドキュメント', exact: true}).click();
  const sidebar = page.locator('aside');
  for (const label of ['sample', 'basic']) {
    await sidebar.getByRole('button', {name: new RegExp(label)}).click();
  }
  await sidebar.getByRole('link', {name: 'Helloのパターン'}).click();
  await expect(page).toHaveURL(/\/pattern\/docs\/sample\/basic\/hello/);
  await expect(page.locator('article')).toContainText('Hello, world!');
});
