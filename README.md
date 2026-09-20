# Jev Decision Lab

![Jev Decision Lab logo](./public/jev-decision-lab-logo.png)

**Rules for the obvious. Jev for the ambiguous.**

An open-source Next.js MVP that compares a fixed personalization function with a hybrid function-plus-Jev decision architecture.

Public site: [radrebelsam.github.io/jev-decision-lab/](https://radrebelsam.github.io/jev-decision-lab/)

## What it demonstrates

- Function-only baseline: page-count first, then campaign signals, then a default.
- Hybrid route: functions handle clear cases; Jev receives only conflicting cases.
- Fixed output schema: `builder | campaign | returning`.
- Transparent labeled test set with the expected answers withheld from Jev.
- Public static replay with no hosted API key.
- Local live mode where each developer uses their own TypeSafe key.

The recorded MVP run scored:

| Approach | Result |
| --- | ---: |
| Function only | 5/8 · 63% |
| Function + Jev | 8/8 · 100% |
| Cases handled without Jev | 4/8 |

This is a behavioral benchmark on eight designed cases. It is not evidence of conversion lift. Production validation requires an online randomized experiment.

## Run the live proof locally

Requirements:

- Node.js 22
- A TypeSafe API key

Clone and install:

```bash
git clone https://github.com/RadRebelSam/jev-decision-lab.git
cd jev-decision-lab
npm install
```

Create `.env.local` in the project root:

```env
TYPESAFE_API_KEY=your_own_key
```

Start the live app:

```bash
npm run dev
```

Open `http://localhost:3000` and select **Run live proof**.

The key stays in the local Next.js server. It is never bundled into browser JavaScript. Files matching `.env*` are ignored by Git, except `.env.example`.

## Build the public static site

The static build uses the recorded benchmark and makes no Jev requests:

```bash
npm run build:static
```

Upload the contents of `out/` to any static host.

## Project structure

```text
app/
  api/benchmark/       Live local Jev benchmark
  api/personalize/     Live local personalization decision
  demo/                Interactive personalization demo
  page.tsx             Public proof page
components/
  proof-lab.tsx        Rules-vs-hybrid benchmark UI
  personalization-demo.tsx
lib/
  benchmark.ts         Cases, features, routing, recorded result
  personalization.ts  Three fixed variants and fallback
```

## Decision architecture

```text
referrer + UTM + page history
              |
       function extracts facts
          /              \
   clear case         conflicting case
      |                     |
 function choice         Jev Choice
          \              /
        schema validation
               |
    builder | campaign | returning
```

## Environment variables

```env
TYPESAFE_API_KEY=
TYPESAFE_BASE_URL=https://api.typesafe.ai
TYPESAFE_DEFAULT_MODEL=jev-latest
```

Never prefix the API key with `NEXT_PUBLIC_`.

## Deploy

See [DEPLOY.md](./DEPLOY.md) for the GitHub Pages deployment and custom-domain notes.

## Independence

Independent Jev experiment by [Rad Rebel Developer](https://radrebeldeveloper.com). Not affiliated with TypeSafe AI.

## License

[MIT](./LICENSE)
