function normalize(value) {
  return value.normalize('NFKC').toLocaleLowerCase('ja');
}

function searchDocuments(documents, query, limit = 8) {
  const terms = [...new Set(normalize(query).trim().split(/\s+/).filter(Boolean))];
  if (!terms.length) return [];
  return documents
    .map((document) => {
      const title = normalize(document.title);
      const content = normalize(document.content);
      if (!terms.every((term) => title.includes(term) || content.includes(term))) return null;
      const score = terms.reduce((sum, term) => sum + (title.includes(term) ? 10 : 1), 0);
      const position = Math.max(0, content.indexOf(terms[0]));
      const start = Math.max(0, position - 32);
      const excerpt = `${start ? '…' : ''}${document.content.slice(start, start + 150)}${document.content.length > start + 150 ? '…' : ''}`;
      return {...document, score, excerpt};
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title, 'ja'))
    .slice(0, limit);
}

module.exports = {searchDocuments};
