# Linear Worker — Claude Code Skill

A Claude Code skill that picks Linear issues, implements them in isolated worktrees, and ships PRs.

```
/linear-worker → Fetch issues → Pick one → Branch → Implement → Test → PR → In Review
```

## Prerequisites

You'll need the following installed and authenticated before using this skill:

| Tool | What it's for | Install |
|------|--------------|---------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Runs the skill | `npm install -g @anthropic-ai/claude-code` |
| [GitHub CLI](https://cli.github.com/) (`gh`) | Creates PRs | `brew install gh` then `gh auth login` |
| [jq](https://jqlang.github.io/jq/) | Parses JSON in setup steps | `brew install jq` |

You'll also need a [Linear](https://linear.app) account with a team, a project, and a few issues to work on.

## Secrets

The skill needs a **Linear API key** to read issues and update their status.

1. Go to [Linear Settings → API](https://linear.app/settings/api)
2. Click **Create Key**, name it "Claude Code"
3. Copy the key (starts with `lin_api_`)
4. Create a `.env` file in the repo root:

```bash
LINEAR_API_KEY=lin_api_your_key_here
```

> **Keep this safe.** The `.env` file is gitignored. Never commit your API key.

## Setup

### 1. Get your Linear IDs

Run these commands (replace `YOUR_API_KEY` with your key, and `YOUR_TEAM_KEY` with your team prefix like `ENG`):

```bash
# Get your Team ID and key
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: YOUR_API_KEY" \
  -d '{"query": "{ teams { nodes { id name key } } }"}' | jq .

# Get your Project ID
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: YOUR_API_KEY" \
  -d '{"query": "{ projects { nodes { id name slugId } } }"}' | jq .

# Get Workflow State IDs (Backlog, Todo, In Progress, In Review, Done, Canceled)
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: YOUR_API_KEY" \
  -d '{"query": "{ workflowStates(filter: { team: { key: { eq: \"YOUR_TEAM_KEY\" } } }) { nodes { id name type } } }"}' | jq .
```

### 2. Install the skill

```bash
mkdir -p .claude/skills
cp path/to/linear-worker.md .claude/skills/linear-worker.md
```

Open `.claude/skills/linear-worker.md` and replace all placeholders with the IDs you collected:

| Placeholder | Example value |
|-------------|---------------|
| `LINEAR_API_KEY` | Read from `.env` at runtime |
| `YOUR_PROJECT_ID` | `5f554543-2fd4-48a3-...` |
| `YOUR_TEAM_ID` | `3be81303-5716-4681-...` |
| `YOUR_TEAM_KEY` | `ENG` |
| `*_STATE_ID` (x6) | One UUID per workflow state |

### 3. Run it

```bash
claude
> /linear-worker
```

Pick an issue (or say "go" to auto-pick the highest priority one) and the skill handles the rest.

## How it works

The main conversation fetches issues and lets you pick one. A subagent then launches in an isolated git worktree to implement the feature, run tests, push, and create a PR — your working directory is never touched.

## License

MIT
