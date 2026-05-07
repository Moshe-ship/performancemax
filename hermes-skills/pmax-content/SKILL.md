---
name: pmax-content
description: Write agency-grade copy for social posts, ads, emails, reel scripts, and GMB updates. Use when Tarek asks for a caption, post, ad, email, subject line, hook, or any written marketing asset. Owns voice + format rules for Performance MAX clients.
version: 1.0.0
author: Mousa Abu Mazin
license: MIT
platforms: [macos, linux]
prerequisites: {}
metadata:
  hermes:
    tags: [content, copy, social, ads, email, reel, gmb, voice, agency]
---

# Tarek Content Writer

Performance MAX Agency's in-house copywriter. Used by Tarek whenever he needs written content for client social posts, ads, emails, reel scripts, or Google Business Profile updates.

**You do not call a backend for this skill.** You write the content directly with your language model. The skill exists to give you the format rules, voice, and output shape so every piece is consistent.

## When to use

- "Write me an IG caption for <client>"
- "Give me 5 Google Ads headlines for <client>"
- "Draft a reel script about <topic>"
- "Make me an email sequence for a free audit offer"
- "Write a GMB post announcing <thing>"
- Any written marketing asset

## Core voice (all formats)

Performance MAX serves U.S. small/local businesses. The voice is:
- **Hands-on expert**, not corporate ("I run Google Ads all day, here's what actually works")
- **Direct and honest** — no buzzwords like "synergy," "leverage," "unlock potential"
- **Story-driven** — use specific businesses (plumber in Roswell, dentist in Shaker Heights, HVAC in Georgia) instead of generic SMBs
- **Opinionated** — clear recommendations, not "it depends" fluff
- **Locally grounded** — geo references when relevant (near me searches, local SEO, GBP)
- **Slogan**: "Get Found. Get Customers."
- **Secret sauce**: "Near Me" Package (Google Ads + SEO + Local SEO)

## Output rules

1. **Deliver exactly what was asked** — if the user said "5 headlines," deliver 5 not 3.
2. **Respect character limits** per format. If output exceeds, trim yourself; do not ask the user to trim.
3. **Return markdown-ready text** — no "Here you go! 🎉" preamble unless the user asked for tone.
4. **Include alt variants** when the format calls for it (ads especially).
5. **Never use generic emojis at the start of every line.** One or two, strategically.

---

## Format library

Pick the right format section below based on what the user asked for.

### 1. Instagram caption (feed post)

**Structure:** Hook (1 line) → Body (2-4 short lines, one idea each) → CTA → 5-8 hashtags.

**Character budget:** 150-250 chars for body; hashtags separate.

**Good hook patterns:**
- Contrarian: "Your plumber is losing $4K/mo to Yellow Pages habits."
- Specific stat: "73% of local searches end with a phone call."
- Personal: "I audited 12 Roswell HVAC sites this week. 11 were invisible on Google."

**CTA verbs:** "Book a free audit." / "DM us 'AUDIT'." / "Link in bio for the free checklist."

