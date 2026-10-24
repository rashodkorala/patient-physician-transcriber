import Link from "next/link";
import styles from "./home.module.css";

export default function Home() {
  return (
    <main className={styles.page}>
      <p className={styles.eyebrow}>Demo night</p>
      <h1 className={styles.title}>Medical interpreter</h1>
      <ul className={styles.links}>
        <li>
          <Link href="/control">
            <span className={styles.name}>Physician controller</span>
            <span className={styles.device}>Laptop</span>
          </Link>
        </li>
        <li>
          <Link href="/screen">
            <span className={styles.name}>Shared screen</span>
            <span className={styles.device}>TV</span>
          </Link>
        </li>
      </ul>
    </main>
  );
}
