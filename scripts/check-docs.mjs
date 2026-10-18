import path from 'node:path';
import {readFile} from 'node:fs/promises';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkFrontmatter from 'remark-frontmatter';
import {parse as parseYaml} from 'yaml';
import {catalog, cliOptions, exists, filesIn, main, read, requireValid} from './lib/project.mjs';

export function markdownTree(source) {
  return unified().use(remarkParse).use(remarkFrontmatter, ['yaml']).parse(source);
}

export function visit(node, action) {
  action(node);
  for (const child of node.children || []) visit(child, action);
}

export async function checkDocs(root) {
  const {ids} = requireValid(await catalog(root));
  const errors = [];
  const slugs = new Map();
  for (const file of (await filesIn(path.join(root, 'docs'))).filter(f => /\.mdx?$/.test(f))) {
    const relative = path.relative(path.join(root, 'docs'), file).split(path.sep).join('/');
    const isProject = relative.startsWith('project/');
    const id = path.posix.dirname(relative);
    if (!isProject && (!ids.includes(id) || path.basename(file) !== 'index.md')) errors.push(`${file}: パターンの入口は3階層配下のindex.mdです。`);
    const tree = markdownTree(await read(file));
    let data;
    try {data = parseYaml(tree.children.find(n => n.type === 'yaml')?.value || '') || {};} catch (e) {errors.push(`${file}: front matterが不正です: ${e.message}`); data = {};}
    for (const key of ['title', 'description', 'slug']) if (typeof data[key] !== 'string' || !data[key].trim()) errors.push(`${file}: ${key}を指定してください。`);
    for (const key of ['title', 'description', 'slug']) if (typeof data[key] === 'string' && /\{\{[^}]+\}\}|TODO|ここに記入/.test(data[key])) errors.push(`${file}: ${key}にテンプレートの記入欄が残っています。`);
    if (typeof data.slug === 'string' && data.slug.trim()) {
      if (!data.slug.startsWith('/') || data.slug.startsWith('/docs/') || /[?#]/.test(data.slug)) errors.push(`${file}: slugは/docsを含めない/始まりのパスにしてください。`);
      if (slugs.has(data.slug)) errors.push(`${file}: slugが${slugs.get(data.slug)}と重複しています。`);
      slugs.set(data.slug, file);
    }
    const definitions = new Map();
    visit(tree, node => {if (node.type === 'definition') definitions.set(node.identifier.toLowerCase(), node);});
    const references = [];
    let hasDownload = false;
    visit(tree, node => {
      if (node.type === 'text' && /\{\{[^}]+\}\}|TODO|ここに記入/.test(node.value)) errors.push(`${file}:${node.position.start.line}: テンプレートの記入欄が残っています。`);
      const definition = node.type.endsWith('Reference') ? definitions.get(node.identifier.toLowerCase()) : node;
      if (node.type === 'image' || node.type === 'imageReference') references.push({node, url: definition?.url});
      if (!isProject && (node.type === 'link' || node.type === 'linkReference')) {
        const url = definition?.url || '';
        const expected = `/downloads/patterns/${id}.zip`;
        if (url === expected) hasDownload = true;
        else if (/\.zip(?:[?#]|$)/i.test(url)) errors.push(`${file}: ZIPリンクは${expected}を指定してください。`);
      }
    });
    if (!isProject && !hasDownload) errors.push(`${file}: 対応するZIPのダウンロードリンクがありません。`);
    for (const {node, url} of references) {
      const fail = message => errors.push(`${file}:${node.position.start.line}: ${message}`);
      if (!node.alt?.trim()) fail('画像に代替テキストを指定してください。');
      if (!url || /^(?:[a-z]+:|\/\/|\/)/i.test(url)) {fail('説明用PNGを文書と同じパターンのimages/に置き、相対参照してください。'); continue;}
      let target;
      try {target = path.resolve(path.dirname(file), decodeURIComponent(url));} catch {fail('画像のURLが不正です。'); continue;}
      const imageRoot = path.join(path.dirname(file), 'images') + path.sep;
      if (!target.startsWith(imageRoot) || path.extname(target) !== '.png') {fail('画像はimages/配下の.pngにしてください。'); continue;}
      if (!await exists(target)) {fail(`画像がありません: ${target}`); continue;}
      const bytes = await readFile(target);
      if (bytes.length < 24 || !bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) || bytes.toString('ascii',12,16) !== 'IHDR' || !bytes.readUInt32BE(16) || !bytes.readUInt32BE(20)) fail(`PNG形式ではありません: ${target}`);
    }
  }
  requireValid({errors});
  return {ids};
}

main(import.meta.url, async () => {
  const {ids} = await checkDocs(cliOptions().root);
  console.log(`文書確認: ${ids.length}パターン。違反なし。`);
});
