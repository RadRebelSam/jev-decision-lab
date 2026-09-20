# Publish Jev Decision Lab

## GitHub Pages

The public site is deployed directly from this repository:

```text
https://radrebelsam.github.io/jev-decision-lab/
```

Every push to `main` runs the Pages workflow. It installs dependencies, creates the static export, and deploys `out/`.

Build the same site locally:

```bash
npm install
npm run build:pages
```

## Custom subdomain

Desired address:

```text
https://jevdecisionlab.radrebeldeveloper.com
```

A DNS CNAME can point `jevdecisionlab` to `radrebelsam.github.io`.

After DNS is ready, add `jevdecisionlab.radrebeldeveloper.com` under **Settings → Pages → Custom domain** in this repository. GitHub will then create the required `CNAME` file and provision HTTPS.
