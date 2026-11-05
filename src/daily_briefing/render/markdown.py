"""Render a Briefing to Markdown."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from ..models import Briefing, Episode, Feature, ForumPost, Item, SourceResult
from ..util import format_duration

SECTIONS = [
    ("news", "🗞 News"),
    ("podcast", "🎧 Podcasts"),
    ("article", "📝 Articles"),
    ("forum", "💬 Forums"),
    ("feature", "🍽 Feature"),
]
STATUS_ICON = {"ok": "✅", "warn": "⚠️", "error": "❌", "skipped": "⏭"}
NOTHING_NEW = "_Nothing new since the last briefing._"


def esc(text: str) -> str:
    """Escape characters that break inline Markdown links/tables."""
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")


def quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def anchor(title: str) -> str:
    keep = "".join(c for c in title.lower() if c.isalnum() or c in " -")
    return keep.strip().replace(" ", "-")


class Renderer:
    def __init__(self, briefing: Briefing):
        self.b = briefing
        self.tz = ZoneInfo(briefing.timezone)

    def dt(self, value: datetime | None, with_time: bool = True) -> str:
        if not value:
            return "date unknown"
        local = value.astimezone(self.tz)
        return local.strftime("%Y-%m-%d %H:%M") if with_time else local.strftime("%Y-%m-%d")

    def ago(self, value: datetime | None) -> str:
        if not value:
            return ""
        secs = (self.b.generated_at.astimezone(UTC) - value.astimezone(UTC)).total_seconds()
        if secs < 3600:
            return f"{max(1, int(secs // 60))}m ago"
        if secs < 86400:
            return f"{int(secs // 3600)}h ago"
        return f"{int(secs // 86400)}d ago"

    # ------------------------------------------------------------------ items
    def ai_lines(self, item: Item) -> list[str]:
        lines = []
        if item.ai_summary:
            lines.append(f"- **AI summary:** {item.ai_summary}")
        elif self.b.ai_enabled:
            lines.append("- **AI summary:** _not generated (budget reached or error)_")
        if item.ai_why_it_matters:
            lines.append(f"- **Why it matters:** {item.ai_why_it_matters}")
        tags = item.ai_tags or [t for t in item.tags if t != "via agent"][:4]
        if tags:
            lines.append("- **Tags:** " + ", ".join(f"`{t}`" for t in tags))
        return lines

    def article(self, item: Item) -> list[str]:
        out = [f"#### [{esc(item.title)}]({item.url})"]
        meta = [f"**Published:** {self.dt(item.published_at)}"]
        if item.author:
            meta.append(f"**By:** {item.author}")
        if item.reading_time_min:
            meta.append(f"**Read:** ~{item.reading_time_min} min")
        out.append("- " + " · ".join(meta))
        if item.source_description:
            out.append(f"- **From the source:** {item.source_description.replace(chr(10), ' ')}")
        out += self.ai_lines(item)
        return out + [""]

    def episode(self, ep: Episode) -> list[str]:
        out = [f"#### [{esc(ep.title)}]({ep.url})"]
        rows = [("Published", self.dt(ep.published_at))]
        if ep.duration_seconds:
            rows.append(("Duration", format_duration(ep.duration_seconds) or ""))
        num = " · ".join(
            x for x in [f"S{ep.season}" if ep.season else "", f"E{ep.episode_number}" if ep.episode_number else ""] if x
        )
        if num:
            rows.append(("Episode", num))
        if ep.episode_type and ep.episode_type != "full":
            rows.append(("Type", ep.episode_type))
        if ep.hosts:
            rows.append(("Hosts", ", ".join(ep.hosts)))
        if ep.guests:
            rows.append(("Guests", ", ".join(ep.guests)))
        if ep.explicit:
            rows.append(("Explicit", "yes"))
        listen = [f"[Episode page]({ep.url})"]
        if ep.audio_url and ep.audio_url != ep.url:
            listen.append(f"[Audio]({ep.audio_url})")
        if ep.apple_url:
            listen.append(f"[Apple Podcasts]({ep.apple_url})")
        rows.append(("Listen", " · ".join(listen)))
        out += ["| | |", "|---|---|"] + [f"| {k} | {esc(v) if k != 'Listen' else v} |" for k, v in rows]
        out.append("")
        if ep.ai_summary:
            out.append(f"**AI summary:** {ep.ai_summary}")
            out.append("")
        if ep.ai_why_it_matters:
            out.append(f"**Why it matters:** {ep.ai_why_it_matters}")
            out.append("")
        if ep.ai_tags:
            out.append("**Tags:** " + ", ".join(f"`{t}`" for t in ep.ai_tags))
            out.append("")
        if ep.source_description:
            out += [
                "<details><summary>Show notes (from the episode)</summary>",
                "",
                ep.source_description,
                "",
                "</details>",
            ]
        return out + [""]

    def forum(self, idx: int, p: ForumPost) -> list[str]:
        domain = f" ({p.domain})" if p.domain else ""
        head = (
            f"{idx}. **[{esc(p.title)}]({p.url})**{domain} · ▲ {p.points} · "
            f"💬 [{p.comments} comments]({p.comments_url})"
        )
        if p.submitter:
            head += f" · by {p.submitter}"
        if p.published_at:
            head += f" · {self.ago(p.published_at)}"
        out = [head]
        if p.ai_summary:
            out.append(f"   > {p.ai_summary}")
        if p.ai_why_it_matters:
            out.append(f"   > _Why it matters:_ {p.ai_why_it_matters}")
        if p.reading_time_min:
            out.append(f"   > _~{p.reading_time_min} min read_")
        return out

    def feature(self, f: Feature) -> list[str]:
        out = [f"### {esc(f.place_name)}"]
        if f.source_description:
            out += [f.source_description, ""]
        loc = ", ".join(x for x in [f.address, f.neighborhood] if x) or "not found"
        out.append(f"- **Address / area:** {loc}" + (f" · [Map]({f.map_url})" if f.map_url else ""))
        out.append(f"- **Price range:** {f.price_range or 'not found'} · **Hours:** {f.hours or 'not found'}")
        if f.must_try:
            out.append("- **Must try:** " + ", ".join(f.must_try))
        if f.why_featured:
            out.append(f"- **Why it's featured:** {f.why_featured}")
        if f.url:
            out.append(f"- **Page:** {f.url}")
        if f.sources:
            refs = ", ".join(f"[{esc(s.title)} ({s.date})]({s.url})" for s in f.sources)
            out.append(f"- **Sources (recent):** {refs}")
        return out + [""]

    # ---------------------------------------------------------------- section
    def source_block(self, r: SourceResult) -> list[str]:
        out = [f"### {esc(r.name)}"]
        if r.show and (r.show.author or r.show.genre):
            bits = [x for x in [r.show.author, r.show.genre] if x]
            out.append(f"_{' · '.join(bits)}_")
            out.append("")
        if r.status == "error":
            return out + [f"_Could not fetch this source: {r.notes}_", ""]
        if not r.items:
            return out + [NOTHING_NEW, ""]
        if r.category == "forum":
            for i, p in enumerate(r.items, 1):
                out += self.forum(i, p)  # type: ignore[arg-type]
            return out + [""]
        for item in r.items:
            if isinstance(item, Episode):
                out += self.episode(item)
            else:
                out += self.article(item)
        return out

    def render(self) -> str:
        b = self.b
        gen = b.generated_at.astimezone(self.tz)
        total = sum(len(r.items) for rs in b.sections.values() for r in rs)
        day = datetime.fromisoformat(b.date).strftime("%A, %-d %B %Y")
        lines = [
            f"# Daily Briefing — {day}",
            f"_Generated {gen.strftime('%H:%M')} {b.timezone} (all times local) · {total} new items · "
            f"model `{b.model}` · est. AI cost ${b.cost_usd:.2f}_",
            "",
        ]
        if not b.ai_enabled:
            lines += ["> ℹ️ AI enrichment was disabled for this run (no summaries or feature).", ""]
        if b.budget_exhausted:
            lines += ["> ⚠️ The AI budget was reached; some items have no AI summary.", ""]

        toc = []
        for key, title in SECTIONS:
            if key in b.sections:
                n = sum(len(r.items) for r in b.sections[key])
                toc.append(f"[{title.split(' ', 1)[1]}](#{anchor(title)}) ({n})")
        lines += ["## Contents", "- " + " · ".join(toc), ""]

        for key, title in SECTIONS:
            results = b.sections.get(key)
            if results is None:
                continue
            lines += [f"## {title}", ""]
            if key == "feature":
                for r in results:
                    if r.status in ("error", "skipped"):
                        lines += [f"_No feature today: {r.notes}_", ""]
                    for f in r.items:
                        lines += self.feature(f)  # type: ignore[arg-type]
                continue
            if not results:
                lines += [NOTHING_NEW, ""]
            for r in results:
                lines += self.source_block(r)

        lines += [
            "---",
            "## Run report",
            "| Source | Section | Status | Fetched | New | Notes |",
            "|---|---|---|---|---|---|",
        ]
        for key, _ in SECTIONS:
            for r in b.sections.get(key, []):
                notes = esc(r.notes.replace("\n", " "))[:200]
                lines.append(f"| {esc(r.name)} | {key} | {STATUS_ICON[r.status]} | {r.fetched} | {r.new} | {notes} |")
        return "\n".join(lines).rstrip() + "\n"


def render_markdown(briefing: Briefing) -> str:
    return Renderer(briefing).render()
