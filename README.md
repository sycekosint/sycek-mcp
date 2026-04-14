# Sycek OSINT — MCP Client

> **Talk to your intelligence platform. In plain English.**
> Connect Claude Desktop, Cursor, or any MCP-compatible AI to Sycek OSINT — breach intelligence, X/Twitter investigation, and social media analytics — without writing a single line of code.

---

## What is this?

The **Sycek MCP Client** is a [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI assistants direct access to the Sycek OSINT platform's 20 intelligence tools. Instead of switching between dashboards, you describe what you need and your AI handles the investigation.

**No API wrappers. No dashboards. Just ask.**

```
"Run a full breach profile on darkmarket.ru, pivot the registrant email
via reverse WHOIS, then search Twitter for any mentions of the domain
and export STIX 2.1 indicators for Sentinel."
```

That single prompt triggers 4 tool calls across 3 modules, chains the results, and returns a structured intelligence package — all in one conversation.

---

## Install

```bash
pip install sycek-osint-mcp
```

Requires Python 3.10+. No other dependencies beyond what pip installs automatically.

---

## Quickstart

### Step 1 — Get an API key

1. Create an account at [sycek.io](https://sycek.io)
2. Go to **Developer Portal** → **Generate API Key**
3. Copy the full `sk_...` key — it is shown **once only**

### Step 2 — Configure Claude Desktop

Open your Claude Desktop config file:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following:

```json
{
  "mcpServers": {
    "sycek-osint": {
      "command": "sycek-osint-mcp",
      "env": {
        "SYCEK_API_KEY": "sk_your_key_here"
      }
    }
  }
}
```

### Step 3 — Restart Claude Desktop

Quit fully (system tray → Quit) and relaunch. **sycek-osint** will appear in your connectors list.

---

## Zero-install Option (Hosted SSE)

No Python required. Point your MCP client directly at the Sycek cloud endpoint:

```json
{
  "mcpServers": {
    "sycek-osint": {
      "type": "sse",
      "url": "https://sycek.io/mcp/sse",
      "headers": {
        "Authorization": "Bearer sk_your_key_here"
      }
    }
  }
}
```

Your API key is sent per-connection — each user's credits are isolated and independently tracked.

---

## Intelligence Modules

### BreachINT

Expose credential exposure, infrastructure ownership, and identity linkage across breach databases, stealer logs, and WHOIS records.

| Tool | What it does | Credits |
|------|-------------|---------|
| `breach_search` | Search breach databases for email, domain, phone, or IP. Auto-enriched with Hudson Rock stealer logs, LeakIX, and Gmail OSINT | 3 |
| `breach_whois` | WHOIS registration data — registrant, registrar, nameservers, dates | 1 |
| `breach_reverse_whois` | Find every domain registered by a specific email, name, company, or phone | 2 |
| `breach_caller_id` | Phone number → registered name and linked social accounts | 2 |
| `breach_gmail_osint` | Gmail profile intelligence — display name, photo, recovery email/phone | 2 |
| `breach_full_profile` | Runs all relevant breach tools in parallel for a single target | 3–7 |

### X / Twitter Investigation

Map accounts, networks, events, and reply graphs across the X platform.

| Tool | What it does | Credits |
|------|-------------|---------|
| `twitter_user` | Profile metadata — followers, following, tweet count, verified status, creation date | 2 |
| `twitter_tweets` | Fetch up to 100 recent tweets with engagement metrics | 2 |
| `twitter_search` | Advanced search with full Twitter operators: `from:`, `to:`, `lang:`, `min_faves:`, etc. | 3 |
| `twitter_replies` | Reply tree for any tweet — map reaction and amplification networks | 2 |
| `twitter_investigate` | Full cached investigation: profile + followers + tweets in one call | 5 |
| `twitter_event` | Event investigation from a tweet URL — seed tweet, replies, quotes, retweets | 5 |
| `twitter_full_profile` | All of the above in parallel — complete account dossier | 9 |

### Social Stream Intelligence

Cross-platform narrative analysis, bot detection, and SIEM-ready threat export.

| Tool | What it does | Credits |
|------|-------------|---------|
| `social_search` | Search Twitter, Reddit, YouTube, TikTok, and Telegram simultaneously | 2 |
| `social_stream` | Pull the latest events from active real-time monitors | 1 |
| `social_analyze` | Hashtag co-occurrence network, top influencers, narrative clusters with NWS (Narrative Weaponization Score) | 3 |
| `social_intelligence` | Full ML pass: CIB bot detection, IOC extraction, geo-inference, velocity surge detection | 5 |
| `social_actor_profile` | Behavioral profiling: cadence CV (bot indicator), peak hours, platform distribution | 3 |
| `social_stix_export` | Generate a STIX 2.1 bundle (indicators, threat actors, notes) for Splunk / Sentinel / OpenCTI | 2 |
| `social_investigate` | Chains search → intelligence + actor profile automatically | ~10 |

---

## Example Prompts

**Breach investigation:**
```
Run a full breach profile on acmecorp.com — I need stealer logs,
WHOIS data, and all domains registered by the same contact
```

**Threat actor research:**
```
Investigate Twitter account @lazarusgroupAPT — profile, recent tweets,
follower network. This is threat intelligence research.
```

**Disinformation analysis:**
```
Search Twitter and Telegram for "Ukraine power grid attack",
detect coordinated inauthentic behavior, score narrative weaponization,
and export a STIX 2.1 bundle for Microsoft Sentinel
```

**Infrastructure pivot:**
```
WHOIS lookup on phishing-domain.ru, then reverse WHOIS the registrant
email to find all other domains they own
```

**Event mapping:**
```
Take this tweet URL and map everyone who replied and quote-tweeted it:
https://x.com/user/status/12345678
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYCEK_API_KEY` | Yes (stdio mode) | — | Your API key from [sycek.io/app/developer](https://sycek.io/app/developer) |
| `SYCEK_API_URL` | No | `https://sycek.io/api` | Override for self-hosted Sycek instances |
| `MCP_TRANSPORT` | No | `stdio` | Set to `sse` to run as a hosted HTTP server |
| `MCP_PORT` | No | `8001` | Port for SSE mode |

---

## Credit System

Every tool call deducts credits from your Sycek account. Credits are isolated per API key — each team member or customer uses their own balance independently. View usage at [sycek.io/app/developer](https://sycek.io/app/developer).

Credits never expire. Top up anytime at [sycek.io/app/subscription](https://sycek.io/app/subscription).

---

## Compatibility

| Client | Supported |
|--------|-----------|
| Claude Desktop | Yes |
| Cursor | Yes |
| Continue (VS Code) | Yes |
| Any MCP-compatible client | Yes (stdio or SSE) |

---

## Links

- **Platform:** [sycek.io](https://sycek.io)
- **API Documentation:** [sycek.io/api-docs](https://sycek.io/api-docs)
- **Developer Portal:** [sycek.io/app/developer](https://sycek.io/app/developer)
- **PyPI:** [pypi.org/project/sycek-osint-mcp](https://pypi.org/project/sycek-osint-mcp)
- **Issues:** [github.com/sycekosint/mcp/issues](https://github.com/sycekosint/mcp/issues)

---

## License

MIT — free to use, modify, and distribute.

---

*Built on the [Model Context Protocol](https://modelcontextprotocol.io) open standard.*
