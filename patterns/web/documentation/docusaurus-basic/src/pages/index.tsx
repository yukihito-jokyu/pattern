import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import type {PatternOptions} from '../pattern-types';
export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const home = (siteConfig.customFields?.pattern as PatternOptions).home;
  return <Layout title={siteConfig.title} description={siteConfig.tagline}>
    <main className="container margin-vert--xl">
      <p>{siteConfig.title}</p><h1>{home.heading}</h1><p>{home.body}</p>
      <Link className="button button--primary margin-top--md" to={home.linkTo}>{home.linkLabel}</Link>
      <hr className="margin-vert--xl"/>
      <div className="row">
        <section className="col col--4"><h2>書いて整理する</h2><p>Markdownの記事をカテゴリにまとめ、サイドバーから読み進めます。</p></section>
        <section className="col col--4"><h2>検索で見つける</h2><p>文書のタイトルと本文を、日本語のキーワードで検索できます。</p></section>
        <section className="col col--4"><h2>用途に合わせる</h2><p>setupスキルと設定台帳で、自分のサイトの設定を選べます。</p></section>
      </div>
    </main>
  </Layout>;
}
