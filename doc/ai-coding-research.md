# Research: How to Use AI Coding Agents Effectively

Research compiled from official Anthropic docs, Boris Cherny (Claude Code creator), Peter Steinberger (OpenClaw creator), Armin Ronacher, Simon Willison, incident.io, thoughtbot, and community blogs. Compiled 2026-02-14.

---

## 0. Peter Steinberger's Workflow (Creator of OpenClaw, 200+ commits/day)

**Who:** Peter Steinberger (@steipete), Vienna/London. Previously founded PSPDFKit (bootstrapped to millions ARR, exited). Came out of retirement to build AI tools. Created OpenClaw (193k GitHub stars, 9,887 commits, 300k LOC TypeScript).

**Velocity:** 6,600+ commits in January 2026. Peak: 600 commits in a single day. Runs 3-8 AI agents simultaneously in a 3x3 terminal grid.

**Blog:** https://steipete.me/ (treasure trove of practical AI dev insights)

### Key Blog Posts

**"Just Talk To It" (Oct 2025)** - https://steipete.me/posts/just-talk-to-it

His most detailed workflow post. Key techniques:

- **Prompt strategy:** Short, concise prompts (1-2 sentences + screenshot). Includes screenshots for 50%+ of prompts. Adds trigger words for hard tasks: "take your time," "comprehensive," "read all related code."
- **AGENTS.md:** ~800 lines, symlinked to claude.md. Contains product explanation, naming patterns, API preferences, React Compiler guidance, Tailwind 4 notes, database migration patterns, design system specs, AST-grep rules. He calls it "organizational scar tissue" built iteratively.
- **Slash commands (used sparingly):**
  - `/commit` - specifies "only commit your own changes" (prevents cross-agent conflicts)
  - `/automerge` - processes one PR at a time, reacts to bot comments, squashes when CI passes
  - `/massageprs` - like automerge without squashing, enables parallelization
  - `/review` - GitHub integration
- **Refactoring:** Allocates ~20% of time. Uses `jscpd` (code duplication), `knip` (dead code), `eslint` React Compiler plugin, `ast-grep` as git hook to block commits with violations.
- **What he dismissed:** "Don't waste your time on stuff like RAG, subagents, Agents 2.0 or other things that are mostly just charade."
- **Cost:** ~$1k/month for 4 OpenAI + 1 Anthropic subscription (unlimited tokens). API would be 5-10x more.

**"My Current AI Dev Workflow" (Aug 2025)** - https://steipete.me/posts/2025/optimal-ai-development-workflow

- **Tool rejections:** VS Code terminal too unstable ("plenty of freezes pasting large text"). Zed dismissed for terminal appearance. **Worktrees slowed him down** despite enabling parallel work. Removed last MCP because Claude spun up Playwright unnecessarily.
- **Agent scaling rule:** 1-2 agents for refactoring/focused work. ~4 agents for cleanup/tests/UI (his "sweet spot"). Scaling depends on work's "blast radius."
- **CLI integration:** "Pick services that have CLIs: vercel, psql, gh, axiom. Agents can use them, one line in CLAUDE.md is enough."
- **Testing insight:** "Automated tests usually aren't great, but the model almost always finds issues when you ask it to write tests IN THE SAME CONTEXT. Context is precious, don't waste it."
- **Hard problems that still need humans:** Distributed system design, dependency selection, platform architecture, forward-thinking database schema design.

**"Claude Code is My Computer" (Jun 2025)** - https://steipete.me/posts/2025/claude-code-is-my-computer

- Uses `cc="claude --dangerously-skip-permissions"` as shell alias
- Converted 40 Jekyll posts to MDX in 20 minutes
- Git through natural language: "commit everything in logical chunks"
- Paradigm shift: "Instead of 'I need to write a bash script to process these files,' I think 'organize these files by date and compress anything older than 30 days.'"

**"Shipping at Inference-Speed" (Dec 2025)** - https://steipete.me/posts/2025/shipping-at-inference-speed

- Commits directly to main without branching, rarely reverts
- "I don't read much code anymore" - Architecture understanding supersedes line-level review
- **Abandoned:** Plan mode ("feels like a hack for older models"), slash commands ("inconsistent with natural typing"), issue trackers ("important ideas executed immediately; others not worth recording"), session checkpointing/worktrees ("too much cognitive overhead for solo work")
- **Language picks:** Go for CLIs (agents excel, simple type system), Swift for macOS/iOS, TypeScript for web, Zig for low-level
- "Most software does not require hard thinking. Most apps shove data from one form to another."

