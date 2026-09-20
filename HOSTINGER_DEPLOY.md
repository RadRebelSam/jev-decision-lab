# Publish the static site on Hostinger

Target domain:

```text
https://jevdecisionlab.radrebeldeveloper.com
```

The public build is fully static. It replays the recorded benchmark and does not contain or require a TypeSafe API key.

## 1. Build

From the project directory:

```bash
npm install
npm run build:static
```

The deployable website is generated in `out/`.

## 2. Create the subdomain

In Hostinger hPanel:

1. Open the website for `radrebeldeveloper.com`.
2. Open **Domains → Subdomains**.
3. Create `jevdecisionlab`.
4. Note the document-root folder Hostinger assigns to it.

If DNS is managed outside Hostinger, add the DNS record supplied by Hostinger at that provider.

## 3. Upload the site

1. Open **Files → File Manager**.
2. Open the subdomain document root.
3. Remove only the default placeholder file if Hostinger created one.
4. Upload the **contents** of `out/`, not the `out` directory itself.
5. Confirm that `index.html` is directly inside the subdomain document root.

You can also upload `jev-decision-lab-static.zip` and extract it in the document root.

## 4. Verify

Open:

```text
https://jevdecisionlab.radrebeldeveloper.com
```

Check:

- The logo appears in the header.
- The favicon appears in the browser tab.
- **Replay recorded proof** shows `63%` versus `100%`.
- **GitHub** opens the public repository.
- **Run live with your own key** opens the local-run instructions.
- `/demo/` loads the static function-only personalization preview.

## Updating the site

After changing the code:

```bash
git pull
npm install
npm run build:static
```

Replace the existing hosted files with the new contents of `out/`.

## Why the hosted site has no API key

TypeSafe rejects this public domain as a browser CORS origin, so a static page cannot call Jev directly. Asking visitors to send their keys through a proxy would make your server a secret-handling service.

The safer split is:

- Public site: static recorded proof.
- GitHub repository: live local proof using each developer's own `.env.local` key.
