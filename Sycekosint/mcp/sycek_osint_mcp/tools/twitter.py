"""
X / Twitter Investigation tools for the Sycek OSINT MCP server.

Tools registered:
  twitter_user           — user profile + metadata                               (2 credits)
  twitter_tweets         — recent tweets for a user (up to 100)                  (2 credits)
  twitter_search         — advanced search with Twitter operators                 (3 credits)
  twitter_replies        — reply tree for a specific tweet                        (2 credits)
  twitter_investigate    — full cached investigation (profile + followers + tweets) (5 credits)
  twitter_event          — event investigation from a tweet URL or ID             (5 credits)
  twitter_full_profile   — user + tweets + full investigation in parallel          (9 credits)
"""
import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from sycek_osint_mcp import client, formatting


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        description=(
            "Fetch Twitter/X profile metadata for a user: name, bio, follower count, "
            "following count, tweet count, verified status, account creation date, "
            "and location. First step in any X investigation. "
            "Do NOT include the @ symbol in the username. "
            "Costs 2 credits."
        )
    )
    async def twitter_user(username: str) -> str:
        """
        Args:
            username: Twitter handle without @ (e.g. 'elonmusk', not '@elonmusk')
        """
        username = username.lstrip("@")
        try:
            data = await client.api_get("/v1/twitter/user", params={"username": username})
        except Exception as e:
            return formatting.error_response(f"Twitter User: @{username}", e)

        facts = _user_facts(data)
        return formatting.render(f"Twitter User: @{username}", facts, data)

    @mcp.tool(
        description=(
            "Fetch up to 100 recent tweets for a Twitter/X user. "
            "Returns tweet text, engagement metrics (likes, retweets, replies), "
            "media attachments, and timestamps. "
            "Do NOT include the @ symbol in the username. "
            "Costs 2 credits."
        )
    )
    async def twitter_tweets(username: str, count: int = 20) -> str:
        """
        Args:
            username: Twitter handle without @
            count: Number of tweets to fetch (1–100)
        """
        username = username.lstrip("@")
        count = max(1, min(count, 100))
        try:
            data = await client.api_get("/v1/twitter/tweets", params={
                "username": username,
                "count": count,
            })
        except Exception as e:
            return formatting.error_response(f"Twitter Tweets: @{username}", e)

        tweets = data.get("tweets") or data.get("results") or []
        facts = [
            f"Tweets retrieved: {len(tweets)}",
            f"Requested count: {count}",
        ]
        if tweets:
            top = max(tweets, key=lambda t: t.get("likes", 0) + t.get("retweets", 0), default={})
            if top:
                facts.append(f"Most engaged tweet: {top.get('likes', 0)} likes, {top.get('retweets', 0)} retweets")
        return formatting.render(f"Twitter Tweets: @{username}", facts, data)

    @mcp.tool(
        description=(
            "Advanced Twitter/X search using full Twitter search syntax. "
            "Supports operators: from:user, to:user, #hashtag, lang:en, "
            "-excludeterm, since:2024-01-01, until:2024-12-31, min_faves:100. "
            "search_type: 'Latest' (chronological), 'Top' (engagement-ranked), "
            "'People' (user search), 'Media' (images/videos only). "
            "Costs 3 credits."
        )
    )
    async def twitter_search(
        q: str,
        search_type: str = "Latest",
        limit: int = 20,
    ) -> str:
        """
        Args:
            q: Search query with optional Twitter operators
            search_type: 'Latest' | 'Top' | 'People' | 'Media'
            limit: Results to return (1–100)
        """
        limit = max(1, min(limit, 100))
        try:
            data = await client.api_get("/v1/twitter/search", params={
                "q": q,
                "search_type": search_type,
                "limit": limit,
            })
        except Exception as e:
            return formatting.error_response(f"Twitter Search: {q}", e)

        results = data.get("results") or data.get("tweets") or data.get("users") or []
        facts = [
            f"Query: {q}",
            f"Type: {search_type}",
            f"Results: {len(results)}",
        ]
        return formatting.render(f"Twitter Search: {q}", facts, data)

    @mcp.tool(
        description=(
            "Fetch the reply tree for a specific tweet by its ID. "
            "Returns who replied, their reply text, and engagement. "
            "Useful for mapping disinformation spread, identifying troll networks, "
            "and understanding community reaction to a post. "
            "Up to 5 pages (~20 replies/page). "
            "Costs 2 credits."
        )
    )
    async def twitter_replies(tweet_id: str, page_count: int = 1) -> str:
        """
        Args:
            tweet_id: The numeric tweet/post ID (from URL: x.com/user/status/<ID>)
            page_count: Number of reply pages to fetch (1–5)
        """
        page_count = max(1, min(page_count, 5))
        try:
            data = await client.api_get(
                f"/v1/twitter/tweet/{tweet_id}/replies",
                params={"page_count": page_count},
            )
        except Exception as e:
            return formatting.error_response(f"Twitter Replies: {tweet_id}", e)

        replies = data.get("replies") or data.get("results") or []
        facts = [
            f"Tweet ID: {tweet_id}",
            f"Replies fetched: {len(replies)}",
            f"Pages fetched: {page_count}",
        ]
        return formatting.render(f"Twitter Replies: {tweet_id}", facts, data)

    @mcp.tool(
        description=(
            "Comprehensive Twitter/X account investigation: profile metadata, "
            "followers list, following list, and recent tweets — all in one call. "
            "Results are cached so repeat investigations of the same account don't "
            "cost extra credits. Use force_refresh to bypass the cache. "
            "Best tool for building a full dossier on a specific account. "
            "Costs 5 credits."
        )
    )
    async def twitter_investigate(
        username: str,
        include_followers: bool = True,
        include_followings: bool = False,
        include_tweets: bool = True,
        max_followers: int = 200,
        max_tweets: int = 20,
        force_refresh: bool = False,
    ) -> str:
        """
        Args:
            username: Twitter handle without @
            include_followers: Fetch follower list
            include_followings: Fetch following list (slower)
            include_tweets: Fetch recent tweets
            max_followers: Max followers to collect (up to 500)
            max_tweets: Max tweets to collect (up to 100)
            force_refresh: Bypass result cache
        """
        username = username.lstrip("@")
        try:
            data = await client.api_post("/v1/twitter/investigate", {
                "username": username,
                "include_followers": include_followers,
                "include_followings": include_followings,
                "include_tweets": include_tweets,
                "max_followers": min(max_followers, 500),
                "max_tweets": min(max_tweets, 100),
                "force_refresh": force_refresh,
            })
        except Exception as e:
            return formatting.error_response(f"Twitter Investigate: @{username}", e)

        facts = _investigate_facts(data, username)
        return formatting.render(f"Twitter Investigate: @{username}", facts, data)

    @mcp.tool(
        description=(
            "Event-centric investigation starting from a tweet URL or ID. "
            "Phase 1 collects: the seed tweet, all replies, quote tweets, retweets, "
            "and thread context. Returns an investigation_id for deeper analysis. "
            "Use this for viral content, disinformation events, coordinated campaigns. "
            "Accepts tweet URLs (x.com/user/status/ID) or raw numeric IDs. "
            "Costs 5 credits."
        )
    )
    async def twitter_event(
        post_id_or_url: str,
        max_reply_pages: int = 3,
        max_quote_pages: int = 2,
        include_thread: bool = True,
    ) -> str:
        """
        Args:
            post_id_or_url: Tweet URL (https://x.com/user/status/123) or numeric ID
            max_reply_pages: Reply pages to collect (1–5, ~20 replies/page)
            max_quote_pages: Quote tweet pages to collect (1–5)
            include_thread: Whether to collect the full conversation thread
        """
        try:
            data = await client.api_post("/v1/twitter/event", {
                "post_id_or_url": post_id_or_url,
                "max_reply_pages": min(max_reply_pages, 5),
                "max_quote_pages": min(max_quote_pages, 5),
                "include_thread": include_thread,
            })
        except Exception as e:
            return formatting.error_response(f"Twitter Event: {post_id_or_url}", e)

        inv_id = data.get("investigation_id", "N/A")
        seed = data.get("seed_tweet") or {}
        facts = [
            f"Investigation ID: {inv_id}",
            f"Seed tweet author: @{seed.get('author', '?')}",
            f"Replies collected: {len(data.get('replies', []))}",
            f"Quote tweets: {len(data.get('quotes', []))}",
            f"Retweets: {len(data.get('retweets', []))}",
        ]
        return formatting.render(f"Twitter Event: {post_id_or_url}", facts, data)

    @mcp.tool(
        description=(
            "Full X/Twitter profile investigation: runs user profile lookup, "
            "recent tweets fetch, and comprehensive investigation in parallel. "
            "The most thorough single-call investigation available for any Twitter account. "
            "WARNING: costs 9 credits minimum. Confirm with the user before calling "
            "this on an unknown or unverified target. "
            "Do NOT include the @ symbol in the username."
        )
    )
    async def twitter_full_profile(
        username: str,
        max_followers: int = 200,
        max_tweets: int = 50,
    ) -> str:
        """
        Args:
            username: Twitter handle without @
            max_followers: Max followers to collect in the investigation (up to 500)
            max_tweets: Max tweets to collect (up to 100)
        """
        username = username.lstrip("@")

        results = await asyncio.gather(
            client.api_get("/v1/twitter/user", params={"username": username}),
            client.api_get("/v1/twitter/tweets", params={"username": username, "count": max_tweets}),
            client.api_post("/v1/twitter/investigate", {
                "username": username,
                "include_followers": True,
                "include_followings": False,
                "include_tweets": True,
                "max_followers": min(max_followers, 500),
                "max_tweets": min(max_tweets, 100),
            }),
            return_exceptions=True,
        )

        return formatting.render_multi(
            title=f"Full Twitter Profile: @{username}",
            sections=["profile", "recent_tweets", "investigation"],
            results=list(results),
        )


