import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { collectCatalog, coverageOf } from './catalog.mjs';
import { schemas, digest, require } from './surfaces.mjs';
import { hydrate } from './runtime.cjs';
import { assertQuestionLevel, includesQuestion, changedPaths, coversPath } from './question-levels.mjs';
const ts = require('typescript');
const { parseDocument, stringify } = require('yaml');
export const root = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const json = async (file) => JSON.parse(await fs.readFile(file, 'utf8'));
export const encode = value => JSON.stringify(value, null, 2) + '\n';
export async function safeFile(base, relative) {
    if (typeof relative !== 'string' || path.isAbsolute(relative) || relative.split(/[\\/]/).includes('..'))
        throw Error(`サイト内の相対パスが必要です: ${relative}`);
    const target = path.resolve(base, relative);
    if (!target.startsWith(path.resolve(base) + path.sep))
        throw Error('サイト外へは書き込めません。');
    let current = path.resolve(base);
    for (const part of path.relative(base, target).split(path.sep)) {
        current = path.join(current, part);
        try {
            if ((await fs.lstat(current)).isSymbolicLink())
                throw Error(`シンボリックリンクは対象外です: ${relative}`);
        }
        catch (e) {
            if (e.code !== 'ENOENT')
                throw e;
        }
    }
    return target;
}
export async function verifyCoverage(base = root) {
    const expected = collectCatalog();
    const actual = await json(path.join(base, 'setup/settings.catalog.json'));
    if (JSON.stringify(actual) !== JSON.stringify(expected) || JSON.stringify(await json(path.join(base, 'setup/coverage.json'))) !== JSON.stringify(coverageOf(expected)))
        throw Error('設定台帳・OSSの版・網羅性が一致しません。出典を確認して台帳を更新してください。');
    if (new Set(actual.entries.map(e => e.id)).size !== actual.entries.length)
        throw Error('台帳IDが重複しています。');
    return actual;
}
async function manifest(base) {
    try {
        return await json(path.join(base, '.setup-state.json'));
    }
    catch (e) {
        if (e.code !== 'ENOENT')
            throw e;
        return json(path.join(base, 'setup/managed-files.json'));
    }
}
export async function hashes(base, files, { metadataOnly = false } = {}) {
    return Object.fromEntries(await Promise.all(files.map(async (file) => {
        const p = await safeFile(base, file);
        try {
            let content = await fs.readFile(p, 'utf8');
            if (metadataOnly && /\.mdx?$/.test(file))
                content = JSON.stringify(parseDocument(content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1] ?? '').toJSON());
            return [file, digest(content)];
        }
        catch (e) {
            if (e.code === 'ENOENT')
                return [file, null];
            throw e;
        }
    })));
}
export async function checkManaged(base = root) {
    const state = await manifest(base);
    const actual = await hashes(base, Object.keys(state), { metadataOnly: true });
    const conflicts = Object.keys(state).filter(f => state[f] !== actual[f]);
    if (conflicts.length)
        throw Error(`管理ファイルに手編集があります。差分を回答へ取り込むか元に戻してください: ${conflicts.join(', ')}`);
    return state;
}
async function readSettings(base) {
    const settings = await json(path.join(base, 'site.settings.json'));
    const docsPath = typeof settings.preset.docs === 'object' ? settings.preset.docs.path ?? 'docs' : 'docs';
    const dir = await safeFile(base, docsPath);
    const docs = {};
    const categories = {};
    async function walk(folder) {
        for (const entry of await fs.readdir(folder, { withFileTypes: true })) {
            const absolute = path.join(folder, entry.name);
            const relative = path.relative(base, absolute).split(path.sep).join('/');
            if (entry.isSymbolicLink())
                throw Error('記事のシンボリックリンクは対象外です。');
            if (entry.isDirectory())
                await walk(absolute);
            else if (/\.mdx?$/.test(entry.name)) {
                const text = await fs.readFile(absolute, 'utf8');
                const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
                const parsed = match ? parseDocument(match[1]) : null;
                if (parsed?.errors.length)
                    throw Error(`${relative}: YAMLが不正です。`);
                docs[relative] = { ...(parsed?.toJSON() ?? {}), ...(settings.documents[relative] ?? {}) };
            }
            else if (entry.name === '_category_.json')
                categories[relative] = { ...await json(absolute), ...(settings.categories[relative] ?? {}) };
        }
    }
    try {
        await walk(dir);
    }
    catch (e) {
        if (e.code !== 'ENOENT')
            throw e;
    }
    return {
        ...settings, documents: { ...docs, ...settings.documents }, categories: { ...categories, ...settings.categories }
    };
}
async function inputFiles(base, settings) {
    return [...new Set([
        ...Object.keys(await manifest(base)),
        ...Object.keys(settings.documents),
        ...Object.keys(settings.categories),
    ])];
}
export async function initAnswers(base = root, { level = 'important' } = {}) {
    assertQuestionLevel(level);
    await checkManaged(base);
    const catalog = await verifyCoverage(base);
    const settings = await readSettings(base);
    return {
        version: 1,
        questionLevel: level,
        base: await hashes(base, await inputFiles(base, settings)),
        settings,
        reviews: Object.fromEntries(listing(catalog, settings).map(e => [e.id, {
            decision: includesQuestion(level, e.importance) ? 'unanswered' : 'retained', values: structuredClone(e.current),
            ...(!includesQuestion(level, e.importance) ? { reason: '選択した質問範囲の対象外。現在値・未設定時の既定動作を維持する。' } : {})
        }])),
    };
}

