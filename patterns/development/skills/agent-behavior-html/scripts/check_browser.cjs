"use strict";

// Optional real-browser verification. Runtime users do not need Playwright.
// node scripts/check_browser.cjs [playwright-package] [chromium-executable]
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const playwright = require(process.argv[2] || "playwright");
const root = path.resolve(__dirname, "..");
const output = path.join(root, ".foundation/browser-validation");

async function main() {
  fs.mkdirSync(output, {recursive:true});
  const browser = await playwright.chromium.launch({
    headless:true,
    ...(process.argv[3] ? {executablePath:process.argv[3]} : {}),
  });
  const errors = [], requests = [];
  const context = await browser.newContext({viewport:{width:1440,height:1000}, acceptDownloads:true});
  const page = await context.newPage();
  page.on("pageerror", error => errors.push(String(error)));
  page.on("request", request => {if (/^https?:/.test(request.url())) requests.push(request.url());});
  try {
    await page.goto(pathToFileURL(path.join(root, "examples/demo.html")).href);
    await page.locator("#calls").waitFor();
    assert.equal(await page.locator("#calls").textContent(), "12");
    assert.equal(await page.locator("#errors").textContent(), "2");
    assert.equal(await page.locator("#call-rows tr").count(), 12);
    assert.equal(await page.locator(".action-card").count(), 12);
    assert((await page.locator("#action-list").textContent()).includes("認証を通る原因"));
    await page.screenshot({path:path.join(output, "desktop.png"), fullPage:true});
    await page.locator("#source").selectOption("claude");
    assert.equal(await page.locator("#calls").textContent(), "6");
    await page.locator("#tool").selectOption("Bash");
    assert.equal(await page.locator("#calls").textContent(), "3");
    await page.locator("#status").selectOption("error");
    assert.equal(await page.locator("#calls").textContent(), "1");
    await page.getByRole("button", {name:"記録を見る"}).click();
    assert.equal(await page.locator("#evidence-details").getAttribute("open"), "");
    assert((await page.locator("#evidence").textContent()).includes("check-1"));
    const downloadPromise = page.waitForEvent("download");
    await page.locator("#export").click();
    const download = await downloadPromise;
    const exported = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
    assert.equal(exported.calls.length, 1);
    assert.equal(exported.events.length, 2);
    await page.locator("#status").selectOption("");
    await page.locator("#search").fill("check-2");
    assert.equal(await page.locator("#calls").textContent(), "1");
    await page.locator("#session").selectOption(JSON.stringify(["codex","demo-codex"]));
    assert.equal(await page.locator("#calls").textContent(), "0");
    assert((await page.locator("#call-rows").textContent()).includes("ありません"));
    await page.reload();
    await page.locator("#timezone").selectOption("UTC");
    assert((await page.locator("#call-rows td").first().textContent()).includes("00:00"));
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(output, "mobile.png"), fullPage:true});
    const widths = await page.evaluate(() => ({viewport:innerWidth, document:document.documentElement.scrollWidth}));
    assert(widths.document <= widths.viewport, "page must fit a narrow viewport");
    assert.deepEqual(errors, [], "no browser JavaScript errors");
    assert.deepEqual(requests, [], "standalone report must make no network requests");
    const result = {status:"passed", browser:await browser.version(), desktop:{width:1440,height:1000},
      mobile:{width:390,height:844}, checks:["render","filters","evidence","download","empty","timezone","responsive","offline"],
      page_errors:errors, external_requests:requests};
    fs.writeFileSync(path.join(output, "result.json"), JSON.stringify(result,null,2)+"\n");
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}

main().catch(error => {console.error(error);process.exitCode=1;});
