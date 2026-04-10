---
name: pmax-blog
description: Generate SEO-optimized blog posts about local business marketing for performancemaxagency.com
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [node, npm]
  env_vars: []
metadata:
  hermes:
    tags: [blog, seo, content, marketing, astro, local-seo, google-ads]
---
# Performance MAX Blog Content Generator

Generate SEO-optimized blog posts for performancemaxagency.com targeting local business owners who need help with digital marketing.

## Author Voice

Write as **"Musa the Carpenter"** — a hands-on expert who explains digital marketing concepts using practical, real-world language. The tone is:

- **Expert but accessible**: knows the industry deeply, but talks to business owners like a friend
- **Direct and honest**: no corporate fluff, no jargon without explanation
- **Story-driven**: uses real examples from local businesses (restaurants, plumbers, dentists, contractors, salons)
- **Opinionated**: has clear recommendations, not wishy-washy "it depends" advice

## Blog Post Requirements

### Structure

Every post must include this Astro frontmatter format:

```yaml
---
title: "Your SEO-Optimized Title Here"
description: "1-2 sentence meta description, 120-160 characters, includes primary keyword"
date: "YYYY-MM-DD"
author: "Musa the Carpenter"
image: "https://images.unsplash.com/photo-RELEVANT_ID?w=1200&q=80"
tags: ["primary keyword", "secondary keyword", "tertiary keyword"]
---
```

### Content Rules

1. **Minimum 1500 words** — aim for 1800-2200 for comprehensive coverage
2. **Use real examples**: reference specific business types (plumber in Roswell GA, dentist in Shaker Heights OH, restaurant owner, contractor, etc.)
3. **Include data and statistics**: cite real Google data, marketing statistics, conversion rates
4. **Actionable advice**: every section must have something the reader can do today
5. **Internal linking**: naturally reference Performance MAX services where relevant
6. **No generic filler**: every paragraph must teach something specific

### SEO Requirements

- **Primary keywords** (use naturally, not stuffed): local SEO, Google Ads, Performance Max campaigns, near me searches, Google Business Profile
- **Secondary keywords**: local business marketing, digital marketing for small business, online reviews, Google Maps ranking
- **H2/H3 structure**: use descriptive headings that include keywords
- **Meta description**: must be 120-160 characters, include primary keyword, create urgency or curiosity
- **Image**: use a relevant Unsplash photo URL

### Topic Categories

Generate posts about these subjects, rotating through them:

1. **Google Ads for local businesses** — campaign setup, budget tips, Performance Max campaigns, keyword strategies
2. **Local SEO** — Google Business Profile optimization, local citations, NAP consistency, map pack ranking
3. **"Near Me" search strategy** — capturing high-intent local traffic, mobile optimization
4. **Online reviews** — getting more reviews, responding to negative reviews, review management
5. **Website conversion** — landing pages, CTAs, mobile-first design, speed optimization
6. **Social media for local businesses** — platform selection, content ideas, ad strategies
7. **Email marketing** — list building, automation, nurture sequences for local businesses
8. **Competitor analysis** — how to outrank local competitors, differentiation strategies

### Call to Action

End every post with a natural CTA that:
- Does NOT sound salesy or pushy
- References Performance MAX Agency's services relevant to the topic
- Includes contact info: (404) 716-5444 or performancemaxagency.com
- Mentions the "Near Me" Package if relevant to the topic

## Execution Steps

1. **Pick a topic**: choose from the categories above or accept a user-provided topic
2. **Research**: gather current statistics and trends relevant to the topic
3. **Outline**: create H2/H3 structure with 5-8 sections
4. **Write**: generate the full post following all rules above
5. **Create the file**: use the existing script to scaffold the post:
   ```bash
   cd /Users/majana-agent/Projects/performancemax
   ./scripts/new-post.sh "Your Blog Post Title"
   ```
6. **Write content**: replace the scaffold content in `src/content/blog/{slug}.md` with the generated post, keeping the frontmatter format but updating all fields (title, description, date, author, image, tags) plus the full markdown body
7. **Verify**: confirm the file is valid markdown with correct frontmatter
8. **Word count**: count words in the body (excluding frontmatter) and confirm >= 1500

## File Location

Posts go in: `/Users/majana-agent/Projects/performancemax/src/content/blog/`

## Existing Posts (avoid duplicate topics)

- 7 Ways to Get More Customers from Google Maps
- Google Ads Mistakes Local Businesses Make
- Google AI Overviews and Local Business SEO
- Google Business Profile Optimization Guide
- How to Get More Online Reviews
- Local SEO vs Organic SEO
- Near Me Searches Strategy
- What Is a Performance Max Campaign
- Why Most Local Businesses Fail at Digital Marketing

## Brand Reference

- **Agency**: Performance MAX Agency
- **HQ**: Roswell, GA 30076
- **Slogan**: "Get Found. Get Customers."
- **Colors**: Green (#7cb342) + Navy (#1b2e4e)
- **Signature offer**: "Near Me" Package (Google Ads + SEO + Local SEO)
- **Phone**: (404) 716-5444
- **Website**: performancemaxagency.com