function getValue(settings, p) {
    let values = [settings];
    for (const token of p.replace(/\[\]/g, '.[]').split('.'))
        values = values.flatMap(v => token === '*' ? Object.values(v ?? {}) : token === '[]' ? (Array.isArray(v) ? v : []) : v && Object.hasOwn(v, token) ? [v[token]] : []);
    return values;
}
export function listing(catalog, settings) {
    return catalog.entries.map(e => ({
        ...e, current: getValue(settings, e.path), state: getValue(settings, e.path).length ? '設定済み' : '未設定', ...(e.path === 'site.baseUrl' ? { effective: process.env.SITE_BASE_URL ?? settings.site.baseUrl ?? '/' } : {})
    }));
}
function tsDiagnostics(settings, base) {
    const parsed = ts.parseJsonConfigFileContent(structuredClone(settings.typescript), ts.sys, base);
    const errors = parsed.errors.filter(e => e.code !== 18003); // No inputs is checked by actual typecheck.
    const virtual = path.join(base, 'setup-input.ts');
    function expression(value) {
        if (Array.isArray(value))
            return '[' + value.map(expression).join(',') + ']';
        if (value && typeof value === 'object') {
            if (value.$module)
                return `(await import(${JSON.stringify(value.$module)}))[${JSON.stringify(value.export ?? 'default')}]`;
            return '{' + Object.entries(value).map(([k, v]) => JSON.stringify(k) + ':' + expression(v)).join(',') + '}';
        }
        return JSON.stringify(value);
    }
    const content = `import type {PlaywrightTestConfig} from '@playwright/test';\nconst config: PlaywrightTestConfig = ${expression(settings.playwright)};\n`;
    const host = ts.createCompilerHost({
        strict: true, allowJs: true, skipLibCheck: true, moduleResolution: ts.ModuleResolutionKind.Bundler, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, noEmit: true
    });
    const originalRead = host.readFile, originalExists = host.fileExists;
    host.readFile = f => f === virtual ? content : originalRead(f);
    host.fileExists = f => f === virtual || originalExists(f);
    const program = ts.createProgram([virtual], {
        strict: true, allowJs: true, skipLibCheck: true, moduleResolution: ts.ModuleResolutionKind.Bundler, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, noEmit: true
    }, host);
    errors.push(...ts.getPreEmitDiagnostics(program));
    return errors.map(e => ts.flattenDiagnosticMessageText(e.messageText, '\n'));
}
export async function validateSettings(settings, base = root) {
    if (!settings || typeof settings !== 'object' || Array.isArray(settings))
        throw Error('settingsはオブジェクトです。');
    const required = ['site', 'preset', 'theme', 'sidebar', 'documents', 'categories', 'typescript', 'playwright', 'custom'];
    if (Object.keys(settings).some(k => !required.includes(k)) || required.some(k => !settings[k] || typeof settings[k] !== 'object' || Array.isArray(settings[k])))
        throw Error('settingsの区分が不正です。');
    const resolved = hydrate(settings, base);
    const sc = schemas();
    function validate(schema, value, label) {
        const { error } = schema.validate(value, { abortEarly: false, convert: false });
        if (error)
            throw Error(`${label}: ${error.message}`);
    }
    validate(sc.site, resolved.site, 'site');
    validate(sc.theme, resolved.theme, 'theme');
    validate(sc.custom, resolved.custom, 'custom');
    const presetKeys = ['debug', 'docs', 'blog', 'pages', 'sitemap', 'svgr', 'theme', 'googleAnalytics', 'gtag', 'googleTagManager'];
    if (Object.keys(resolved.preset).some(k => !presetKeys.includes(k)))
        throw Error('presetに未知のキーがあります。');
    for (const [k, v] of Object.entries(resolved.preset)) {
        if (k === 'debug') {
            if (typeof v !== 'boolean')
                throw Error('debugはbooleanです。');
            continue;
        }
        if (v === false && ['docs', 'blog', 'pages', 'sitemap', 'svgr'].includes(k))
            continue;
        validate(sc['preset.' + k], v, 'preset.' + k);
    }
    const { validateSidebars } = require('@docusaurus/plugin-content-docs/lib/sidebars/validation.js');
    validateSidebars(resolved.sidebar);
    for (const [k, v] of Object.entries(resolved.documents)) {
        await safeFile(base, k);
        if (!/\.mdx?$/.test(k))
            throw Error('記事はmd/mdxを指定してください。');
        validate(sc['documents.*'], v, k);
    }
    for (const [k, v] of Object.entries(resolved.categories)) {
        await safeFile(base, k);
        if (!k.endsWith('/_category_.json'))
            throw Error('カテゴリは_category_.jsonを指定してください。');
        validate(sc['categories.*'], v, k);
    }
    const baseUrl = process.env.SITE_BASE_URL ?? settings.site.baseUrl ?? '/';
    if (typeof baseUrl !== 'string' || !/^\/(?:[^?#\\]*\/)?$/.test(baseUrl) || baseUrl.includes('//') || baseUrl.split('/').includes('..'))
        throw Error('baseUrlは前後/付きのパスです。');
    if (settings.site.customFields && Object.hasOwn(settings.site.customFields, 'pattern'))
        throw Error('customFields.patternはcustomから生成します。');
    for (const p of [settings.playwright, ...(settings.playwright.projects ?? [])]) {
        if (p.workers !== undefined && !(Number.isInteger(p.workers) && p.workers > 0) && !(typeof p.workers === 'string' && /^[1-9][0-9]*%$/.test(p.workers)))
            throw Error('workers must be a positive number or percentage');
    }
    const errors = tsDiagnostics(settings, base);
    if (errors.length)
        throw Error(errors.join('\n'));
    return resolved;
}
export async function validateAnswers(answers, base = root) {
    if (answers.version !== 1)
        throw Error('回答ファイルのversionが不正です。');
    const catalog = await verifyCoverage(base);
    const ids = new Set(catalog.entries.map(e => e.id));
    if (Object.keys(answers.reviews ?? {}).some(id => !ids.has(id)))
        throw Error('未知の回答項目があります。');
    const listingRows = listing(catalog, answers.settings);
    const current = await readSettings(base);
    // Legacy answer files required every entry to be reviewed.
    const level = assertQuestionLevel(answers.questionLevel ?? 'advanced');
    for (const row of listingRows) {
        const review = answers.reviews?.[row.id];
        if (review?.decision === 'retained') {
            if (includesQuestion(level, row.importance) || !review.reason?.trim() ||
                JSON.stringify(review.values) !== JSON.stringify(getValue(current, row.path)))
                throw Error(`維持する項目の範囲・理由・元の値を確認してください: ${row.id}`);
            continue;
        }
        if (!['confirmed', 'not-applicable'].includes(review?.decision))
            throw Error(`未回答: ${row.id}`);
        if (JSON.stringify(review.values) !== JSON.stringify(row.current))
            throw Error(`確認した値から変更されています: ${row.id}`);
        if (review.decision === 'not-applicable' && (!review.reason?.trim() || row.current.length && !row.condition && !row.forbidden))
            throw Error(`非該当の理由または条件を確認してください: ${row.id}`);
    }
    const expectedInputs = await inputFiles(base, current);
    if (answers.questionLevel) {
        const confirmed = listingRows.filter(row => answers.reviews[row.id]?.decision === 'confirmed');
        for (const keys of changedPaths(current, answers.settings)) {
            if (!confirmed.some(row => coversPath(row.path, keys)))
                throw Error(`質問範囲外の変更は個別確認が必要です: ${keys.join('.')}`);
        }
    }
    if (expectedInputs.some(file => !Object.hasOwn(answers.base ?? {}, file)))
        throw Error('回答作成後にファイルが変更されています。回答を作り直してください。');
    for (const scope of ['documents', 'categories']) {
        if (Object.keys(current[scope]).some(file => !Object.hasOwn(answers.settings[scope], file)))
            throw Error(`${scope}の既存ファイルを省略できません。全メタデータを未設定にする場合は {} を指定してください。`);
    }
    const actual = await hashes(base, Object.keys(answers.base ?? {}));
    if (!Object.keys(actual).length || JSON.stringify(actual) !== JSON.stringify(answers.base))
        throw Error('回答作成後にファイルが変更されています。回答を作り直してください。');
    await checkManaged(base);
    await validateSettings(answers.settings, base);
    return answers;
}
export async function plannedFiles(answers, base = root) {
    await validateAnswers(answers, base);
    const next = {
        'site.settings.json': encode(answers.settings),
        'tsconfig.json': encode(answers.settings.typescript),
    };
    for (const [file, front] of Object.entries(answers.settings.documents)) {
        const p = await safeFile(base, file);
        let text = '';
        try {
            text = await fs.readFile(p, 'utf8');
        }
        catch (e) {
            if (e.code !== 'ENOENT')
                throw e;
        }
        const body = text.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '');
        next[file] = `---\n${stringify(front).trimEnd()}\n---\n${body}`;
    }
    for (const [file, value] of Object.entries(answers.settings.categories))
        next[file] = encode(value);
    return next;
}
export async function plan(answers, base = root) {
    const next = await plannedFiles(answers, base);
    const changes = [];
    for (const [file, after] of Object.entries(next)) {
        const p = await safeFile(base, file);
        let before = null;
        try {
            before = await fs.readFile(p, 'utf8');
        }
        catch (e) {
            if (e.code !== 'ENOENT')
                throw e;
        }
        if (before !== after)
            changes.push({ file, before, after });
    }
    return { changes, questionLevel: answers.questionLevel ?? 'advanced', retainedEntries: Object.values(answers.reviews).filter(r => r.decision === 'retained').length, warning: 'ブログ・翻訳・公開先などを有効にした場合、対応コンテンツやモジュールの準備が必要です。反映後に型・ビルド・テストで確認してください。' };
}
export async function apply(answers, base = root, { failAfter = Infinity } = {}) {
    const { changes } = await plan(answers, base);
    const tracked = Object.keys(await manifest(base));
    const backups = new Map();
    let count = 0;
    try {
        for (const change of changes) {
            const file = await safeFile(base, change.file);
            backups.set(file, change.before);
            await fs.mkdir(path.dirname(file), { recursive: true });
            await fs.writeFile(file, change.after);
            if (++count === failAfter)
                throw Error('反映失敗の検証');
        }
        const stateFile = await safeFile(base, '.setup-state.json');
        try {
            backups.set(stateFile, await fs.readFile(stateFile, 'utf8'));
        }
        catch (e) {
            if (e.code !== 'ENOENT')
                throw e;
            backups.set(stateFile, null);
        }
        // Record every new document/category as well as existing managed files.
        await fs.writeFile(stateFile, encode(await hashes(base, [...new Set([...tracked, ...Object.keys(answers.settings.documents), ...Object.keys(answers.settings.categories), ...changes.map(c => c.file)])], { metadataOnly: true })));
    }
    catch (error) {
        for (const [file, before] of [...backups].reverse()) {
            if (before === null)
                await fs.rm(file, { force: true });
            else
                await fs.writeFile(file, before);
        }
        throw error;
    }
    return { changed: changes.map(c => c.file) };
}
