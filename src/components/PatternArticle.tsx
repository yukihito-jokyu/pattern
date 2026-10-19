import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './PatternArticle.module.css';

export type PatternArticleProps = {
  id: string;
  category: readonly [string, string];
  title: string;
  to: string;
  description: ReactNode;
  features: ReadonlyArray<{label: string; value: ReactNode}>;
  actionLabel: string;
  downloadPath: string;
  preview?: {
    to: string;
    linkLabel: string;
    src: string;
    alt: string;
    width: number;
    height: number;
    caption: string;
  };
};

export default function PatternArticle({
  id, category, title, to, description, features, actionLabel, downloadPath, preview,
}: PatternArticleProps): ReactNode {
  const downloadUrl = useBaseUrl(downloadPath);
  return (
    <article className={`${styles.pattern}${preview ? '' : ` ${styles.textPattern}`}`} aria-labelledby={id}>
      <div className={styles.details}>
        <p className={styles.category}>{category[0]} <span aria-hidden="true">/</span> {category[1]}</p>
        <h2 id={id}><Link to={to}>{title}</Link></h2>
        <p className={styles.description}>{description}</p>
        {features.length > 0 && <dl className={styles.features}>
          {features.map(({label, value}) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>}
        <div className={styles.actions}>
          <Link className="button button--primary" to={to}>{actionLabel}</Link>
          <a href={downloadUrl} download>実装をダウンロード <span className={styles.fileType}>ZIP</span></a>
        </div>
      </div>
      {preview && (
        <figure className={styles.preview}>
          <Link to={preview.to} aria-label={preview.linkLabel}>
            <img src={preview.src} alt={preview.alt} width={preview.width} height={preview.height} />
          </Link>
          <figcaption>{preview.caption}</figcaption>
        </figure>
      )}
    </article>
  );
}
