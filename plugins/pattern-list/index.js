const path = require('node:path');
const {pathToFileURL} = require('node:url');

module.exports = function patternListPlugin(context) {
  return {
    name: 'pattern-list',
    getPathsToWatch() {return [path.join(context.siteDir, 'docs/**/*.{md,json,png}'), path.join(context.siteDir, 'patterns/*/*/*/README.md')];},
    async loadContent() {
      const {patternList} = await import(pathToFileURL(path.join(context.siteDir, 'scripts/lib/pattern-list.mjs')).href);
      return patternList(context.siteDir);
    },
    async contentLoaded({content, actions}) {
      const imports = [];
      const entries = content.map((entry, index) => {
        if (!entry.preview) return JSON.stringify(entry);
        const {preview, ...rest} = entry;
        const {src, ...metadata} = preview;
        imports.push(`import image${index} from ${JSON.stringify(src)};`);
        return `{...${JSON.stringify(rest)}, preview: {...${JSON.stringify(metadata)}, src: image${index}}}`;
      });
      const modulePath = await actions.createData('patterns.js', `${imports.join('\n')}\nexport default [${entries.join(',\n')}];\n`);
      actions.addRoute({path: context.siteConfig.baseUrl, exact: true, component: '@site/src/components/PatternHome.tsx', modules: {patterns: modulePath}});
    },
  };
};