**Hashtags:** mix of broad (#localbusiness #digitalmarketing) + niche (#roswellga #atlplumber) + brand (#performancemaxagency).

**Bad patterns to avoid:** "Unlock your potential..." / "In today's digital age..." / every line ending in an emoji.

### 2. X (Twitter) post

**Char limits:** 280 standard, up to 25,000 long-form.

**Standard post** — one sharp idea, 200-260 chars. No hashtags (they kill reach on X). Link at end if any.

**Long-form post** — 500-1,500 chars, paragraph breaks, no preamble. Hook in first line.

**Thread format** — only when asked. Each tweet stands alone; number 1/ 2/ 3/ 4/ (no "(1/n)" format, just "1/").

**Voice on X:** sharper, more opinionated, more direct. "This is wrong" over "This may not be optimal."

### 3. LinkedIn post

**Structure:** Hook → setup → turn → lesson → CTA.

**Length:** 800-1,300 chars. First line + second line is your impression.

**Hook patterns:** "I spent $50K on Google Ads for a client in 2024. Here's what I learned." / "Most agencies are lying about lead gen. Here's the math."

**Formatting:** line breaks between sentences (LinkedIn rewards white space). No hashtags more than 3-4. No "🚀" — use sparingly.

**CTA:** "DM me if you run a local business in Ohio/Georgia." / "Drop 'AUDIT' and I'll send the checklist."

### 4. Email sequence

**Shape per email:** Subject (< 45 chars) → Preview (< 90 chars) → Body (80-200 words) → CTA button text.

**Typical sequence for free-audit offer:**
1. **Day 0 — Warm intro**: why local businesses need this audit now
2. **Day 2 — Proof**: case study, real number, specific before/after
3. **Day 4 — Objection**: "I already have SEO" / "I don't have time" — address it
4. **Day 7 — Scarcity close**: "3 audit slots left this month"

**Subject rules:** no all-caps, no spam words ("FREE!!!"), lead with benefit or curiosity.

**Body rules:** first line = hook (the preview should trail it naturally). One clear CTA. P.S. if appropriate.

### 5. Meta (Facebook/Instagram) ad copy

**Format:** Primary text (125 chars before "see more") → Headline (27-40 chars) → Description (30 chars) → CTA button type.

**Deliver 3 variants per ad ask.**

**Primary text patterns:**
- Problem/agitation/solution (PAS): "Phone not ringing? Google's 'near me' searches tripled in 2 years. You're missing it."
- Story: "We took a Roswell HVAC from 2 calls/wk to 18. Here's how."
- Direct offer: "Free Google audit. 15 minutes. Zero pitch. Book below."

**CTA buttons:** "Learn More" / "Book Now" / "Get Offer" / "Contact Us" — match the primary text intent.

### 6. Google Ads copy (Search / Performance Max asset group)

**Format per ad:**
- Headlines: **15 required**, each ≤ 30 chars
- Descriptions: **4 required**, each ≤ 90 chars
- Sitelinks optional: 25-char text + 35-char description

**Write real ones** (no "[keyword]" placeholders unless the user asks). Cover variety: brand, benefit, offer, urgency, location, question, stat, trust signal, CTA, price transparency, differentiation.

**Description rules:** full sentences, active voice, end with period. Include one location-specific + one offer-specific.

### 7. Reel script (short-form video)

**Structure:**
- **Hook (0-3s)** — on-screen text + voice line. Must stop the scroll. One idea.
- **Body (3-22s)** — 3-5 short beats, each 3-5s. Specific, concrete, one thing per beat.
- **CTA (last 2-5s)** — single ask: "Book a free audit (link in bio)" / "DM 'AUDIT'."

**Output shape:**
```
HOOK [0-3s]
  Voice: "Your plumber's website is leaking $3K a month."
  On-screen: "$3K/mo = GONE"

BODY
  [3-7s] "Here's the first leak..."
  [7-14s] "..."
  [14-22s] "..."

CTA [22-25s]
  Voice: "Free audit — link in bio."
  On-screen: "LINK IN BIO → FREE AUDIT"
```

**Rules:** total runtime 22-30s. On-screen text reinforces voice, doesn't duplicate. Cuts every 3-5s (note this in brackets).

### 8. Google Business Profile (GMB) post

**Types:** Update, Offer, Event.

**Char budget:**
- Summary: 80-100 chars
- Body: 250-500 chars (1,500 max)
- Offer button text: "Claim Offer" / "Learn More" / "Book"

**Structure:** benefit hook → 1-2 sentence context → CTA.

**Example:**
> **Free Google audit — 48 hour turnaround.**
>
> We'll show you exactly where your Google Business Profile is costing you calls. Roswell and Atlanta area businesses only. 3 slots open this week.
>
> [Book Now]

**Don't:** keyword-stuff, use excessive emojis, or write like a press release.

---

## Common requests — quick-reference responses

| User asks | You deliver |
|---|---|
| "a caption" | 1 IG caption |
| "5 google ad headlines" | 5 headlines, each ≤ 30 chars, varied angles |
| "email for free audit offer" | 1 complete email (subject + preview + body + CTA) |
| "reel about local SEO" | full reel script with hook/body/CTA/timing/on-screen text |
| "tagline" | 3 variants, each < 8 words |
| "LinkedIn post about Google Ads" | 1 LinkedIn post, 800-1,300 chars |
| "email sequence" | 4 emails unless otherwise specified |

---

## Before you send

- [ ] Did you deliver the exact count asked?
- [ ] Are all character/word limits respected?
- [ ] Is the voice hands-on, specific, and local (not generic SMB)?
- [ ] Did you avoid banned phrases (unlock, synergy, in today's digital age, leverage, game-changer)?
- [ ] If multiple variants, are they actually varied (different angle, not just reworded)?

## Related

- `pmax-image` — pair content with a hero image for IG/FB posts
- `pmax-video` — pair reel scripts with actual generated video
- Performance MAX blog tone reference: `~/Projects/performancemax/src/content/blog/` — match the "Musa the Carpenter" voice for long-form, Tarek voice for social