**"Slot Machines for Programmers" (Jun 2025)** - https://steipete.me/posts/2025/when-ai-meets-madness-peters-16-hour-days

- **SDD (Software Design Document) approach:** Brain dump ideas into 500-line SDD using Google AI Studio. Iterate with "Take this SDD apart" prompts for 3-5 rounds. Feed completed spec.md to Claude Code with "Build spec.md." Let system run hours uninterrupted.
- **20x productivity claim:** Built analytics service (Sparkle) in 4 hours. Mac app release automation in 3 days. Rebuilt a 100-person company's fitness app in 2 afternoons.
- **Prompting philosophy:** Dismisses elaborate prompting guides as "bullshit." Explain goals from multiple angles using natural rambling. Redundancy helps clarification, not confusion.
- **Quote:** "They're non-predictable. It's like nature. If you don't like the outcome, just try it again."

### OpenClaw's Skill System & Agent Scripts

**Skill structure:**
- Skills stored in `~/.openclaw/workspace/skills/<skill>/SKILL.md`
- Format: SKILL.md (required, <500 lines, index), references/, scripts/, assets/
- **ClawHub marketplace:** 3,000+ community skills at https://clawhub.ai/
- Install: `clawhub install my-skill` or `npx clawhub@latest install my-skill`
- Publish: `clawhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.2.0`

**Steinberger's own agent-scripts repo** (https://github.com/steipete/agent-scripts):
- 16 skills: 1password, brave-search, create-cli, domain-dns-ops, frontend-design, instruments-profiling, markdown-converter, native-app-performance, openai-image-gen, oracle, swift-concurrency-expert, swiftui-liquid-glass, swiftui-performance-audit, swiftui-view-refactor, video-transcript-downloader, nano-banana-pro
- Slash commands in: `~/.codex/prompts/` (global) and `docs/slash-commands/` (repo-local)
- Common slash commands: `/handoff` and `/pickup` (for transferring work between sessions)
- **Ralph supervisor loop:** Orchestrates multi-step workflows by launching Claude with supervisor directives. Responses must terminate with control tokens (CONTINUE, SEND, RESTART).

**Skill example - swift-concurrency-expert:**
```
Description: "Swift Concurrency review and remediation for Swift 6.2+"
Workflow: Triage -> capture diagnostics -> identify actor context -> apply smallest safe fix
References: references/swift-6-2-concurrency.md, references/swiftui-concurrency-tour-wwdc.md
```
Skills are scoped, focused, and reference external docs rather than inlining everything.

**Workspace files:**
- **AGENTS.md** -- Agent config (~800 lines, symlinked to CLAUDE.md)
- **SOUL.md** -- Personality and behavioral directives
- **USER.md** -- User preferences and context
- **MEMORY.md** -- Persistent memory across sessions

### Steinberger's Key Principles

1. **Just talk to it.** Develop intuition through practice. Short prompts + screenshots > elaborate instructions.
2. **Atomic commits.** Each agent commits only files it touched. Prevents cross-agent conflicts.
3. **Blast radius thinking.** Before any change: how long will it take? How many files will it touch? Scope accordingly.
4. **Parallel by default.** 3-8 agents simultaneously. Don't wait for one to finish.
5. **20% cleanup rule.** Spend 1/5 of agent time on: dead code (knip), duplication (jscpd), deps, linting.
6. **Voice input + AI formatting.** Wispr Flow for dictation, Claude structures output.
7. **Simplify tooling.** Removed MCP servers, worktrees, plan mode. If "read the code" is faster, do that.
8. **SDD-first for big features.** Brain dump -> 3-5 rounds of AI iteration -> feed spec to agent.
9. **Tests in same context.** Write tests after features in the same conversation for best results.
10. **"If you don't like the outcome, try again."** Non-determinism is a feature; re-run with same prompt.

### What He Tried and Abandoned
- Git worktrees (slower than single folder)
- Multiple dev servers (resource-heavy)
- Plan mode ("hack for older models")
- Elaborate prompting (natural rambling is better)
- Subagents ("prefers separate terminals for visibility/control")
- Most MCPs (GitHub MCP alone = 23k token cost)
- RAG for codebase context
- Issue trackers ("execute or forget")
- Spec-driven development (slower than iterative)
- Claude Code plugins ("marketing checkbox")

