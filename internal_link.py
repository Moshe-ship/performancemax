#!/usr/bin/env python3
"""Inject contextual internal links into pmax blog markdown posts. Idempotent:
never links a URL already present, never self-links, skips frontmatter/headings/
code/existing links. Caps per post.  Usage: internal_link.py <file.md> | --all"""
import re, sys, pathlib
BLOG = pathlib.Path(__file__).parent / "src/content/blog"

# (phrase, url) most-specific first. Broad phrases + synonyms so real prose matches.
REGISTRY = [
    ("performance max campaign", "/blog/what-is-performance-max-campaign-google-ads"),
    ("google ai overviews", "/blog/google-ai-overviews-local-business-seo-2026"),
    ("ai overviews", "/blog/google-ai-overviews-local-business-seo-2026"),
    ("google business profile", "/blog/google-business-profile-optimization-guide"),
    ("map pack", "/blog/7-ways-to-get-more-customers-from-google-maps-in-2026"),
    ("google maps", "/blog/7-ways-to-get-more-customers-from-google-maps-in-2026"),
    ("voice search", "/blog/how-to-optimize-your-local-business-for-voice-search-in-2026"),
    ("schema markup", "/blog/schema-markup-for-local-businesses-the-invisible-seo-ranking-factor-you-are-ignoring"),
    ("structured data", "/blog/schema-markup-for-local-businesses-the-invisible-seo-ranking-factor-you-are-ignoring"),
    ("nap consistency", "/blog/local-citations-and-nap-consistency-the-hidden-local-seo-ranking-factor-most-businesses-ignore"),
    ("local citations", "/blog/local-citations-and-nap-consistency-the-hidden-local-seo-ranking-factor-most-businesses-ignore"),
    ("link building", "/blog/the-ultimate-guide-to-local-link-building-for-small-businesses"),
    ("backlinks", "/blog/the-ultimate-guide-to-local-link-building-for-small-businesses"),
    ("cost per click", "/blog/the-real-cost-per-click-for-local-businesses-in-2026-and-how-to-pay-less"),
    ("email marketing", "/blog/email-marketing-system-for-local-businesses-2026"),
    ("social media", "/blog/social-media-marketing-for-local-businesses-which-platforms-actually-drive-customers"),
    ("how much does local seo cost", "/blog/how-much-does-local-seo-cost-a-2026-pricing-guide-for-small-"),
    ("online reviews", "/blog/how-to-get-more-online-reviews-for-your-local-business"),
    ("google reviews", "/blog/how-to-get-more-online-reviews-for-your-local-business"),
    ("customer reviews", "/blog/how-to-get-more-online-reviews-for-your-local-business"),
    ("local seo vs organic", "/blog/local-seo-vs-organic-seo-what-local-businesses-need-to-know"),
    ("lead generation", "/blog/stop-chasing-leads-how-to-build-a-local-lead-machine-that-ru"),
    ("marketing budget", "/blog/stop-burning-your-marketing-budget-"),
    ("conversion rate", "/blog/turn-website-visitors-into-paying-customers-conversion-optimization-guide"),
    ("conversion optimization", "/blog/why-your-local-business-website-is-leaking-money-the-ultimate-guide-to-cro-for-local-services"),
    ("local competitors", "/blog/how-to-spy-on-your-local-competitors-legally-and-steal-their-customers"),
    ("competitors", "/blog/how-to-spy-on-your-local-competitors-legally-and-steal-their-customers"),
    ("google ads", "/blog/google-ads-mistakes-local-businesses"),
    ("paid ads", "/blog/google-ads-mistakes-local-businesses"),
    # money pages
    ("near me", "/near-me"),
    ("local seo", "/services"),
]
MAX_LINKS = 4
PROTECT = re.compile(r'(```.*?```|`[^`]*`|!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)|^#{1,6}\s.*$)',
                     re.DOTALL | re.MULTILINE)

def split_fm(t):
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', t, re.DOTALL)
    return (m.group(1), m.group(2)) if m else ("", t)

def link_body(body, self_url):
    parts = PROTECT.split(body)
    used = set(u.rstrip('/') for u in re.findall(r'\]\((/[^)]*)\)', body))
    added = 0
    for phrase, url in REGISTRY:
        if added >= MAX_LINKS: break
        if url.rstrip('/') in used or url == self_url: continue
        pat = re.compile(r'(?<![\w/\-])(' + re.escape(phrase) + r')(?![\w\-])', re.IGNORECASE)
        for i in range(0, len(parts), 2):
            if not parts[i]: continue
            new, n = pat.subn(lambda m: f'[{m.group(1)}]({url})', parts[i], count=1)
            if n:
                parts[i] = new; used.add(url.rstrip('/')); added += 1; break
    return "".join(parts), added

def process(path):
    fm, body = split_fm(path.read_text())
    nb, added = link_body(body, f"/blog/{path.stem}")
    if added: path.write_text(fm + nb)
    return added

if len(sys.argv) < 2: sys.exit("usage: internal_link.py <file.md> | --all")
if sys.argv[1] == "--all":
    tot = lk = 0
    for f in sorted(BLOG.glob("*.md")):
        n = process(f); tot += 1
        if n: lk += n
    print(f"done: {lk} links across {tot} posts")
else:
    p = pathlib.Path(sys.argv[1]); print(f"+{process(p)} links -> {p.name}")
