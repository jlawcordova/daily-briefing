# CLAUDE.md

The daily briefing (Python, `src/daily_briefing`) and the pixel art of J. Law's Daily Brief page (`art/`, made
with Pixpocket). `README.md` has the setup and the commands.

## The briefing

- `uv sync`, `uv run pytest`, `uv run ruff check src tests`, `uv run ruff format --check src tests`.
- `uv run python -m daily_briefing validate --config config/briefing.yaml` checks the config.

## The art

- Read the `pixel-art-style` skill (`.claude/skills/pixel-art-style/SKILL.md`) before drawing or changing art.
  It's the house style and the owner's rules. When the owner reacts to how something looks, add the rule there.
- Pixpocket is pinned in `.pixpocket-version`; `scripts/install-pixpocket.sh` installs it into `.tools/`.
  The generators use that copy and refuse another version.
- The art is generated: edit `art/generators/`, never the JSON in `art/daily-brief.pixpocket/`, then
  `python3 art/generators/build.py` (builds, checks, rulers and publishes into `art/build/`, gitignored).
- Run `pixpocket` from `art/`, where it finds the document. Leave `PIXPOCKET_DOC` and `PIXPOCKET_SITE` unset.
- Never commit `art/build/`, `.tools/`, rendered images or video.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
