/** Text with each critical value marked, so a dose reads the same in both languages (CDR-002). */

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export default function Highlighted({ text, values, className }: { text: string; values: string[]; className?: string }) {
  const wanted = [...new Set(values.filter(Boolean))].sort((a, b) => b.length - a.length);
  if (!wanted.length) return <>{text}</>;
  const pattern = new RegExp(`(${wanted.map(escape).join("|")})`, "giu");
  const lower = new Set(wanted.map((v) => v.toLocaleLowerCase()));
  return (
    <>
      {text.split(pattern).map((part, i) =>
        lower.has(part.toLocaleLowerCase()) ? (
          <mark key={i} className={className}>
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </>
  );
}
