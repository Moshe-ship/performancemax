---
name: pmax-competitor
description: Analyze competitor websites and generate competitive intelligence reports for local markets
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [curl]
  env_vars: []
metadata:
  hermes:
    tags: [competitor, analysis, marketing, local-seo, strategy, intelligence]
---
# Performance MAX Competitor Analysis

Analyze competitor websites in Performance MAX's target markets and generate actionable competitive intelligence reports.

## Target Markets

Performance MAX serves local businesses in two primary markets:

1. **Roswell, GA** (and greater North Atlanta / Fulton County)
2. **Shaker Heights, OH** (and greater Cleveland / Cuyahoga County)

When analyzing competitors, focus on businesses operating in or serving these areas.

## How to Use

The user provides one or more competitor URLs, a business category, or a market to analyze. Use the browser tool (Camofox) or curl to visit competitor sites and extract intelligence.

## Analysis Process

### Step 1: Gather Competitor Data

For each competitor URL, fetch and analyze the site:

```bash
# Fetch homepage
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" "COMPETITOR_URL" -o /tmp/competitor-home.html

# Fetch services/pricing page if it exists
curl -sL -A "Mozilla/5.0" "COMPETITOR_URL/services" -o /tmp/competitor-services.html
curl -sL -A "Mozilla/5.0" "COMPETITOR_URL/pricing" -o /tmp/competitor-pricing.html

# Fetch about page
curl -sL -A "Mozilla/5.0" "COMPETITOR_URL/about" -o /tmp/competitor-about.html

# Fetch sitemap for full site structure
curl -sL "COMPETITOR_URL/sitemap.xml" -o /tmp/competitor-sitemap.xml
```

Prefer the browser tool (Camofox) when available for JavaScript-rendered content.

### Step 2: Extract Intelligence

Analyze each competitor across these dimensions:

#### A. Services Offered

Parse the competitor's services/about pages and extract:

- Complete list of services offered
- How services are categorized and described
- Service-specific landing pages (indicates investment in that service)
- Unique service offerings not common in the market
- Service bundles or packages

Map each service to Performance MAX's equivalent:
| Competitor Service | PMax Equivalent | Gap? |
|---|---|---|
| [service] | [our service or "none"] | [yes/no] |

#### B. Pricing Signals

Look for any pricing information:

- Explicit price lists or rate cards
- "Starting at" pricing language
- Package tiers (basic/pro/enterprise)
- "Free consultation" or "free audit" offers
- "Contact for pricing" (indicates custom/high-end positioning)
- Monthly retainer language vs project-based

If no pricing is found, note the pricing strategy as opaque and what that implies about their positioning.

#### C. SEO and Content Strategy

Analyze their search visibility approach:

- **Blog presence**: do they have a blog? How often do they post? What topics?
- **Keywords targeted**: what terms appear in their title tags, H1s, and meta descriptions?
- **Content depth**: thin pages (under 300 words) vs comprehensive content?
- **Local SEO**: do they target specific cities/neighborhoods?
- **Schema markup**: what structured data types are they using?
- **Backlink signals**: do they mention partnerships, directories, or associations?

#### D. Trust and Authority Signals

- Client testimonials and case studies
- Portfolio or work examples
- Industry certifications or awards
- Team bios and credentials
- Google review count and rating (if visible or linked)
- Better Business Bureau, Chamber of Commerce memberships
- Years in business claims

#### E. Technology Stack

Identify the tech behind the competitor's site:

- CMS (WordPress, Squarespace, Wix, custom, etc.)
- Analytics tools (Google Analytics, Facebook Pixel, etc.)
- Chat widgets or lead capture tools
- Booking/scheduling integrations
- Speed and performance (how fast does the page load?)

#### F. Unique Selling Proposition (USP)

- What is their main headline/value proposition?
- How do they differentiate from other agencies?
- What guarantees or promises do they make?
- What is their brand personality (corporate, friendly, aggressive)?

#### G. Lead Generation Strategy

- Primary CTA (call, form, chat, book a meeting?)
- Number and placement of CTAs
- Lead magnets (free guides, audits, consultations)
- Pop-ups or exit-intent offers
- Phone number prominent or hidden?

### Step 3: Compare Against Performance MAX

For each dimension above, compare the competitor's approach to Performance MAX:

