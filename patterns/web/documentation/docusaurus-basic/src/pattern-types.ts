export type PatternOptions = {
  home: {heading: string; body: string; linkLabel: string; linkTo: string};
  search: {enabled: boolean; limit: number; excerptLength: number; titleWeight: number; include: string[]; exclude: string[]; label: string; placeholder: string; emptyMessage: string; noResultsMessage: string; shortcut: string};
};
