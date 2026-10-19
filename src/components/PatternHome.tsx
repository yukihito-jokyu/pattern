import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import PatternArticle from './PatternArticle';
import type {PatternArticleProps} from './PatternArticle';
import styles from './PatternHome.module.css';

export default function PatternHome({patterns}: {patterns: PatternArticleProps[]}): ReactNode {
  return <Layout title="pattern" description="設定や構成の説明と、対応する実装を掲載するパターン集です。">
    <main className={styles.page}>
      <div className="container">
        <header className={styles.header}>
          <h1>パターン一覧</h1>
          <p>設定や構成の説明と、対応する実装を掲載しています。<br className={styles.desktopBreak} />各パターンの実装・README・検証用ファイルをZIPで取得できます。</p>
        </header>

        {patterns.map(pattern => <PatternArticle key={pattern.id} {...pattern} />)}

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
