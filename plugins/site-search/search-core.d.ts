export type SearchDocument = {title: string; content: string; permalink: string};
export type SearchResult = SearchDocument & {score: number; excerpt: string};
export function searchDocuments(documents: SearchDocument[], query: string, limit?: number): SearchResult[];
