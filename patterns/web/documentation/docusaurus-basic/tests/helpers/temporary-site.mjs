import { mkdtemp, cp, symlink, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
export const repository = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
export async function temporarySite() {
    const temp = await mkdtemp(path.join(os.tmpdir(), 'docusaurus-basic-'));
    const ignored = new Set(['node_modules', 'build', '.docusaurus', 'test-results', 'playwright-report', '.git']);
    await cp(repository, temp, { recursive: true, filter: p => !ignored.has(path.basename(p)) });
    await symlink(path.join(repository, 'node_modules'), path.join(temp, 'node_modules'), 'dir');
    return { temp, cleanup: () => rm(temp, { recursive: true, force: true }) };
}
export function build(temp, baseUrl = '/') {
    return spawnSync(process.execPath, [path.join(repository, 'node_modules/@docusaurus/core/bin/docusaurus.mjs'), 'build'], {
        cwd: temp, env: { ...process.env, SITE_BASE_URL: baseUrl, NODE_ENV: 'production' }, encoding: 'utf8', timeout: 180000, maxBuffer: 8 * 1024 * 1024
    });
}
if (process.argv[2] === 'serve') {
    const site = await temporarySite();
    let child;
    let stopped = false;
    async function close() {
        if (stopped)
            return;
        stopped = true;
        if (child && child.exitCode === null) {
            child.kill('SIGTERM');
            await new Promise(r => child.once('exit', r));
        }
        await site.cleanup();
    }
    for (const sig of ['SIGINT', 'SIGTERM'])
        process.on(sig, () => close().then(() => process.exit()));
    try {
        // Additional articles exist only in this test site.
        await writeFile(path.join(site.temp, 'docs/guide/added.md'), '---\ntitle: 追加した記事\nslug: /guide/added\nsidebar_position: 3\n---\n\n# 追加した記事\n\n追加反映専用キーワード。\n');
        await writeFile(path.join(site.temp, 'docs/hidden.md'), '---\ntitle: 検索非公開記事\nunlisted: true\n---\n\n非公開専用語。\n');
        const result = build(site.temp, '/preview/');
        if (result.status !== 0)
            throw Error(result.stdout + result.stderr);
        child = spawn(process.execPath, [path.join(repository, 'node_modules/@docusaurus/core/bin/docusaurus.mjs'), 'serve', '--host', '127.0.0.1', '--port', '4186', '--no-open'], { cwd: site.temp, env: { ...process.env, SITE_BASE_URL: '/preview/' }, stdio: 'inherit' });
        child.on('exit', code => {
            if (!stopped)
                close().then(() => process.exit(code || 1));
        });
    }
    catch (error) {
        console.error(error);
        await close();
        process.exitCode = 1;
    }
}
