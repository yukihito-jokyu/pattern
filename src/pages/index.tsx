import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home(): ReactNode {
  return <Layout title="pattern" description="パターンの仕組みと、利用できる実装をまとめます。">
    <main className="container margin-vert--xl">
      <h1>仕組みを理解し、実装を持ち帰る。</h1>
      <p>設定値や構造の意味を具体例で読み、対応する実装をZIPで取得できるパターン集です。</p>
      <p>現在は管理基盤を整備した段階です。実用パターンはこれから追加します。</p>
      <Link className="button button--primary" to="/docs/project/contributing">パターンの追加・更新方法</Link>
    </main>
  </Layout>;
}
