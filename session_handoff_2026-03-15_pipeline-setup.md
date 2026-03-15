# Session Handoff — 2026-03-15 — Pipeline Setup & Infrastructure

## What Got Done
- **Landing page**: `index.html` (root) — live on Netlify
- **First guide**: `houston-dynamo/index.html` (1108 lines) — Rodeo Night vs Portland, public/shareable version
- **Generation pipeline scaffolded**: `pipeline/` directory — 6 Python modules (config.py, roster.py, research.py, caricature.py, assemble.py, generate.py)
- **GitHub Actions workflow**: `.github/workflows/generate-guide.yml` — supports manual dispatch AND Monday 9am CT cron
- **3 Texas teams configured**: Houston Dynamo, FC Dallas, Austin FC in `pipeline/config.py`
- **Schedule checker**: `pipeline/schedule.py` — fetches MLS schedules, identifies home games only (saves tokens)
- **Opponent scouting**: `pipeline/opponents.py` — researches 3 opposing players per match, builds `data/opponents.json` database over time
- **Community corrections system**: `houston-dynamo/corrections.json` — seeded with Ponce wife IG fix
- **DNS configured on GoDaddy**: A record → 75.2.60.5 (Netlify), www CNAME → dynamic-stroopwafel-00a3e5.netlify.app
- **Memories updated**: `project_girlfriendguide.md` and `feedback_girlfriendguide_tone.md` in Claude memory
- **Branch merged**: `claude/progress-update-ew6cg` merged to main, CNAME file removed (we use Netlify, not GitHub Pages)

## Exact State of In-Progress Work
- **Netlify ↔ GitHub link: NOT DONE.** The Netlify project is still deployed from "Netlify Drop" (manual drag-and-drop). The GitHub button on the "Link repository" page (`/projects/dynamic-stroopwafel-00a3e5/link`) requires OAuth — user must click it themselves. Currently at Step 1 of 3 ("Connect to Git provider").
- **DNS propagation: IN PROGRESS.** Records are correct at GoDaddy nameservers (`dig @ns03.domaincontrol.com girlfriendguide.gg A` returns `75.2.60.5`). But the `.gg` TLD root nameservers are still returning NXDOMAIN — the registry hasn't propagated the delegation yet. Expected to resolve within 24-48 hours for a new `.gg` domain.
- **Instagram MCP: BROKEN BUILD.** Cloned `duhlink/instagram-server-next-mcp` to `~/.claude-mcp-servers/instagram-mcp` but it has TypeScript build errors (missing `ps-list` types, `getConfig` API mismatch). Not yet added to Claude Code settings. Needs fix or alternative approach.
- **Pipeline: SCAFFOLDED, NOT TESTED.** All modules have code but none have been run end-to-end. No API keys are set as GitHub secrets yet.

## Decisions Made This Session
| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Use Netlify (not GitHub Pages) for hosting | DNS already configured, Netlify supports forms (future corrections), custom build commands | GitHub Pages — simpler but less flexible, would need 4 different A records |
| Perplexity for BOTH research AND image generation (Nano Banana) | Already paying for Perplexity, single API key, single bill | Separate Gemini API key for images — adds another billing relationship |
| Two-pass Perplexity research (research + verification) | Solves the Brittany Ulrich factual accuracy problem — second pass catches errors from first | Single pass — cheaper but error-prone |
| Positive tone rule — "would the player repost this?" test | Players will see the guides. First prototype led with Héctor Herrera's divorce (old, negative) | Allow all public info — too negative for the brand |
| Home games only in automated pipeline | People at the game are the audience; away games waste tokens | Generate for all games — 2x the cost, half the value |
| 3 Texas teams (Houston, Dallas, Austin) | Geographic proximity, shared audience, manageable scope | All MLS — too many teams to start |

## Key Numbers Established or Used
| Number | Context | Source |
|--------|---------|--------|
| 75.2.60.5 | Netlify A record IP for girlfriendguide.gg | Netlify domain management page |
| dynamic-stroopwafel-00a3e5.netlify.app | Netlify subdomain / www CNAME target | Netlify dashboard |
| ~$2-3 per guide | Perplexity API cost for player research | Estimated from sonar-pro pricing |
| ~$1.50 per guide | Claude API cost for HTML assembly | Estimated from Sonnet pricing |
| ~$5 per guide total | Combined API cost per team per week | Sum of above |
| $18-20/week | Estimated total for 3 teams | $5 × 3 teams + overhead |
| 1108 lines | Length of houston-dynamo/index.html | File created this session |

## Conditional Logic in Effect
- IF scheduled run (Monday cron) THEN check all 3 Texas teams for home games, generate only for teams with upcoming home games (matrix strategy)
- IF manual dispatch THEN generate for the specified team/opponent/date only
- IF a player claim has low confidence (sources disagree) THEN add qualifier ("reportedly") or drop the claim entirely
- IF a correction exists in `corrections.json` THEN apply it BEFORE Perplexity research (avoids re-discovering wrong info)
- IF old breakup/divorce (>2 weeks old) THEN omit from guide. Only include if genuinely breaking news.

## Open Questions (NOT Resolved)
- [ ] Should Perplexity or Gemini handle caricature generation? User said Perplexity can do Nano Banana — need to verify their API supports image generation
- [ ] What email address for girlfriendguide.gg? Options discussed: Google Workspace ($7/mo), Zoho (free), or simple forwarding (free). User hasn't chosen.
- [ ] Instagram MCP approach — fix duhlink build, use Apify MCP, or build lightweight Playwright-based one?
- [ ] Public version section reorder — should "Big Names" lead instead of "Young Ones"? Discussed in prior session but not implemented
- [ ] Perplexity API — does the user's plan include API access, or is it web-only?

## Next Session: Do This First
1. **Link Netlify to GitHub** — user must click the GitHub OAuth button at `app.netlify.com/projects/dynamic-stroopwafel-00a3e5/link`, then select `ChasFletch/girlfriend-guide` repo, branch `main`
2. **Check DNS propagation** — run `dig girlfriendguide.gg A` to see if `.gg` registry has propagated. If yes, verify SSL on Netlify domain management page.
3. **Add API keys as GitHub repo secrets** — PERPLEXITY_API_KEY, GEMINI_API_KEY (or skip if using Perplexity for images), ANTHROPIC_API_KEY
4. **Create fc-dallas/ and austin-fc/ directories** with initial `corrections.json` files
5. **Test pipeline manually** — run `python pipeline/generate.py --team houston-dynamo --opponent "Portland Timbers" --date 2026-03-14` locally
6. **Address Perplexity image generation** — verify API supports Nano Banana, update `caricature.py` if switching from Gemini

## Files to Read on Resume
- `/Users/charlesfletcher/.claude/projects/-Users-charlesfletcher/memory/project_girlfriendguide.md` — project overview and infrastructure
- `/Users/charlesfletcher/.claude/projects/-Users-charlesfletcher/memory/feedback_girlfriendguide_tone.md` — positive tone rules
- `/Users/charlesfletcher/girlfriend-guide/session_handoff_2026-03-15_pipeline-setup.md` — this file
- `/Users/charlesfletcher/girlfriend-guide/pipeline/config.py` — team configs, API keys, prompt templates
- `/Users/charlesfletcher/girlfriend-guide/.github/workflows/generate-guide.yml` — GitHub Actions workflow
