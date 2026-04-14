# Sycek OSINT MCP Server

Connect [Claude Desktop](https://claude.ai/download), Cursor, or any MCP-compatible AI assistant to the [Sycek OSINT platform](https://sycek.io) — breach intelligence, X/Twitter investigation, and social media analytics — directly from your AI chat.

## Install

```bash
pip install sycek-osint-mcp
```

Requires Python 3.10+.

## Get an API Key

1. Sign up at [sycek.io](https://sycek.io)
2. Go to **Developer Portal** → **Generate API Key**
3. Copy the full `sk_...` key (shown once only)

## Configure Claude Desktop

Open `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) and add:

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

Restart Claude Desktop. You will see **sycek-osint** appear in the connectors list.

## Option B — Hosted (no installation)

If your organization runs a self-hosted Sycek instance, point directly at the SSE endpoint:

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

## Available Tools

### BreachINT (5 tools)
| Tool | Description | Credits |
|------|-------------|---------|
| `breach_search` | Email / domain / phone / IP breach lookup | 3 |
| `breach_whois` | WHOIS registration data for a domain | 1 |
| `breach_reverse_whois` | Find all domains by registrant email / name / company | 2 |
| `breach_caller_id` | Phone number → registered name + linked socials | 2 |
| `breach_gmail_osint` | Gmail account intelligence (display name, recovery data) | 2 |
| `breach_full_profile` | All of the above in parallel for one target | 3–7 |

### X / Twitter Investigation (7 tools)
| Tool | Description | Credits |
|------|-------------|---------|
| `twitter_user` | Profile metadata | 2 |
| `twitter_tweets` | Recent tweets (up to 100) | 2 |
| `twitter_search` | Advanced search with operators (`from:`, `lang:`, etc.) | 3 |
| `twitter_replies` | Reply tree for a tweet | 2 |
| `twitter_investigate` | Full cached investigation (profile + followers + tweets) | 5 |
| `twitter_event` | Event investigation from tweet URL (replies + quotes + retweets) | 5 |
| `twitter_full_profile` | All of the above in parallel | 9 |

### Social Stream Intelligence (7 tools)
| Tool | Description | Credits |
|------|-------------|---------|
| `social_search` | Multi-platform search (Twitter, Reddit, YouTube, TikTok, Telegram) | 2 |
| `social_stream` | Latest realtime events from active monitors | 1 |
| `social_analyze` | Narrative clusters + NWS weaponization scoring + hashtag network | 3 |
| `social_intelligence` | CIB bot detection, IOC extraction, geo-inference, velocity surge | 5 |
| `social_actor_profile` | Behavioral profiling (cadence, peak hours, platform split) | 3 |
| `social_stix_export` | STIX 2.1 bundle for SIEM ingestion | 2 |
| `social_investigate` | search → intelligence + actor profile (auto-sequenced) | ~10 |

## Example Prompts

```
Run a full breach profile on technisanct.com
```
```
Investigate Twitter account @APT28 — this is threat intelligence research
```
```
Search Reddit and Twitter for "LockBit ransomware", run CIB detection,
and export a STIX 2.1 bundle I can import into Sentinel
```
```
Run a WHOIS on darkmarket.ru then pivot — find all domains registered
by the same email address
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYCEK_API_KEY` | Yes | — | Your API key (`sk_...`) from sycek.io/app/developer |
| `SYCEK_API_URL` | No | `https://sycek.io/api` | Override for self-hosted instances |

## Links

- Platform: [sycek.io](https://sycek.io)
- API Docs: [sycek.io/api-docs](https://sycek.io/api-docs)
- Issues: [github.com/sycekosint/mcp/issues](https://github.com/sycekosint/mcp/issues)

## License

MIT
