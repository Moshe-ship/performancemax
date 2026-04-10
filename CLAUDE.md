# CLAUDE.md — Performance MAX Agency

## What This Is
Marketing agency website for performancemaxagency.com. Serves U.S. small and local businesses.

## Stack
- **Astro 6** static site
- **Hosting:** Hostinger (FTP IP: 31.170.166.247)
- **DNS:** Cloudflare (managed by co-founder)
- **CI/CD:** GitHub Actions — push to `main` → build → FTP to `public_html/`
- **Repo:** github.com/Moshe-ship/performancemax

## Key Commands
```bash
npm run dev          # Local dev server
npm run build        # Build to dist/
./scripts/new-post.sh "Title"  # Create new blog post
git push origin main # Auto-deploys via GitHub Actions
```

## Blog System
- Add `.md` files to `src/content/blog/`, push, live in ~20s
- Author: Musa the Carpenter

## SEO
- JSON-LD on every page (LocalBusiness, FAQPage, Service, Product, BlogPosting)
- Open Graph + Twitter Cards, XML sitemap, robots.txt, canonical URLs
- llms.txt for AI crawlers, geo meta tags for Roswell, GA
- GA: G-7D9LWPBDK5 | Search Console verified

## Branding
- Colors: Green (#7cb342) + Navy (#1b2e4e)
- Glassmorphism design, dark/light toggle
- Slogan: "Get Found. Get Customers."
- Secret sauce: "Near Me" Package (Google Ads + SEO + Local SEO)

## Contact
- HQ: 1804 Calibre Creek Pkwy, Roswell, GA 30076
- Phone: +1 (404) 716-5444
- Email: info@performancemaxagency.com
