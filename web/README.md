# Web (Next.js)

Screens for the demo: `/control` (physician laptop) and `/screen` (shared TV). See the repository README for how to run everything.

- `npm run build`: production build.
- `npm run check:contracts`: type-checks `lib/contracts.ts` against the server's contract fixtures (CDR-001, CDR-002).
- `node e2e/week1.mjs`: browser check against a running `scripts/dev.sh --prod` with `TRANSLATOR=fake`.