### Community Reception

- Featured on Lex Fridman Podcast (#491), The Pragmatic Engineer newsletter
- Quote from Pragmatic Engineer interview: "I don't like the term vibe coding. I tell people what I do is 'agentic engineering' with a little star. Vibe coding starts at 3am."
- Reorx's blog: transitioned from code executor to "super manager" coordinating AI tools
- HN discussion: mixed. Skeptics note LLMs "fall apart on actually difficult things." Proponents cite gains in boilerplate elimination and small-scoped projects.

Sources:
- https://steipete.me/ (all blog posts)
- https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code
- https://reorx.com/blog/openclaw-is-changing-my-life/
- https://github.com/openclaw/openclaw
- https://github.com/steipete/agent-scripts

---

## 1. Boris Cherny's Workflow (Creator of Claude Code, 50-100 PRs/week)

**Setup:** Surprisingly vanilla. 10-15 concurrent sessions: 5 in terminal (tabbed, numbered, OS notifications), 5-10 in browser, plus mobile sessions started in morning and checked later. Relies on system notifications rather than babysitting.

**Core workflow:**
- Uses Plan Mode to iterate on approach before any code. Goes back and forth until plan is right, then switches to auto-accept edits mode. Claude usually 1-shots it from a good plan.
- Slash commands for every repeated inner-loop workflow (`/commit-push-pr` used daily). Commands checked into git in `.claude/skills/`.
- Each team maintains CLAUDE.md in git to document mistakes. Uses `@.claude` tag on coworkers' PRs to add learnings, preserving knowledge from each PR.
- Prefers Opus with thinking for all coding - values quality and reliability over speed.

**Key insight:** "Giving Claude a way to verify its work is important to get great results; if Claude has that feedback loop, it will 2-3x the quality of the final result."

Sources:
- https://medium.com/vibe-coding/claude-codes-creator-100-prs-a-week-his-setup-will-surprise-you-7d6939c99f2b
- https://www.infoq.com/news/2026/01/claude-code-creator-workflow/
- https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm

---

## 2. Core Concepts That Make AI Coding Efficient

### A. CLAUDE.md: The Foundation

The single most important configuration artifact. Read at session start, serves as the agent's "constitution."

**Optimal:** Under 300 lines. HumanLayer keeps theirs under 60. LLMs can follow ~150-200 instructions reliably; Claude Code's system prompt already uses ~50. Every line in CLAUDE.md competes for attention.

**Rule:** For each line, ask "Would removing this cause Claude to make mistakes?" If not, cut it. Bloated files cause Claude to ignore your actual instructions.

**Include:** Build/test/lint commands Claude can't guess, code style rules that differ from defaults, repo conventions (commit style, PR format), architectural decisions, environment quirks.

**Exclude:** Anything Claude can figure out from code, standard conventions it already knows, detailed API docs (link instead), self-evident instructions.

**Progressive disclosure:** Don't cram everything into CLAUDE.md. Keep domain knowledge in separate files. Write "For Stripe issues, see docs/stripe-guide.md" instead of inlining the guide.

Sources:
- https://code.claude.com/docs/en/best-practices
- https://www.humanlayer.dev/blog/writing-a-good-claude-md
- https://claude.com/blog/using-claude-md-files

### B. Verification Loops (Highest-Leverage Practice)

Give Claude a way to check its own work. Without verification criteria, you become the only feedback loop.

**Bad:** "implement email validation"
**Good:** "write validateEmail. Tests: user@example.com=true, invalid=false, user@.com=false. Run tests after implementing."

**Bad:** "the build is failing"
**Good:** "build fails with [paste error]. Fix it, verify build succeeds. Address root cause, don't suppress."

### C. Small Steps, High Control

thoughtbot achieved production-quality Rails code in a 2-week sprint by:
- Giving Claude very small tasks
- Coaching it through writing good tests
- Building on patterns from previous features to gain momentum
- Keeping humans in charge of strategy, direction, and quality control

The key difference between "vibe coding" and production-quality: control through smaller steps.

Source: https://thoughtbot.com/blog/claude-code-skills-production-ready-code-in-a-two-week-sprint

### D. Context Window Management

**Kitchen sink session:** Starting one task, asking something unrelated, returning. Context fills with noise. Fix: `/clear` between unrelated tasks.

**Correcting repeatedly:** After 2 failed corrections, the context is polluted. Fix: `/clear`, write a better initial prompt incorporating what you learned. Clean session + better prompt > long session + accumulated corrections.

**Session commands:** `/clear` (reset), `/compact <focus>` (compress context), `/context` (check usage), `--continue` (resume last), `--resume` (pick from recent), `/rename` (name sessions).

### E. The "How" to "What" Shift

Most productive developers shifted from telling agents HOW to code to telling them WHAT success looks like. Define acceptance criteria, provide test cases, let the agent figure out implementation. Developer role changes from operator to manager of outcomes and constraints.

---

## 3. Workflow Patterns

### A. Plan Then Execute (Official Anthropic Workflow)

1. **Explore** (Plan Mode): Read files, understand codebase. No changes.
2. **Plan** (Plan Mode): Create detailed implementation plan. Iterate until good.
3. **Implement** (Normal Mode): Code against the plan. Write tests, run suite, fix failures.
4. **Commit**: Descriptive message, create PR.

Skip planning for small, clear-scope fixes. Use it when uncertain about approach, touching multiple files, or unfamiliar with the code.

### B. Test-Driven AI Development

1. Ask Claude to write failing tests first (be explicit: "We are doing TDD")
2. Let Claude implement code to pass tests
3. Ask Claude to refactor while keeping tests green

Multi-agent TDD: separate context windows for test writer and implementer. The test writer's analysis should not bleed into implementer's thinking.

Source: https://thenewstack.io/claude-code-and-the-art-of-test-driven-development/

### C. Writer/Reviewer Pattern

Session A writes code. Session B (fresh context) reviews it. Fresh context prevents bias toward code just written. A subagent focused on review with a critical mindset is far superior to asking the main agent to "mark its own homework."

Source: https://code.claude.com/docs/en/best-practices

### D. Parallel Agent Workflows

**Simon Willison** (6 agents, 6 terminals):
- **Scout agent:** Give it a hard task with no intention of landing code. Learn which files it modifies, how it approaches the problem.
- **Domain parallelism:** Frontend, backend, database agents working simultaneously.
- **Architect + implementer:** One agent plans, fresh instances implement.

**incident.io** uses git worktrees for isolation:
- Each Claude session gets its own branch checkout in its own directory
- Built a custom worktree manager for instant isolated environments
- Multiple agents in parallel on isolated features

**Boris Cherny:** 10-15 sessions with OS notifications for when human input is needed.

Sources:
- https://simonwillison.net/2025/Oct/5/parallel-coding-agents/
- https://incident.io/blog/shipping-faster-with-claude-code-and-git-worktrees

### E. Agent Teams (Swarms)

Enable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json. One lead agent delegates to teammates working in parallel, each in its own context window. Shared task list, automatic notifications. Now first-class in Claude Code with Opus 4.6.

Source: https://code.claude.com/docs/en/agent-teams

---

## 4. Skills and Commands

### Existing Skills

| Skill | Purpose |
|-------|---------|
| `/push` | Pull, build, bump version, push |
| `/pull` | Git pull sync |
| `/plan-doc` | Analyze doc gaps, produce batch-compatible doc tracker |
| `/plan-refactor` | Analyze codebase, refresh refactoring backlog |
| `/refactor` | Work on a tracker item |
| `/design` | Pre-implementation feature design spec |

### Implemented Skills (from community patterns)

All in `.claude/skills/`. Created 2026-02-14.

| Skill | Purpose | Pattern |
|-------|---------|---------|
| `/review` | Code review with fresh context | Writer/reviewer. Review diff for correctness, races, edge cases, consistency |
| `/test` | TDD workflow | Red/green/refactor. Write failing tests first, implement, verify |
| `/investigate` | Debug/explore issue | Read-only scout. Trace execution path, identify root cause, report |
| `/changelog` | Generate changelog from commits | Read git log, categorize by Conventional Commits, write entry |
| `/deps` | Dependency audit | cargo update --dry-run, cargo audit, unused dep scan |
| `/bench` | Performance benchmark | criterion/hyperfine, compare baseline, report regressions |
| `/onboard` | New developer context | Read-only codebase overview for newcomers |
| `/handoff` | Transfer work between sessions | Capture state to handoff.md for next session |
| `/pickup` | Resume work from handoff | Read handoff.md, verify state, continue |

### Implemented Hooks

In `.claude/settings.json`. Created 2026-02-14.

| Hook Event | Script | Purpose |
|------------|--------|---------|
| PostToolUse:Edit\|Write | `scripts/hook-fmt.sh` | Auto-format .rs files with rustfmt after every edit |
| PreToolUse:Bash | `scripts/hook-block-dangerous.sh` | Block `git push --force`, `git reset --hard`, `git clean -fd`, `git branch -D main/master` |

### Hooks Considered But Not Added

| Hook | Reason skipped |
|------|---------------|
| PostToolUse → cargo clippy | Too slow (full project check on every edit). Clippy already in pre-commit hook. |
| Stop → cargo test-safe | Fires after every response — too frequent. Run tests manually or in `/test`. |
| SessionStart → git pull | Could disrupt uncommitted work. Use `/pull` explicitly. |

---

## 5. Pitfalls to Avoid

### Armin Ronacher's Lessons (Flask/Rye/uv creator)

- **Mental disengagement:** Biggest hidden risk. When you stop thinking like an engineer, quality drops. Don't let automation make you lazy.
- **Premature automation:** Only automate things you do regularly. If you haven't done it manually several times, don't automate it.
- **Sub-agent chaos:** Tasks that don't parallelize well (mixing reads and writes) create chaos. Sub-agents work best for investigation, not mixed operations.
- **Elaborate prompts vs. conversation:** Without rigorous rules you consistently follow, simply taking time to talk clearly to the machine outperforms elaborate pre-written prompts.

Source: https://lucumr.pocoo.org/2025/7/30/things-that-didnt-work/

### The 80% Problem (Addy Osmani)

AI agents rapidly generate 80% of code, but the remaining 20% requires deep context, architecture, and trade-off knowledge. Teams that handle this well use:
- Fresh-context code reviews
- Automated verification at every step (CI/CD, linters, type checkers, tests)
- Deliberate constraints on agent autonomy
- Human-in-the-loop at architectural decision points

Source: https://addyo.substack.com/p/the-80-problem-in-agentic-coding

### The "First Attempt is 95% Garbage" (Sanity Staff Engineer)

After 6 weeks with Claude Code, a staff engineer at Sanity learned that the first output is almost always garbage. The path to quality is iteration, verification, and tight feedback loops.

Source: https://www.sanity.io/blog/first-attempt-will-be-95-garbage

---

## 6. Tools and Integrations

| Tool | Purpose |
|------|---------|
| Git worktrees | Parallel agent isolation (each session on its own branch) |
| `gh` CLI | GitHub operations without API rate limits |
| MCP servers | Connect Notion, Figma, databases, monitoring |
| Docker/DevContainers | Sandboxed execution for `--dangerously-skip-permissions` |
| `/permissions` | Allowlist safe commands to reduce interruption fatigue |
| Hooks system | Deterministic automation (format, lint, test after edits) |
| Plugin system | Bundle skills+hooks+agents into shareable units |
| ClawHub | Skill marketplace for OpenClaw (3,000+ skills) |
| `ast-grep` | Custom linting rules as git hooks |
| `jscpd` / `knip` | Code duplication / dead code detection |
| Wispr Flow | Voice dictation with semantic correction |

---

## 7. Key Takeaways for Any Package Development

1. **CLAUDE.md is your highest-leverage investment.** Keep it under 300 lines, focused on what Claude can't figure out alone. Document mistakes as you encounter them.

2. **Verification is everything.** Give Claude tests, linters, build commands. The feedback loop 2-3x quality.

3. **Small tasks > big tasks.** Break work into focused, verifiable chunks. Each task should have clear acceptance criteria.

4. **Use Plan Mode for anything non-trivial.** Iterate on the plan before writing code. Good plans enable 1-shot implementation.

5. **Slash commands for repeated workflows.** Anything you do daily should be a command. Check them into git.

6. **Fresh context for review.** Never ask the same session to review its own work. Use subagents or separate sessions.

7. **Commit frequently.** Every small success is a checkpoint. Enables safe experimentation.

8. **Parallelize with isolation.** Git worktrees or agent teams for parallel work. Don't mix concerns in one session.

9. **Don't mentally disengage.** AI amplifies your engineering skill. If you stop thinking, quality drops.

10. **Start simple, add complexity based on friction.** Don't over-engineer your AI setup. Add rules/hooks/skills when you encounter actual repeated problems.

---


- no mcp, use skills, slash commands
- no git tree, no branch
- multi agent multi folder