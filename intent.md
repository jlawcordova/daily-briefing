# Intent: Daily Briefing

## Why
I follow news outlets, podcasts, AI/dev blogs, and tech forums. Checking each one by hand every day is slow, and I end up seeing the same items again or missing new ones. I want **one daily document** that collects what's new from all of them, with enough detail that I can decide what to read or listen to without opening every link.

## What I want
- **One YAML config** that lists exactly what to collect. Adding, removing, or changing a source should mean editing the YAML only, not code.
- **Source categories:**
  - **News outlets**: e.g. BBC, The New York Times.
  - **Podcasts**: e.g. Syntax (syntax.fm) and Soft Skills Engineering (softskills.audio). Each is given by name plus a URL (Apple Podcasts/iTunes link, the show's own site, or an RSS feed), with a date window for which episodes count.
  - **Articles/blogs**: e.g. claude.dev (tips, tricks, and POVs from Anthropic's developers) and the OpenAI blog.
  - **Forums**: e.g. Hacker News (news.ycombinator.com).
  - **Feature**: a recommended food/café place in Davao City, backed by sources from the last 12 months.
- **No repeats.** An item (episode, article, post, featured place) that appeared in an earlier briefing must not show up again. The record of what has been shown is kept in a private GitHub Gist rather than the repo.
- **Runs automatically in GitHub Actions** every day at 06:00 Manila time, and can also be started by hand.
- **An AI agent built on Claude** (I supply an Anthropic API key from the Claude Console as a GitHub secret). It reads the config, gets the data, and writes the summaries.
- **The output is a Markdown file** uploaded as a GitHub Actions artifact.
- **As much detail as possible for each item.** For a podcast episode that means: title, publish date, duration, link, the show's own description, a short summary written by the agent, and any other metadata available. Other item types get the same level of detail.

## What success looks like
- Each morning there is a `briefing-YYYY-MM-DD.md` artifact I can open and skim in a few minutes.
- Nothing in it repeats a previous day's briefing.
- I can add a new podcast or blog by adding about 4 lines of YAML.
- If one source fails, the briefing is still produced, and the failure is reported in it.
- The run costs a predictable, small amount of API money.

## Non-goals (for now)
- No web UI, email, or push notifications. The artifact is the only output. Delivery can be added later.
- No paywall bypassing. For paywalled outlets like NYT, use public RSS headlines and descriptions only.
- No transcription of podcast audio.
- No multi-user support.
