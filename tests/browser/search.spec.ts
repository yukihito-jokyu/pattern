import {test, expect} from '@playwright/test';

test('検索結果をキーボードで選び、対象ページへ移動する', async ({page}) => {
  await page.goto('/preview/');
  await page.getByRole('button', {name: '文書を検索'}).click();
  const input = page.getByRole('combobox', {name: '検索キーワード'});
  await input.fill('Hello');
  await expect(page.getByRole('option').first()).toContainText('Helloのパターン');
  await input.press('ArrowDown');
  await input.press('Enter');
  await expect(page).toHaveURL(/\/preview\/docs\/sample\/basic\/hello/);
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('該当なしを表示し、Escで閉じてフォーカスを戻す', async ({page}) => {
  await page.goto('/preview/');
  const trigger = page.getByRole('button', {name: '文書を検索'});
  await trigger.click();
  const input = page.getByRole('combobox', {name: '検索キーワード'});
  await input.fill('該当しない文書名');
  await expect(page.getByRole('dialog')).toContainText('一致する文書はありません');
  await input.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(trigger).toBeFocused();
});
