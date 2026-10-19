import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { temporarySite } from './helpers/temporary-site.mjs';
import { initAnswers, listing, verifyCoverage, validateAnswers, checkManaged, plan, apply, hashes, encode } from '../setup/lib/setup.mjs';
import { execFileSync } from 'node:child_process';
async function fixture(t) { const site = await temporarySite(); t.after(site.cleanup); return site.temp; }
// Test data represents explicit answers; the shipped skill must obtain real answers.
async function confirmed(temp, mutate = () => { }) {
    const answers = await initAnswers(temp);
    mutate(answers.settings);
    const rows = listing(await verifyCoverage(temp), answers.settings);
    for (const row of rows)
        answers.reviews[row.id] = { decision: 'confirmed', values: row.current };
    return answers;
}
test('初期設定と公式スキーマ・台帳が一致し、未回答を拒否する', async (t) => { const temp = await fixture(t); const a = await initAnswers(temp); assert.ok(Object.keys(a.reviews).length > 2000); await assert.rejects(validateAnswers(a, temp), /未回答/); });
test('台帳の欠落を公式ソースとの照合で検出する', async (t) => { const temp = await fixture(t); const f = path.join(temp, 'setup/settings.catalog.json'); const c = JSON.parse(await fs.readFile(f)); c.entries.pop(); await fs.writeFile(f, encode(c)); await assert.rejects(verifyCoverage(temp), /一致/); });
test('回答を反映し、再実行で同じファイルを変更しない', async (t) => { const temp = await fixture(t); const a = await confirmed(temp, s => { s.site.title = 'チームの手順書'; s.site.baseUrl = '/manual/'; s.custom.search.limit = 5; }); await validateAnswers(a, temp); const preview = await plan(a, temp); assert.ok(preview.changes.some(c => c.file === 'site.settings.json')); await apply(a, temp); assert.equal(JSON.parse(await fs.readFile(path.join(temp, 'site.settings.json'))).site.title, 'チームの手順書'); await checkManaged(temp); const b = await confirmed(temp); assert.deepEqual((await plan(b, temp)).changes, []); });
test('不正値と確認後の変更を拒否し、元ファイルを保つ', async (t) => { const temp = await fixture(t); const before = await hashes(temp, ['site.settings.json']); const a = await confirmed(temp, s => s.custom.search.limit = 0); await assert.rejects(apply(a, temp), /limit/); assert.deepEqual(await hashes(temp, ['site.settings.json']), before); const b = await confirmed(temp); b.settings.site.title = '未確認の変更'; await assert.rejects(validateAnswers(b, temp), /確認した値/); });
test('未設定とfalseを区別し、手編集・古い回答・パス逸脱を拒否する', async (t) => { const temp = await fixture(t); const a = await confirmed(temp, s => { delete s.site.tagline; s.custom.search.enabled = false; }); await apply(a, temp); const s = JSON.parse(await fs.readFile(path.join(temp, 'site.settings.json'))); assert.equal(Object.hasOwn(s.site, 'tagline'), false); assert.equal(s.custom.search.enabled, false); await assert.rejects(apply(a, temp), /変更されています/); await fs.appendFile(path.join(temp, 'tsconfig.json'), ' '); await assert.rejects(initAnswers(temp), /手編集/); });
test('反映途中の失敗は全ファイルを復元する', async (t) => { const temp = await fixture(t); const a = await confirmed(temp, s => { s.site.title = '復元検証'; s.typescript.compilerOptions.strict = false; }); const files = Object.keys(a.base); const before = await hashes(temp, files); await assert.rejects(apply(a, temp, { failAfter: 2 }), /反映失敗/); assert.deepEqual(await hashes(temp, files), before); await checkManaged(temp); });
test('記事本文を保持してfront matterだけを変更する', async (t) => { const temp = await fixture(t); const a = await confirmed(temp, s => s.documents['docs/intro.md'].title = '入門資料'); const file = path.join(temp, 'docs/intro.md'); const before = (await fs.readFile(file, 'utf8')).split('\n---\n')[1]; await apply(a, temp); const after = await fs.readFile(file, 'utf8'); assert.ok(after.includes('title: 入門資料')); assert.equal(after.split('\n---\n')[1], before); });
test('サイト外の文書と不正なPlaywright・TypeScript設定を拒否する', async (t) => { const temp = await fixture(t); const a = await confirmed(temp, s => s.documents['../outside.md'] = { title: '外' }); await assert.rejects(validateAnswers(a, temp), /相対パス/); const b = await confirmed(temp, s => s.playwright.workers = 'wrong'); await assert.rejects(validateAnswers(b, temp), /positive number or percentage/); const c = await confirmed(temp, s => s.typescript.compilerOptions.noSuchSetting = true); await assert.rejects(validateAnswers(c, temp), /Unknown compiler option/); });
test('本文の追記を許可し、ローカル関数を設定へ渡せる', async (t) => { const temp = await fixture(t); const a = await confirmed(temp); await apply(a, temp); await fs.appendFile(path.join(temp, 'docs/intro.md'), '\n本文の追記。\n'); await checkManaged(temp); await fs.writeFile(path.join(temp, 'handler.cjs'), 'exports.edit = () => "https://example.com/edit";'); const b = await confirmed(temp, s => s.preset.docs.editUrl = { $module: './handler.cjs', export: 'edit' }); await validateAnswers(b, temp); });

