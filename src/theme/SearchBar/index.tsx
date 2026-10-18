import {useEffect, useId, useMemo, useRef, useState, type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {useHistory} from '@docusaurus/router';
import {usePluginData} from '@docusaurus/useGlobalData';
import {searchDocuments, type SearchDocument} from '../../../plugins/site-search/search-core';
import styles from './styles.module.css';

function SearchIcon(): ReactNode {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>;
}

export default function SearchBar(): ReactNode {
  const data = usePluginData('pattern-search') as {documents: SearchDocument[]};
  const history = useHistory();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [shortcut, setShortcut] = useState('Ctrl K');
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const resultList = useRef<HTMLUListElement>(null);
  const id = useId();
  const results = useMemo(() => searchDocuments(data.documents, query), [data.documents, query]);

  function close() {
    dialog.current?.close();
    setOpen(false);
  }

  useEffect(() => {
    setShortcut(/Mac|iPhone|iPad/.test(navigator.platform) ? '⌘ K' : 'Ctrl K');
    function keydown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setQuery('');
        setActive(0);
        setOpen(true);
      }
    }
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, []);

  useEffect(() => {
    if (open) {
      dialog.current?.showModal();
      input.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    resultList.current?.children[active]?.scrollIntoView({block: 'nearest'});
  }, [active]);

  return <>
    <button ref={trigger} type="button" className={styles.trigger} onClick={() => {setQuery(''); setActive(0); setOpen(true);}} aria-label="文書を検索" aria-haspopup="dialog">
      <SearchIcon/><span>文書を検索</span><kbd>{shortcut}</kbd>
    </button>
    <dialog ref={dialog} className={styles.dialog} aria-labelledby={`${id}-title`} onCancel={close} onClose={() => {setOpen(false); trigger.current?.focus();}} onClick={(event) => {if (event.target === dialog.current) {const box = dialog.current.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close();}}}>
      <div className={styles.header}><h2 id={`${id}-title`}>文書を検索</h2><button type="button" className={styles.close} onClick={close} aria-label="検索を閉じる"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button></div>
      <div className={styles.field}><SearchIcon/><input ref={input} value={query} placeholder="キーワードを入力…" aria-label="検索キーワード" role="combobox" aria-autocomplete="list" aria-expanded={results.length > 0} aria-controls={`${id}-results`} aria-activedescendant={results[active] ? `${id}-result-${active}` : undefined} onChange={(event) => {setQuery(event.target.value); setActive(0);}} onKeyDown={(event) => {
        if (event.nativeEvent.isComposing) return;
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {event.preventDefault(); setActive((value) => Math.max(0, Math.min(results.length - 1, value + (event.key === 'ArrowDown' ? 1 : -1))));}
        if (event.key === 'Enter' && results[active]) {event.preventDefault(); const target = results[active].permalink; close(); history.push(target);}
      }}/>{query && <button type="button" className={styles.clear} aria-label="検索語を消去" onClick={() => {setQuery(''); setActive(0); input.current?.focus();}}>×</button>}</div>
      <div className={styles.results}>
        {!query.trim() ? <p className={styles.message}>文書名やキーワードで検索できます。<br/><span>例：パターン、設定、追加</span></p> : results.length ? <ul ref={resultList} id={`${id}-results`} role="listbox" aria-label="検索結果">{results.map((result, index) => <li key={result.permalink} role="presentation"><Link id={`${id}-result-${index}`} to={result.permalink} role="option" aria-selected={active === index} className={`${styles.result} ${active === index ? styles.active : ''}`} onMouseEnter={() => setActive(index)} onClick={close}><strong>{result.title}</strong><p>{result.excerpt}</p><span className={styles.path}>{result.permalink}</span></Link></li>)}</ul> : <p className={styles.message}>「{query}」に一致する文書はありません。<br/><span>別の単語や短いキーワードで検索してください。</span></p>}
      </div>
      <footer className={styles.footer}><span aria-live="polite">{query.trim() ? `${results.length}件の文書` : `${data.documents.length}件の文書を検索`}</span><span className={styles.keys}>↑↓ 選択　Enter 移動　Esc 閉じる</span></footer>
    </dialog>
  </>;
}
