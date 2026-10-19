function normalize(value) {
  return value.normalize('NFKC').toLocaleLowerCase('ja');
}

function searchDocuments(documents, query, options = {}) {
  const {limit = 8, excerptLength = 150, titleWeight = 10} = typeof options === 'number' ? {limit: options} : options;
  const terms = Array.from(new Set(normalize(query).trim().split(/\s+/).filter(Boolean)));
  if (!terms.length) return [];
  return documents
    .map((document) => {
      const title = normalize(document.title);
      const content = normalize(document.content);
      if (!terms.every((term) => title.includes(term) || content.includes(term))) return null;
      const score = terms.reduce((sum, term) => sum + (title.includes(term) ? titleWeight : 1), 0);
      const position = Math.max(0, content.indexOf(terms[0]));
      const start = Math.max(0, position - 32);
      const excerpt = `${start ? '…' : ''}${document.content.slice(start, start + excerptLength)}${document.content.length > start + excerptLength ? '…' : ''}`;
      return {...document, score, excerpt};
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title, 'ja'))
    .slice(0, limit);
}

module.exports = {searchDocuments};
