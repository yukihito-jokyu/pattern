import { test, expect } from "@playwright/test";
// 実際のCSS transitionを途中へ進めて止める。時間待ちの揺れを避け、補間そのものを観測する。
async function disclosureAt(page, action, progress) {
  return page.evaluate(({action,progress}) => {
    const panel=document.getElementById("panel");
    const target=document.getElementById(action === "close" ? "close" : "open");
    target.focus({preventScroll:true}); target.click();
    const animations=panel.getAnimations();
    for (const animation of animations) {
      animation.pause(); animation.currentTime=animation.effect.getTiming().duration*progress;
    }
    return {animations:animations.length,height:panel.getBoundingClientRect().height,full:panel.firstElementChild.scrollHeight,opacity:Number(getComputedStyle(panel).opacity),inert:panel.inert,expanded:document.getElementById("open").getAttribute("aria-expanded")};
  },{action,progress});
}
async function finishDisclosure(page) {
  await page.locator("#panel").evaluate((el) => { for (const animation of el.getAnimations()) animation.finish(); });
}
test.beforeEach(async ({page}) => { await page.goto("/"); await expect(page.locator("#effective")).toContainText("ON"); });
test("STATE-01: save response is semantic and keeps input through failure and retry",async ({page}) => {
  await page.locator("#note").fill("変更したメモ");
  await page.locator("#result").selectOption("error");
  await page.locator("#save").click();
  await expect(page.locator("#save-status")).toHaveText("保存中");
  await expect(page.locator("#save")).toBeDisabled();
  await expect(page.locator("#save-status")).toContainText("保存できませんでした");
  await expect(page.locator("#note")).toHaveValue("変更したメモ");
  await page.locator("#result").selectOption("success");
  await page.locator("#save").click();
  await expect(page.locator("#save-status")).toHaveText("保存しました");
});
test("MOT-03: priority, mid-flight OFF, resume and OS reduction",async ({page}) => {
  await page.locator("#parent").selectOption("off");
  await expect(page.locator("#effective")).toContainText("OFF");
  await page.locator("#local").selectOption("on");
  await expect(page.locator("#effective")).toContainText("ON");
  await page.locator('[data-choice="2"]').click();
  await page.locator("#local").selectOption("off");
  expect(await page.locator("#indicator").evaluate((el) => el.getAnimations().length)).toBe(0);
  await expect(page.locator('[data-choice="2"]')).toHaveAttribute("aria-pressed","true");
  await page.locator("#local").selectOption("on");
  expect(await page.locator("#indicator").evaluate((el) => el.getAnimations().length)).toBe(0);
  await page.emulateMedia({reducedMotion:"reduce"});
  await expect(page.locator("#effective")).toContainText("OS");
  await page.locator('[data-choice="0"]').click();
  expect(await page.locator("#indicator").evaluate((el) => el.getAnimations().length)).toBe(0);
  await page.emulateMedia({reducedMotion:"no-preference"});
  await expect(page.locator("#effective")).toContainText("ON");
  await disclosureAt(page,"toggle",.4);
  await page.locator("#local").selectOption("off");
  expect(await page.locator("#panel").evaluate((el) => el.getAnimations().length)).toBe(0);
  expect(await page.locator("#panel").evaluate((el) => el.getBoundingClientRect().height)).toBeGreaterThan(0);
  await page.locator("#local").selectOption("on");
  expect(await page.locator("#panel").evaluate((el) => el.getAnimations().length)).toBe(0);
  await disclosureAt(page,"close",.4);
  await page.emulateMedia({reducedMotion:"reduce"});
  await expect(page.locator("#effective")).toContainText("OS");
  expect(await page.locator("#panel").evaluate((el) => el.getBoundingClientRect().height)).toBe(0);
  await page.emulateMedia({reducedMotion:"no-preference"});
  expect(await page.locator("#panel").evaluate((el) => el.getAnimations().length)).toBe(0);
});
test("ASYNC-01: retarget starts at visible position and latest selection wins",async ({page}) => {
  const errors=[];page.on("pageerror",(error) => errors.push(error.message));
  const positions = await page.evaluate(async () => {
    document.querySelector('[data-choice="2"]').click();
    await new Promise((resolve) => setTimeout(resolve,70));
    const el=document.getElementById("indicator");
    const before=el.getBoundingClientRect().x;
    document.querySelector('[data-choice="1"]').click();
    return {before,after:el.getBoundingClientRect().x};
  });
  expect(Math.abs(positions.before-positions.after)).toBeLessThan(2);
  await expect(page.locator('[data-choice="1"]')).toHaveAttribute("aria-pressed","true");
  await page.waitForTimeout(350);
  const delta=await page.evaluate(() => document.getElementById("indicator").getBoundingClientRect().x-document.querySelector('[data-choice="1"]').getBoundingClientRect().x);
  expect(Math.abs(delta)).toBeLessThan(2);expect(errors).toEqual([]);
});
test("MOT-05: both directions visibly interpolate while the next action and focus remain available",async ({page}) => {
  const opening=await disclosureAt(page,"toggle",.4);
  expect(opening.animations).toBeGreaterThan(0);
  expect(opening.height).toBeGreaterThan(1); expect(opening.height).toBeLessThan(opening.full-1);
  expect(opening.opacity).toBeGreaterThan(0); expect(opening.opacity).toBeLessThan(1);
  expect(opening.expanded).toBe("true"); expect(opening.inert).toBe(false);
  await finishDisclosure(page);
  await page.locator("#details-note").fill("次も残す入力");
  const closing=await disclosureAt(page,"close",.4);
  expect(closing.animations).toBeGreaterThan(0);
  expect(closing.height).toBeGreaterThan(1); expect(closing.height).toBeLessThan(closing.full-1);
  expect(closing.opacity).toBeGreaterThan(0); expect(closing.opacity).toBeLessThan(1);
  expect(closing.expanded).toBe("false"); expect(closing.inert).toBe(true);
  await expect(page.locator("#open")).toBeFocused();
  await page.locator("#next-action").click();
  await expect(page.locator("#next-status")).toHaveText("次の操作を受け付けました（1回）");
  expect(await page.locator("#panel").evaluate((el) => el.getBoundingClientRect().height)).toBeCloseTo(closing.height,0);
  await finishDisclosure(page);
  expect(await page.locator("#panel").evaluate((el) => el.getBoundingClientRect().height)).toBe(0);
  await expect(page.locator("#details-note")).toHaveValue("次も残す入力");
});
test("MOT-05: repeated reversals continue from the visible size without jumping to an endpoint",async ({page}) => {
  const errors=[];page.on("pageerror",(error) => errors.push(error.message));
  const opening=await disclosureAt(page,"toggle",.35);
  expect(opening.height).toBeGreaterThan(1); expect(opening.height).toBeLessThan(opening.full-1);
  const reversals=await page.evaluate(() => {
    const panel=document.getElementById("panel");const result=[];
    for(let i=0;i<4;i++) {
      const before=panel.getBoundingClientRect().height;
      document.getElementById("open").click();
      const after=panel.getBoundingClientRect().height;
      const animations=panel.getAnimations();
      for(const animation of animations) { animation.pause();animation.currentTime=animation.effect.getTiming().duration*.3; }
      result.push({before,after,progressHeight:panel.getBoundingClientRect().height,expanded:document.getElementById("open").getAttribute("aria-expanded"),inert:panel.inert,animations:animations.length});
    }
    return result;
  });
  for(const [index,reversal] of reversals.entries()) {
    expect(reversal.animations).toBeGreaterThan(0);
    expect(Math.abs(reversal.before-reversal.after)).toBeLessThan(1);
    expect(reversal.expanded).toBe(String(index%2 === 1));
    expect(reversal.inert).toBe(index%2 === 0);
    if(index%2 === 0) expect(reversal.progressHeight).toBeLessThan(reversal.before);
    else expect(reversal.progressHeight).toBeGreaterThan(reversal.before);
  }
  await finishDisclosure(page);
  await expect(page.locator("#open")).toHaveAttribute("aria-expanded","true");
  expect(await page.locator("#panel").evaluate((el) => el.inert)).toBe(false);
  expect(errors).toEqual([]);
});
test("new-york does not expose cobalt props; keyboard and narrow layout remain usable",async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.locator("#system").selectOption("new-york");
  await expect(page.locator("#local")).toBeDisabled();
  await page.locator("#open").focus();await page.keyboard.press("Enter");
  await expect(page.locator("#open")).toBeFocused();
  await page.keyboard.press("Enter");await expect(page.locator("#open")).toBeFocused();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");await expect(page.locator("#next-action")).toBeFocused();
  await page.keyboard.press("Tab");await expect(page.locator("#details-note")).toBeFocused();
  await page.keyboard.press("Escape");await expect(page.locator("#open")).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
test("MOT-04: optional delight follows success once and never replays on ON",async ({page}) => {
  await page.evaluate(() => {
    window.celebrations = 0;
    const mark=document.getElementById("success-mark");
    const animate=mark.animate.bind(mark);
    mark.animate=(...args) => {window.celebrations++; return animate(...args);};
  });
  await page.locator("#delight").check();
  await page.locator("#save").click();
  await expect(page.locator("#save-status")).toHaveText("保存しました");
  expect(await page.evaluate(() => window.celebrations)).toBe(1);
  await page.locator("#local").selectOption("off");
  await page.locator("#local").selectOption("on");
  expect(await page.locator("#success-mark").evaluate((el) => el.getAnimations().length)).toBe(0);
  await page.locator("#save").click();
  await expect(page.locator("#save-status")).toHaveText("保存しました");
  expect(await page.locator("#success-mark").evaluate((el) => el.getAnimations().length)).toBe(0);
  expect(await page.evaluate(() => window.celebrations)).toBe(1);
});
