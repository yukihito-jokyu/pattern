import {test, expect} from '@playwright/test';

test('サブパス配信でPNGを表示する', async ({page}) => {
  await page.goto('/pattern/docs/sample/basic/hello');
  const image = page.getByRole('img', {name: '処理の例'});
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate(img => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(await image.getAttribute('src')).toMatch(/^\/pattern\//);
});
