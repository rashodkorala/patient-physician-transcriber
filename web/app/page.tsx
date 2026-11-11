/**
 * The landing page: the product, one sentence, and the three devices in the room, plus the record view.
 *
 * @implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
 * @implements ADR-012: Clinic design system
 */

import Link from "next/link";
import styles from "./home.module.css";

const DEVICES = [
  {
    href: "/control",
    role: "Clinician",
    device: "Laptop",
    what: "Runs the visit: speaks, hears the interpreter, and sees every check before anything is said.",
    tone: styles.clinician,
  },
  {
    href: "/screen",
    role: "Room screen",
    device: "TV",
    what: "Shows what was said and how it was interpreted, in both languages, large enough for the room.",
    tone: styles.room,
  },
  {
    href: "/patient",
    role: "Patient",
    device: "Tablet or phone",
    what: "Follows the visit in their own language and can ask the doctor to slow down or say it again.",
    tone: styles.patient,
  },
] as const;

export default function Home() {
  return (
    <main className={styles.page}>
      <header className={styles.intro}>
        <h1 className={styles.title}>Medical interpreter</h1>
        <p className={styles.lede}>
          Live interpretation between a patient and a physician, with every word checked before it is spoken and a
          record both can trust.
        </p>
      </header>
      <ul className={styles.devices} aria-label="Devices">
        {DEVICES.map((d) => (
          <li key={d.href} className={`${styles.card} ${d.tone}`}>
            <Link href={d.href} className={styles.cardLink}>
              <span className={styles.role}>{d.role}</span>
              <span className={styles.device}>{d.device}</span>
              <span className={styles.what}>{d.what}</span>
            </Link>
          </li>
        ))}
      </ul>
      <p className={styles.record}>
        The physician&rsquo;s note and its sources are in the <Link href="/record">record view</Link>.
      </p>
    </main>
  );
}
