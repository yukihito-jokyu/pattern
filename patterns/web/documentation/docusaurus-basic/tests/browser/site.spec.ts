import {test,expect} from '@playwright/test';
test('ホームから文書へ移動し、記事・コード・画像・相対リンクを読む',async({page})=>{
  await page.goto('./');await page.getByRole('link',{name:'ドキュメントを読む',exact:true}).click();await expect(page).toHaveURL(/\/preview\/docs\/intro$/);
  await page.getByRole('main').getByRole('link',{name:'記事を書く',exact:true}).first().click();await expect(page.getByRole('heading',{name:'記事を書く',exact:true})).toBeVisible();
  await expect(page.locator('pre').first()).toContainText('チームの手順書');const image=page.getByRole('img',{name:/公開までの流れ/});await expect(image).toBeVisible();await expect(image).toHaveJSProperty('naturalWidth',900);
  await page.getByRole('main').getByRole('link',{name:'サイトを設定する',exact:true}).first().click();await expect(page).toHaveURL(/\/preview\/docs\/guide\/configuration$/);
});
test('検索で追加記事を見つけ、キー操作で移動・復帰する',async({page})=>{
  await page.goto('./');await page.getByRole('button',{name:'文書を検索',exact:true}).click();const input=page.getByRole('combobox');await input.fill('追加反映専用');await expect(page.getByRole('option')).toContainText('追加した記事');await input.press('ArrowDown');await input.press('Enter');await expect(page).toHaveURL(/\/preview\/docs\/guide\/added$/);
  await page.getByRole('button',{name:'文書を検索',exact:true}).click();await input.fill('非公開専用');await expect(page.getByRole('option')).toHaveCount(0);await input.press('Escape');await expect(page.getByRole('button',{name:'文書を検索',exact:true})).toBeFocused();
});
test('モバイルでも文書を読み、ライト・ダークを切り替える',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('./docs/guide/writing');await expect(page.getByRole('heading',{name:'記事を書く',exact:true})).toBeVisible();await expect(page.locator('html')).toHaveAttribute('lang','ja');
  await page.emulateMedia({colorScheme:'dark'});await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});
