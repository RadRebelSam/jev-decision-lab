# Publish Jev Decision Lab

## GitHub Pages path

The public site is deployed inside the existing `awesome-jev` Pages site:

```text
https://radrebelsam.github.io/awesome-jev/jev-decision-lab/

The `awesome-jev` Pages project currently redirects this URL to:

```text
https://jev.radrebeldeveloper.com/jev-decision-lab/
```

For that reason, `npm run build:pages` uses `/jev-decision-lab` as the runtime base path.
```

Build the correctly prefixed static site:

```bash
npm install
npm run build:pages
```

Copy the contents of `out/` into:

```text
RadRebelSam/awesome-jev/site/jev-decision-lab/
```

Pushing that folder to the `awesome-jev` main branch triggers its existing GitHub Pages workflow.

## Custom subdomain

Desired address:

```text
https://jevdecisionlab.radrebeldeveloper.com
```

A DNS CNAME can point the host to `radrebelsam.github.io`, but DNS cannot point directly to the `/awesome-jev/jev-decision-lab/` path.

After creating the CNAME, the GitHub Pages repository must also recognize the custom host. Because `awesome-jev` contains more than this one page, use either:

- a hostname-aware redirect at the Pages root; or
- a separate Pages repository dedicated to `jevdecisionlab.radrebeldeveloper.com`.

Until then, keep the repository homepage set to the working GitHub Pages path above.
