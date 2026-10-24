import Link from "next/link";

export default function Home() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "48px 16px", lineHeight: 1.6 }}>
      <h1>Demo Night Interpreter</h1>
      <p>Open each screen on its device:</p>
      <ul>
        <li><Link href="/control">Physician controller</Link> (laptop)</li>
        <li><Link href="/screen">Shared screen</Link> (TV)</li>
      </ul>
    </main>
  );
}