test('初回の回答後の記事変更を検出し、全記事のメタデータを管理する', async t => {
    const temp = await fixture(t);
    const a = await confirmed(temp);
    const file = path.join(temp, 'docs/intro.md');
    const original = await fs.readFile(file, 'utf8');
    await fs.appendFile(file, '\n回答後の変更。\n');
    await assert.rejects(apply(a, temp), /変更されています/);
    await fs.writeFile(file, original);
    await apply(a, temp);
    await fs.writeFile(file, original.replace('title: はじめに', 'title: 手編集'));
    await assert.rejects(checkManaged(temp), /手編集/);
});

async function answerSelected(temp, level = 'important', mutate = () => {}) {
    const answers = await initAnswers(temp, { level });
    mutate(answers.settings);
    for (const row of listing(await verifyCoverage(temp), answers.settings)) {
        if (answers.reviews[row.id].decision === 'unanswered')
            answers.reviews[row.id] = { decision: 'confirmed', values: row.current };
    }
    return answers;
}
test('重要のみで導入でき、範囲外の現在値と未設定を反映後も維持する', async t => {
    const temp = await fixture(t);
    const answers = await answerSelected(temp, 'important', s => { s.site.title = '重要項目の設定'; s.theme.navbar.title = '重要項目の設定'; });
    const original = JSON.parse(await fs.readFile(path.join(temp, 'site.settings.json')));
    assert.ok(Object.values(answers.reviews).some(r => r.decision === 'retained'));
    const preview = await plan(answers, temp);
    assert.equal(preview.questionLevel, 'important');
    assert.ok(preview.retainedEntries > 2000);
    await apply(answers, temp);
    const saved = JSON.parse(await fs.readFile(path.join(temp, 'site.settings.json')));
    assert.deepEqual(saved.typescript, original.typescript);
    assert.deepEqual(saved.playwright, original.playwright);
    assert.equal(Object.hasOwn(saved.site, 'scripts'), false);
});
test('省略項目の変更と維持値の改ざんを拒否し、個別確認すれば変更できる', async t => {
    const temp = await fixture(t);
    const answers = await answerSelected(temp);
    answers.settings.custom.search.limit = 3;
    await assert.rejects(validateAnswers(answers, temp), /質問範囲外の変更/);
    const rows = listing(await verifyCoverage(temp), answers.settings).filter(r => r.path === 'custom.search.limit');
    for (const row of rows) answers.reviews[row.id] = { decision: 'confirmed', values: row.current };
    await validateAnswers(answers, temp);
    const retained = Object.values(answers.reviews).find(r => r.decision === 'retained');
    retained.values = ['改ざん'];
    await assert.rejects(validateAnswers(answers, temp), /維持する項目/);
});
test('重要項目を維持扱いで飛ばせず、普通・全項目の範囲を段階的に選べる', async t => {
    const temp = await fixture(t);
    const important = await initAnswers(temp);
    const normal = await initAnswers(temp, { level: 'normal' });
    const all = await initAnswers(temp, { level: 'advanced' });
    const count = a => Object.values(a.reviews).filter(r => r.decision === 'unanswered').length;
    assert.ok(count(important) < count(normal));
    assert.ok(count(normal) < count(all));
    assert.equal(count(all), Object.keys(all.reviews).length);
    const rows = listing(await verifyCoverage(temp), important.settings);
    assert.equal(new Set(rows.filter(r => r.importance === 'important').map(r => r.path)).size, 12);
    assert.ok(rows.every(r => r.importanceReason));
    const row = rows.find(r => r.path === 'site.url');
    important.reviews[row.id] = { decision: 'retained', values: row.current, reason: '省略したい' };
    await assert.rejects(validateAnswers(important, temp), /未回答|維持する項目/);
    await assert.rejects(initAnswers(temp, { level: 'unknown' }), /質問範囲/);
});
test('CLIは選んだ範囲と回答中の最新値で一覧を絞り、全台帳も参照できる', async t => {
    const temp = await fixture(t);
    const cli = (...args) => JSON.parse(execFileSync(process.execPath, [path.join(temp, 'scripts/setup.mjs'), ...args], { cwd: temp, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 }));
    const info = cli('init', '--level', 'important', '--out', 'answers.json');
    assert.equal(info.questionPaths, 12);
    const answers = JSON.parse(await fs.readFile(path.join(temp, 'answers.json')));
    answers.settings.site.title = '回答中のサイト名';
    await fs.writeFile(path.join(temp, 'answers.json'), encode(answers));
    const selected = cli('list', '--answers', 'answers.json');
    assert.ok(selected.every(r => r.importance === 'important'));
    assert.deepEqual(selected.find(r => r.path === 'site.title').current, ['回答中のサイト名']);
    assert.ok(cli('list', '--level', 'advanced').length > selected.length);
});
