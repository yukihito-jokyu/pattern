import {test, expect} from '@playwright/test';

test('文書から生成された紹介カードで画像・説明・ZIPへ移動できる', async ({page}) => {
  await page.goto('/pattern/');
  const card = page.getByRole('article').filter({has: page.getByRole('heading', {name: 'Helloのパターン'})});
  await expect(card).toContainText('管理基盤のテスト専用サンプル。');
  await expect(card).toContainText('共通機能の確認');
  const image = card.getByRole('img', {name: '一覧の画面例'});
  await expect.poll(() => image.evaluate(element => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(await image.getAttribute('src')).toMatch(/^\/pattern\//);
  await expect(card.getByRole('link', {name: /実装をダウンロード/})).toHaveAttribute('href', '/pattern/downloads/patterns/sample/basic/hello.zip');
  await card.getByRole('link', {name: '詳しい説明を読む'}).click();
  await expect(page).toHaveURL(/\/pattern\/docs\/sample\/basic\/hello$/);
});
