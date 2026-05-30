# Hugo Article Publishing

This project uses script-based publishing. It does not use a CMS backend.

## Publish One Draft Article

Publish the newest English article from the writing workspace:

```bash
scripts/publish-article.sh --latest --serve
```

Publish a specific article by absolute path:

```bash
scripts/publish-article.sh /home/dev/.skills-manager/skills/my-skills/skills/write-skill/posts/jack-li-website/2026-05-30/claude-code-dynamic-workflows-en.md --serve
```

By default, the script:

- imports only one article;
- preserves the source front matter;
- removes Hugo-removed keys that break builds, such as `lang`;
- renders Mermaid blocks into static SVG files;
- runs a local Hugo build;
- leaves changes uncommitted for review.

It does not publish every article in the writing workspace.

## Optional Flags

Commit the imported article to the staging repository:

```bash
scripts/publish-article.sh --latest --commit
```

Commit and push to the staging sandbox repository:

```bash
scripts/publish-article.sh --latest --push-staging
```

Override `date` and `lastmod` only when explicitly needed:

```bash
scripts/publish-article.sh /path/to/article-en.md --date 2026-05-30T04:00:00Z
```

Add an alias for an old URL:

```bash
scripts/publish-article.sh /path/to/article-en.md --alias /posts/old-post-slug/
```

Replace an old local post file:

```bash
scripts/publish-article.sh /path/to/article-en.md --replace-slug old-post-slug
```

## Production Deploy

Production deploy is a separate hard-gated step.

```bash
scripts/deploy-production.sh --confirm-production -m "post: publish new article"
```

This pushes to:

```text
git@github.com:jack-li-dev/jack-li-dev.github.io.git
```

Do not run the production script unless the current task explicitly authorizes a production push.
