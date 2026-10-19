import fs from 'node:fs/promises';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { root, initAnswers, listing, verifyCoverage, validateAnswers, validateSettings, checkManaged, plan, apply, encode } from '../setup/lib/setup.mjs';
import { assertQuestionLevel, includesQuestion } from '../setup/lib/question-levels.mjs';
const { values, positionals } = parseArgs({
    allowPositionals: true, options: { out: { type: 'string' }, answers: { type: 'string' }, group: { type: 'string' }, level: { type: 'string' } }
});
try {
    const command = positionals[0];
    if (values.level) assertQuestionLevel(values.level);
    const settings = JSON.parse(await fs.readFile(path.join(root, 'site.settings.json'), 'utf8'));
    let result;
    if (command === 'list') {
        const c = await verifyCoverage();
        const answers = values.answers ? JSON.parse(await fs.readFile(values.answers, 'utf8')) : await initAnswers();
        const level = values.level ?? answers.questionLevel ?? 'important';
        result = listing(c, answers.settings).filter(row => includesQuestion(level, row.importance) && (!values.group || row.path === values.group || row.path.startsWith(values.group + '.'))).map(({ schema, ...row }) => row);
    }
    else if (command === 'init') {
        if (!values.out)
            throw Error('--outを指定してください。');
        result = await initAnswers(root, { level: values.level ?? 'important' });
        await fs.writeFile(values.out, encode(result), { flag: 'wx' });
        const rows = listing(await verifyCoverage(), result.settings);
        const selected = rows.filter(row => result.reviews[row.id].decision === 'unanswered');
        result = { file: values.out, questionLevel: result.questionLevel, entries: selected.length, questionPaths: new Set(selected.map(row => row.path)).size, retained: rows.length - selected.length };
    }
    else if (command === 'check') {
        await verifyCoverage();
        await checkManaged();
        await validateSettings(settings);
        result = {
            ok: true, baseUrl: {
                saved: settings.site.baseUrl ?? '/', effective: process.env.SITE_BASE_URL ?? settings.site.baseUrl ?? '/'
            }
        };
    }
    else if (['validate', 'plan', 'apply'].includes(command)) {
        if (!values.answers)
            throw Error('--answersを指定してください。');
        const answers = JSON.parse(await fs.readFile(values.answers, 'utf8'));
        result = command === 'validate' ? (await validateAnswers(answers), { ok: true }) : command === 'plan' ? await plan(answers) : await apply(answers);
    }
    else
        throw Error('list [--group site] [--level important|normal|advanced] [--answers file] | init --out file [--level important|normal|advanced] | validate/plan/apply --answers file | check');
    console.log(encode(result));
}
catch (error) {
    console.error(error.message);
    process.exitCode = 1;
}
