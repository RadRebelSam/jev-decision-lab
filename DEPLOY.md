# Publish Jev Decision Lab

## Public URL

The canonical public site is:

```text
https://jevdecisionlab.radrebeldeveloper.com/
```

GitHub Pages hosts the site from `RadRebelSam/jev-decision-lab`. After the custom domain is active, the default project URL redirects to the canonical URL above.

Every push to `main` runs the Pages workflow. It installs dependencies, creates a root-relative static export, and deploys `out/`.

Build the same site locally:

```bash
npm install
npm run build:pages
```

## Custom subdomain

Custom address:

```text
https://jevdecisionlab.radrebeldeveloper.com
```

A DNS CNAME can point `jevdecisionlab` to `radrebelsam.github.io`.

The repository must also list `jevdecisionlab.radrebeldeveloper.com` under **Settings → Pages → Custom domain**. Because this project deploys through GitHub Actions, a repository `CNAME` file is not required.
