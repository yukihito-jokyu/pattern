const path = require('node:path');
const fs = require('node:fs');
// Explicit module references are local files selected by the user; never eval strings.
function hydrate(value, root = process.cwd()) {
    if (Array.isArray(value))
        return value.map(v => hydrate(v, root));
    if (value && typeof value === 'object') {
        if ('$module' in value) {
            if (Object.keys(value).some(k => !['$module', 'export'].includes(k)) || typeof value.$module !== 'string' || !value.$module.startsWith('./'))
                throw new Error('モジュール参照は {$module:"./file.cjs", export:"name"} で指定します。');
            const file = path.resolve(root, value.$module);
            if (!file.startsWith(path.resolve(root) + path.sep))
                throw new Error('モジュールはサイト内に配置してください。');
            if (!fs.realpathSync(file).startsWith(fs.realpathSync(root) + path.sep))
                throw new Error('モジュールはサイト内に配置してください。');
            const loaded = require(file);
            if (value.export && !Object.hasOwn(loaded, value.export))
                throw new Error(`exportがありません: ${value.export}`);
            return value.export ? loaded[value.export] : loaded.default ?? loaded;
        }
        return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, hydrate(v, root)]));
    }
    return value;
}
function resolveConfig(settings, root = __dirname + '/../..') {
    const resolved = hydrate(settings, root);
    const { error, value } = require('./custom-schema.cjs').validate(resolved.custom);
    if (error)
        throw error;
    return { ...resolved, custom: value };
}
module.exports = { hydrate, resolveConfig };
