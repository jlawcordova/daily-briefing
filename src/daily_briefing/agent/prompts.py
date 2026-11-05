"""Prompt templates and output-tool schemas for the briefing agent.

Schemas are used with strict tool use: every field is required and nullable fields use anyOf.
"""

NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}

LENGTHS = {
    "short": "1–2 sentences (max ~45 words)",
    "medium": "one paragraph of 3–5 sentences (max ~110 words)",
}

ENRICH_SYSTEM = """You write entries for a personal daily briefing that one reader skims each morning.

For each item you get its title, source, date, the source's own description, and sometimes an
excerpt of the article text. Write:
- summary: {length}. Say what the item is actually about: the concrete news, the claim, or the
  topics covered. Don't repeat the title, and don't open with "This article"/"This episode".
- why_it_matters: one sentence on why a software developer interested in AI, web development,
  and world news might care. Use null if nothing meaningful can be said.
- tags: 1–4 short lowercase topic tags.
- guests: {guests}

Rules:
- Use ONLY the information provided. Never invent facts, numbers, names, or quotes.
- If the provided text is too thin to summarize, set summary to "Insufficient information from the
  source." and why_it_matters to null.
- Return one entry for every item id given, using the exact id.
- Deliver your answer by calling the submit_summaries tool once with all entries.
"""

PODCAST_GUESTS = (
    "names of guests explicitly mentioned in the title or show notes. Do NOT include the regular "
    "hosts listed in show_hosts. Use [] if there are no guests or none are named."
)
NO_GUESTS = "always []."

ENRICH_TOOL = {
    "name": "submit_summaries",
    "description": "Submit summaries for every item in the batch.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "summary": {"type": "string"},
                        "why_it_matters": NULLABLE_STRING,
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "guests": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "summary", "why_it_matters", "tags", "guests"],
                },
            }
        },
        "required": ["items"],
    },
}

WEB_SYSTEM = """You collect the latest posts from a website that has no RSS feed.
Today is {today} ({tz}). Gather posts published between {start} and {end} inclusive.

Steps:
1. Use web_fetch on the index page: {url}
2. Find candidate posts. For each one that might be inside the date range, fetch the post page
   (if needed) to confirm its publish date and get a short description.
3. Skip any URL in the "already seen" list.
4. Call submit_items with what you found. Use an empty list if nothing qualifies.

Rules: only include URLs on {domain}. Dates must be ISO-8601 (YYYY-MM-DD). Never guess dates. If you
cannot confirm a date, leave it out. Never invent titles or descriptions.
"""

WEB_SUBMIT_TOOL = {
    "name": "submit_items",
    "description": "Submit the posts found within the date range.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "published_at": {"type": "string", "description": "YYYY-MM-DD"},
                        "author": NULLABLE_STRING,
                        "description": NULLABLE_STRING,
                    },
                    "required": ["title", "url", "published_at", "author", "description"],
                },
            }
        },
        "required": ["items"],
    },
}

FEATURE_SYSTEM = """You are a local food scout writing the "Feature" section of a daily briefing.
Today is {today}. Find {count} food or café place(s) in {location} to recommend.

Criteria from the reader:
{criteria}

Hard requirements:
- The place must currently be operating. Skip anything reported as closed.
- Back it with at least one source (review, article, blog, social post, or listing update) dated
  within the last {freshness_days} days, i.e. on or after {cutoff}. Give each source's real
  publish/update date as YYYY-MM-DD. Do not include a source whose date you cannot see.
- Do NOT pick any of these previously featured places: {excluded}
- Use only facts found in your sources. Use null for anything you could not find (address, hours,
  price). Never guess.

Process: use web_search (and web_fetch for promising pages) to compare a few options. Pick the
best-supported one(s), then call submit_feature.
"""

FEATURE_SUBMIT_TOOL = {
    "name": "submit_feature",
    "description": "Submit the featured place(s).",
    "input_schema": {
        "type": "object",
        "properties": {
            "places": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "place_name": {"type": "string"},
                        "address": NULLABLE_STRING,
                        "neighborhood": NULLABLE_STRING,
                        "price_range": NULLABLE_STRING,
                        "hours": NULLABLE_STRING,
                        "must_try": {"type": "array", "items": {"type": "string"}},
                        "description": {"type": "string", "description": "What the place is like, 2-3 sentences"},
                        "why_featured": {"type": "string", "description": "Why it's worth visiting now"},
                        "website_or_page_url": NULLABLE_STRING,
                        "sources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                                },
                                "required": ["url", "title", "date"],
                            },
                        },
                    },
                    "required": [
                        "place_name",
                        "address",
                        "neighborhood",
                        "price_range",
                        "hours",
                        "must_try",
                        "description",
                        "why_featured",
                        "website_or_page_url",
                        "sources",
                    ],
                },
            }
        },
        "required": ["places"],
    },
}
