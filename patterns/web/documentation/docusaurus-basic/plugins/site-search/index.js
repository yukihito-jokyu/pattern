const fs = require('node:fs');
const path = require('node:path');
const picomatch = require('picomatch');

function plainText(markdown) {
  return markdown
    .replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '')
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^```[^\n]*\n|^```\s*$/gm, '')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/[#*`|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

module.exports = function patternSearch(context) {
  return {
    name: 'pattern-search',
    async allContentLoaded({allContent, actions}) {
      const plugins = allContent['docusaurus-plugin-content-docs'] || {};
      const documents = [];
      const options = context.siteConfig.customFields.pattern.search;
      const included = picomatch(options.include);
      const excluded = options.exclude.length ? picomatch(options.exclude) : () => false;
      for (const content of Object.values(plugins)) {
        for (const version of content.loadedVersions || []) {
          for (const doc of version.docs) {
            if (doc.draft || doc.unlisted) continue;
            const source = doc.source.replace(/^@site\//, '');
            if(!included(source) || excluded(source)) continue;
            const markdown = await fs.promises.readFile(path.resolve(context.siteDir, source), 'utf8');
            documents.push({title: doc.title, permalink: doc.permalink, content: plainText(markdown)});
          }
        }
      }
      const data = {documents};
      actions.setGlobalData(data);
      await actions.createData('search-index.json', JSON.stringify(data));
    },
  };
};