**Performance MAX Positioning:**
- Slogan: "Get Found. Get Customers."
- Signature offer: "Near Me" Package (Google Ads + SEO + Local SEO)
- Author voice: Musa the Carpenter (expert but accessible)
- Markets: Roswell GA, Shaker Heights OH
- Focus: local businesses, not enterprise
- Blog: 9 posts, expert content, practical advice
- Tech: Astro static site, fast, modern
- Phone: (404) 716-5444
- Schema: JSON-LD on every page

### Step 4: Identify Opportunities

Based on the analysis, identify:

1. **Service gaps**: what competitors offer that PMax does not (and should consider)
2. **Content gaps**: topics competitors rank for that PMax has not covered
3. **Positioning gaps**: market segments or messaging angles competitors miss
4. **Technical advantages**: where PMax's site is technically superior
5. **Weaknesses to exploit**: where competitors are clearly failing

## Report Format

Output the report in this structure:

```markdown
# Competitive Analysis Report
**Date:** YYYY-MM-DD
**Market:** [Roswell GA / Shaker Heights OH / Both]
**Competitors Analyzed:** [count]

## Executive Summary
[3-5 sentences: key findings, biggest threats, biggest opportunities]

## Competitor Profiles

### [Competitor 1 Name] — [URL]
**Threat Level:** [High / Medium / Low]

| Dimension | Finding | vs Performance MAX |
|-----------|---------|-------------------|
| Services | [summary] | [advantage/disadvantage/parity] |
| Pricing | [summary] | [advantage/disadvantage/parity] |
| SEO Strategy | [summary] | [advantage/disadvantage/parity] |
| Trust Signals | [summary] | [advantage/disadvantage/parity] |
| Technology | [summary] | [advantage/disadvantage/parity] |
| USP | [summary] | [advantage/disadvantage/parity] |
| Lead Gen | [summary] | [advantage/disadvantage/parity] |

**Key Strengths:** [bullets]
**Key Weaknesses:** [bullets]

[Repeat for each competitor]

## Competitive Landscape Matrix

| Factor | PMax | Competitor 1 | Competitor 2 | Competitor 3 |
|--------|------|-------------|-------------|-------------|
| Local SEO Focus | [rating] | [rating] | [rating] | [rating] |
| Content Quality | [rating] | [rating] | [rating] | [rating] |
| Tech/Speed | [rating] | [rating] | [rating] | [rating] |
| Pricing Transparency | [rating] | [rating] | [rating] | [rating] |
| Trust Signals | [rating] | [rating] | [rating] | [rating] |
| "Near Me" Strategy | [rating] | [rating] | [rating] | [rating] |

Ratings: Strong / Adequate / Weak / Not Found

## Opportunities

### Quick Wins (Implement This Week)
1. [specific action]
2. [specific action]

### Strategic Moves (This Quarter)
1. [specific action with rationale]
2. [specific action with rationale]

### Content Gaps to Fill
1. [blog topic competitors cover that PMax does not]
2. [blog topic competitors cover that PMax does not]

### Service Expansion Ideas
1. [service to consider adding, based on competitor demand signals]

## Threats to Monitor
1. [competitor activity to watch]
2. [market trend that could affect positioning]

## Recommended Actions (Priority Order)
1. [Highest impact action]
2. [Second highest]
3. [Third highest]
4. [Fourth]
5. [Fifth]

---
*Analysis by Performance MAX Agency*
*performancemaxagency.com | (404) 716-5444*
```

## Finding Competitors

If the user does not provide specific competitor URLs, search for competitors using:

```bash
# Search for local marketing agencies in target markets
curl -s "https://www.google.com/search?q=digital+marketing+agency+roswell+ga" # (use browser tool instead for better results)
curl -s "https://www.google.com/search?q=local+seo+company+shaker+heights+oh"
curl -s "https://www.google.com/search?q=google+ads+agency+atlanta+ga"
curl -s "https://www.google.com/search?q=performance+max+agency+near+me"
```

Prefer using the browser tool (Camofox) for search queries to get rendered results.

## Notes

- Be factual and specific — no vague statements like "they have a good website"
- Quote exact text from competitor sites when relevant (headlines, CTAs, claims)
- Always frame findings in terms of actionable intelligence for Performance MAX
- Acknowledge when PMax has an advantage, not just weaknesses
- If a competitor is clearly superior in an area, recommend specific steps to close the gap
