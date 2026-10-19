import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkFrontmatter from 'remark-frontmatter';
import {parse as parseYaml} from 'yaml';

export function markdownTree(source) {
  return unified().use(remarkParse).use(remarkFrontmatter, ['yaml']).parse(source);
}

export function visit(node, action) {
  action(node);
  for (const child of node.children || []) visit(child, action);
}

export function frontMatter(tree) {
  return parseYaml(tree.children.find(n => n.type === 'yaml')?.value || '') || {};
}
