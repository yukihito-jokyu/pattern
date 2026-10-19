import path from 'node:path';
import {readFile} from 'node:fs/promises';
import {catalog, requireValid, exists} from './project.mjs';
import {patternPaths} from './patterns.mjs';
import {markdownTree, frontMatter} from './markdown.mjs';

const text = value => typeof value === 'string' && value.trim() && !/\{\{[^}]+\}\}|TODO|ここに記入/.test(value);

export async function listingEntry(root, id, data) {
  const paths = patternPaths(id);
  const directory = path.dirname(path.join(root, paths.document));
  for (const key of ['title', 'description', 'slug']) if (!text(data[key])) throw new Error(`${key}を指定してください。`);
  if (!data.slug.startsWith('/') || data.slug.startsWith('/docs/') || /[?#]/.test(data.slug)) throw new Error('slugは/docsを含めない/始まりのパスにしてください。');
  const config = data.pattern ?? {};
  if (typeof config !== 'object' || Array.isArray(config) || Object.keys(config).some(key => !['position', 'features', 'actionLabel', 'preview'].includes(key))) throw new Error('patternの紹介設定が不正です。');
  if (config.position !== undefined && !Number.isSafeInteger(config.position)) throw new Error('pattern.positionは整数で指定してください。');
  const features = config.features ?? [];
  if (!Array.isArray(features) || features.some(item => !item || !text(item.label) || !text(item.value)) || new Set(features.map(item => item.label)).size !== features.length) throw new Error('pattern.featuresは重複しないlabelとvalueの配列で指定してください。');
  if (config.actionLabel !== undefined && !text(config.actionLabel)) throw new Error('pattern.actionLabelが不正です。');
  const category = [];
  const parts = id.split('/');
  for (let depth = 1; depth <= 2; depth++) {
    const file = path.join(root, 'docs', ...parts.slice(0, depth), '_category_.json');
    const metadata = await exists(file) ? JSON.parse(await readFile(file, 'utf8')) : {};
    category.push(text(metadata.label) ? metadata.label : parts[depth - 1]);
  }
  const result = {id: `pattern-${id.replaceAll('/', '--')}`, category, title: data.title, description: data.description, to: `/docs${data.slug}`, downloadPath: paths.download, features, actionLabel: config.actionLabel ?? '詳しい説明を読む', position: config.position ?? 0};
  if (config.preview !== undefined) {
    const preview = config.preview;
    if (!preview || typeof preview !== 'object' || Array.isArray(preview) || Object.keys(preview).some(key => !['src', 'alt', 'width', 'height', 'caption', 'anchor'].includes(key)) || !['src', 'alt', 'caption'].every(key => text(preview[key])) || !['width', 'height'].every(key => Number.isSafeInteger(preview[key]) && preview[key] > 0) || (preview.anchor !== undefined && (!text(preview.anchor) || /[#?\s]/.test(preview.anchor)))) throw new Error('pattern.previewの画像・代替テキスト・寸法・説明・anchorを確認してください。');
    const image = path.resolve(directory, preview.src);
    if (!image.startsWith(path.join(directory, 'images') + path.sep) || path.extname(image) !== '.png') throw new Error('pattern.preview.srcは同じ文書のimages/配下のPNGにしてください。');
    if (!await exists(image)) throw new Error(`画像がありません: ${image}`);
    const bytes = await readFile(image);
    if (!bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error('pattern.preview.srcはPNG形式にしてください。');
    result.preview = {src: `@site/${path.relative(root, image).split(path.sep).join('/')}`, alt: preview.alt, width: preview.width, height: preview.height, caption: preview.caption, to: `${result.to}${preview.anchor ? `#${preview.anchor}` : ''}`, linkLabel: `${data.title}の画面例を見る`};
  }
  return result;
}

export async function patternList(root) {
  const {ids} = requireValid(await catalog(root));
  const entries = [];
  for (const id of ids) {
    const file = path.join(root, patternPaths(id).document);
    const data = frontMatter(markdownTree(await readFile(file, 'utf8')));
    if (data.draft || data.unlisted) continue;
    try {entries.push(await listingEntry(root, id, data));} catch (error) {throw new Error(`${file}: ${error.message}`);}
  }
  return entries.sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
}
