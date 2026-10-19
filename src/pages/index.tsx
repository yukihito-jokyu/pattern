import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import documentPreview from '@site/docs/web/documentation/docusaurus-basic/images/document-desktop.png';
import styles from './index.module.css';

export default function Home(): ReactNode {
  const downloadUrl = useBaseUrl('/downloads/patterns/web/documentation/docusaurus-basic.zip');
  return <Layout title="pattern" description="設定や構成の説明と、対応する実装を掲載するパターン集です。">
    <main className={styles.page}>
      <div className="container">
        <header className={styles.header}>
          <h1>パターン一覧</h1>
          <p>設定や構成の説明と、対応する実装を掲載しています。<br className={styles.desktopBreak} />各パターンの実装・README・検証用ファイルをZIPで取得できます。</p>
        </header>

        <article className={styles.pattern} aria-labelledby="docusaurus-title">
          <div className={styles.details}>
            <p className={styles.category}>Web <span aria-hidden="true">/</span> ドキュメント</p>
            <h2 id="docusaurus-title"><Link to="/docs/web/documentation/docusaurus-basic">Docusaurusのドキュメントサイト</Link></h2>
            <p className={styles.description}>Markdownの記事をサイドバーで整理し、日本語で検索できるサイトの構成です。サイト名や公開先などの設定は、付属のsetupスキルから変更できます。</p>
            <dl className={styles.features}>
              <div><dt>文書の表示</dt><dd>記事・コード・画像、自動サイドバー</dd></div>
              <div><dt>検索</dt><dd>タイトルと本文を対象とする日本語検索</dd></div>
              <div><dt>セットアップ</dt><dd>設定台帳と、質問に沿って設定するスキル</dd></div>
            </dl>
            <div className={styles.actions}>
              <Link className="button button--primary" to="/docs/web/documentation/docusaurus-basic">構成と設定の説明</Link>
              <a href={downloadUrl} download>実装をダウンロード <span className={styles.fileType}>ZIP</span></a>
            </div>
          </div>
          <figure className={styles.preview}>
            <Link to="/docs/web/documentation/docusaurus-basic#完成画面" aria-label="Docusaurusパターンの完成画面を見る">
              <img src={documentPreview} alt="左にサイドバー、中央に本文とコード、右に目次を配置した文書画面" width="1440" height="1100" />
            </Link>
            <figcaption>文書画面の例 · Docusaurus</figcaption>
          </figure>
        </article>

        <section className={styles.guide} aria-labelledby="usage-title">
          <h2 id="usage-title">パターンの利用手順</h2>
          <ol className={styles.steps}>
            <li><span className={styles.stepNumber} aria-hidden="true">01</span><div><h3>説明を確認する</h3><p>全体構造、設定値の意味、具体的な動作と制約を確認します。</p></div></li>
            <li><span className={styles.stepNumber} aria-hidden="true">02</span><div><h3>ZIPを展開する</h3><p>実装をダウンロードし、READMEに沿って依存関係と設定を準備します。</p></div></li>
            <li><span className={styles.stepNumber} aria-hidden="true">03</span><div><h3>動作を検証する</h3><p>付属の検証手順を実行し、利用先の環境で期待どおりに動くか確認します。</p></div></li>
          </ol>
        </section>

        <aside className={styles.maintenance} aria-label="パターンの管理手順">
          <div><h2>パターンを追加・更新する</h2><p>配置、説明と実装の作成、レビュー、ZIP配布の手順をまとめています。</p></div>
          <Link to="/docs/project/contributing">追加・更新手順を読む <span aria-hidden="true">→</span></Link>
        </aside>
      </div>
    </main>
  </Layout>;
}