# ── Fact extractors ────────────────────────────────────────────────────────────

def _user_facts(data: dict[str, Any]) -> list[str]:
    facts = []
    user = data.get("user") or data.get("profile") or data
    if user.get("name"):
        facts.append(f"Name: {user['name']}")
    if user.get("followers_count") is not None:
        facts.append(f"Followers: {user['followers_count']:,}")
    if user.get("following_count") is not None:
        facts.append(f"Following: {user['following_count']:,}")
    if user.get("tweet_count") is not None:
        facts.append(f"Total tweets: {user['tweet_count']:,}")
    if user.get("verified"):
        facts.append("Verified: yes (blue check)")
    if user.get("created_at"):
        facts.append(f"Account created: {user['created_at']}")
    return facts or ["Profile data returned — see JSON for fields"]


def _investigate_facts(data: dict[str, Any], username: str) -> list[str]:
    facts = []
    profile = data.get("profile") or data.get("user") or {}
    if profile.get("followers_count") is not None:
        facts.append(f"Followers: {profile['followers_count']:,}")
    followers = data.get("followers") or []
    if followers:
        facts.append(f"Followers collected: {len(followers)}")
    tweets = data.get("tweets") or []
    if tweets:
        facts.append(f"Tweets collected: {len(tweets)}")
    if data.get("from_cache"):
        facts.append("Result served from cache (no extra credits)")
    return facts or [f"Investigation complete for @{username} — see JSON"]
