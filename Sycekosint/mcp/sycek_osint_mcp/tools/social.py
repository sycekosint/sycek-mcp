"""
Social Stream intelligence tools for the Sycek OSINT MCP server.

Tools registered:
  social_search        — multi-platform search (Twitter, Reddit, YouTube, TikTok, Telegram) (2 credits)
  social_stream        — latest realtime social events from active monitors               (1 credit)
  social_analyze       — narrative clusters, hashtag network, NWS weaponization scoring   (3 credits)
  social_intelligence  — full ML pass: CIB detection, IOC extraction, geo, velocity      (5 credits)
  social_actor_profile — behavioral actor profiling: cadence, peak hours, platform split  (3 credits)
  social_stix_export   — STIX 2.1 bundle (indicators, threat actors, notes) for SIEM     (2 credits)
  social_investigate   — search + intelligence + actor_profile in sequence               (~10 credits)

IMPORTANT SEQUENCING NOTE:
  social_analyze, social_intelligence, social_actor_profile, and social_stix_export
  all require a `posts` array as input — they do NOT search independently.
  Always call social_search first to get posts, then pass the posts to these tools.
  The social_investigate meta-tool handles this automatically.
"""
import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from sycek_osint_mcp import client, formatting


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        description=(
            "Search across social media platforms for posts matching a query. "
            "Platforms: twitter, reddit, youtube, tiktok, telegram. "
            "Returns posts with text, author, engagement metrics, timestamps, and sentiment. "
            "The posts array returned here is the INPUT required by social_analyze, "
            "social_intelligence, social_actor_profile, and social_stix_export. "
            "Costs 2 credits."
        )
    )
    async def social_search(
        query: str,
        platforms: list[str] | None = None,
        count_per_platform: int = 50,
    ) -> str:
        """
        Args:
            query: Search query (keywords, hashtags, phrases)
            platforms: List of platforms to search (default: ['twitter', 'reddit'])
            count_per_platform: Posts to fetch per platform (1–200)
        """
        platforms = platforms or ["twitter", "reddit"]
        count_per_platform = max(1, min(count_per_platform, 200))
        try:
            data = await client.api_post("/v1/social/search", {
                "query": query,
                "platforms": platforms,
                "count_per_platform": count_per_platform,
            })
        except Exception as e:
            return formatting.error_response(f"Social Search: {query}", e)

        results = data.get("results") or data.get("posts") or []
        platform_counts: dict[str, int] = {}
        for post in results:
            p = post.get("platform", "unknown")
            platform_counts[p] = platform_counts.get(p, 0) + 1

        facts = [
            f"Total posts retrieved: {len(results)}",
            f"Platforms searched: {', '.join(platforms)}",
        ]
        for plat, count in platform_counts.items():
            facts.append(f"  {plat}: {count} posts")

        return formatting.render(f"Social Search: {query}", facts, data)

    @mcp.tool(
        description=(
            "Fetch the latest events from all active social monitoring streams. "
            "Returns realtime posts currently being tracked by the platform. "
            "Does NOT require a query — pulls from the live stream buffer. "
            "Costs 1 credit."
        )
    )
    async def social_stream(limit: int = 50) -> str:
        """
        Args:
            limit: Number of events to return (1–500)
        """
        limit = max(1, min(limit, 500))
        try:
            data = await client.api_get("/v1/social/stream", params={"limit": limit})
        except Exception as e:
            return formatting.error_response("Social Stream", e)

        events = data.get("events") or []
        facts = [
            f"Events returned: {len(events)}",
            f"Requested: {limit}",
        ]
        return formatting.render("Social Stream (Realtime)", facts, data)

    @mcp.tool(
        description=(
            "Analyze a batch of social media posts for narrative intelligence. "
            "Returns: hashtag co-occurrence network (nodes + edges), top influencers "
            "by engagement, narrative clusters with NWS (Narrative Weaponization Score), "
            "and posting timeline by UTC hour. "
            "NWS > 0.7 indicates potentially weaponized narrative. "
            "REQUIRES: a 'posts' array from social_search — call social_search first. "
            "Costs 3 credits."
        )
    )
    async def social_analyze(posts: list[dict[str, Any]]) -> str:
        """
        Args:
            posts: Array of post objects from social_search results
        """
        if not posts:
            return formatting.error_response(
                "Social Analyze",
                ValueError("posts array is empty — call social_search first to get posts")
            )
        try:
            data = await client.api_post("/v1/social/analyze", {"posts": posts})
        except Exception as e:
            return formatting.error_response("Social Analyze", e)

        clusters = data.get("narrative_clusters") or []
        influencers = data.get("top_influencers") or []
        ht_nodes = len((data.get("hashtag_network") or {}).get("nodes", []))
        ht_edges = len((data.get("hashtag_network") or {}).get("edges", []))

        # Find highest NWS score
        max_nws = max((c.get("nws_score", 0) for c in clusters), default=0)
        nws_flag = " ⚠ HIGH NWS" if max_nws >= 0.7 else (" MEDIUM NWS" if max_nws >= 0.4 else "")

        facts = [
            f"Posts analyzed: {len(posts)}",
            f"Narrative clusters: {len(clusters)}{nws_flag}",
            f"Top influencers: {len(influencers)}",
            f"Hashtag network: {ht_nodes} nodes, {ht_edges} edges",
            f"Peak NWS (Narrative Weaponization Score): {max_nws:.2f}",
        ]
        return formatting.render("Social Narrative Analysis", facts, data)

    @mcp.tool(
        description=(
            "Run full ML intelligence analysis on social media posts. "
            "Executes in parallel: "
            "(1) CIB detection — coordinated inauthentic behavior / bot networks, "
            "(2) IOC extraction — IP addresses, domains, malware hashes, CVEs, "
            "(3) Geo-inference — country/region distribution of content origins, "
            "(4) Velocity monitoring — surge detection (abnormal posting rate vs baseline). "
            "REQUIRES: a 'posts' array from social_search — call social_search first. "
            "This is the most powerful social analysis tool. "
            "Costs 5 credits."
        )
    )
    async def social_intelligence(
        posts: list[dict[str, Any]],
        keyword: str = "",
    ) -> str:
        """
        Args:
            posts: Array of post objects from social_search results
            keyword: The original search keyword (used for velocity baseline comparison)
        """
        if not posts:
            return formatting.error_response(
                "Social Intelligence",
                ValueError("posts array is empty — call social_search first to get posts")
            )
        try:
            data = await client.api_post("/v1/social/intelligence", {
                "posts": posts,
                "keyword": keyword,
            })
        except Exception as e:
            return formatting.error_response(f"Social Intelligence: {keyword}", e)

        cib = data.get("cib") or {}
        iocs = data.get("iocs") or {}
        geo = data.get("geo") or {}
        velocity = data.get("velocity") or {}

        ioc_count = sum(
            len(v) if isinstance(v, list) else 0
            for v in iocs.values()
        )
        is_surge = velocity.get("is_surge", False)
        cib_score = cib.get("cib_score", 0) or cib.get("score", 0)

        facts = [
            f"Posts analyzed: {data.get('post_count', len(posts))}",
            f"CIB score: {cib_score:.2f} {'— COORDINATED BEHAVIOR DETECTED' if cib_score > 0.6 else ''}",
            f"IOCs extracted: {ioc_count}",
            f"Geo regions identified: {len(geo.get('countries', geo.get('regions', [])))}",
            f"Velocity surge: {'YES — abnormal posting rate detected' if is_surge else 'No'}",
        ]
        return formatting.render(f"Social Intelligence: {keyword}", facts, data)

    @mcp.tool(
        description=(
            "Build a behavioral profile for a specific social media actor from their posts. "
            "Returns: platform distribution, peak activity hours (UTC), "
            "cadence coefficient of variation (low CV < 0.15 suggests automated/bot behavior), "
            "total engagement metrics, follower count, and verified status. "
            "REQUIRES: a 'posts' array from social_search AND the author's ID from those posts. "
            "Call social_search first, then use an author_id from the results. "
            "Costs 3 credits."
        )
    )
    async def social_actor_profile(
        author_id: str,
        posts: list[dict[str, Any]],
    ) -> str:
        """
        Args:
            author_id: The author identifier to profile (from post.author_id or post.author field)
            posts: Array of all posts (the actor's posts will be filtered automatically)
        """
        if not posts:
            return formatting.error_response(
                f"Social Actor Profile: {author_id}",
                ValueError("posts array is empty — call social_search first to get posts")
            )
        try:
            data = await client.api_post("/v1/social/actor-profile", {
                "author_id": author_id,
                "posts": posts,
            })
        except Exception as e:
            return formatting.error_response(f"Social Actor Profile: {author_id}", e)

        cv = data.get("cadence_cv")
        cadence_flag = data.get("cadence_flag", False)

        facts = [
            f"Author: {data.get('author', author_id)}",
            f"Posts by this author: {data.get('post_count', 0)}",
            f"Total engagement: {data.get('total_engagement', 0):,}",
            f"Peak hours (UTC): {data.get('peak_hours', [])}",
            f"Cadence CV: {cv:.3f} {'— POSSIBLE BOT (low variance)' if cadence_flag else ''}" if cv is not None else "Cadence CV: insufficient data",
            f"Platforms: {list((data.get('platforms') or {}).keys())}",
        ]
        return formatting.render(f"Social Actor Profile: {author_id}", facts, data)

    @mcp.tool(
        description=(
            "Export a STIX 2.1 bundle from social intelligence data: "
            "identity objects, indicator objects (for IOCs), threat-actor objects, "
            "note objects (narrative clusters), and a report object. "
            "Output is valid STIX 2.1 JSON suitable for ingestion into any SIEM "
            "(Splunk, Elastic SIEM, Microsoft Sentinel, OpenCTI). "
            "REQUIRES: posts from social_search, optionally iocs from social_intelligence, "
            "optionally clusters from social_analyze. "
            "Costs 2 credits."
        )
    )
    async def social_stix_export(
        query: str,
        posts: list[dict[str, Any]],
        iocs: dict[str, Any] | None = None,
        clusters: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Args:
            query: The original search query (becomes the STIX report title)
            posts: Array of post objects from social_search
            iocs: IOC dict from social_intelligence (optional, enriches indicators)
            clusters: Narrative clusters from social_analyze (optional, adds threat context)
        """
        if not posts:
            return formatting.error_response(
                f"STIX Export: {query}",
                ValueError("posts array is empty — call social_search first to get posts")
            )
        try:
            data = await client.api_post("/v1/social/stix-export", {
                "query": query,
                "posts": posts,
                "iocs": iocs or {},
                "clusters": clusters or [],
            })
        except Exception as e:
            return formatting.error_response(f"STIX Export: {query}", e)

        obj_count = len(data.get("objects", []))
        bundle_id = data.get("id", "N/A")

        facts = [
            f"STIX bundle ID: {bundle_id}",
            f"STIX objects: {obj_count}",
            f"Spec version: {data.get('spec_version', '2.1')}",
            f"Source posts: {len(posts)}",
        ]
        return formatting.render(f"STIX Export: {query}", facts, data)

    @mcp.tool(
        description=(
            "Complete social media investigation in one call: "
            "searches for posts (2 credits), then runs ML intelligence analysis "
            "and behavioral profiling on the top author in parallel (5 + 3 credits). "
            "Total cost: ~10 credits. "
            "This is the best starting point for any social OSINT investigation — "
            "it reveals CIB activity, IOCs, narrative weaponization, and actor profiles. "
            "After this call, use social_stix_export to generate SIEM-ready output "
            "or social_analyze for deeper narrative cluster analysis."
        )
    )
    async def social_investigate(
        query: str,
        platforms: list[str] | None = None,
        count_per_platform: int = 50,
        top_author: str | None = None,
    ) -> str:
        """
        Args:
            query: Search query (keywords, hashtags, entity names)
            platforms: Platforms to search (default: ['twitter', 'reddit'])
            count_per_platform: Posts per platform (1–200)
            top_author: Specific author_id to profile (if None, profiles the most prolific author)
        """
        platforms = platforms or ["twitter", "reddit"]
        count_per_platform = max(1, min(count_per_platform, 200))

        # Step 1: search is mandatory first — intelligence and actor-profile need posts
        try:
            search_data = await client.api_post("/v1/social/search", {
                "query": query,
                "platforms": platforms,
                "count_per_platform": count_per_platform,
            })
        except Exception as e:
            return formatting.error_response(f"Social Investigate: {query}", e)

        posts = search_data.get("results") or search_data.get("posts") or []
        if not posts:
            return formatting.render(
                f"Social Investigate: {query}",
                ["No posts found — try a broader query or add more platforms"],
                search_data,
            )

        # Determine which author to profile
        if top_author is None:
            author_counts: dict[str, int] = {}
            for post in posts:
                aid = post.get("author_id") or post.get("author") or ""
                if aid:
                    author_counts[aid] = author_counts.get(aid, 0) + 1
            top_author = max(author_counts, key=author_counts.get) if author_counts else None

        # Step 2: intelligence + actor_profile in parallel (both need the posts array)
        parallel_tasks: list[Any] = [
            client.api_post("/v1/social/intelligence", {
                "posts": posts,
                "keyword": query,
            })
        ]
        section_names: list[str | None] = ["search_results", "intelligence"]

        if top_author:
            parallel_tasks.append(
                client.api_post("/v1/social/actor-profile", {
                    "author_id": top_author,
                    "posts": posts,
                })
            )
            section_names.append("actor_profile")

        intel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

        # Combine search result + parallel results
        all_results = [search_data] + list(intel_results)
        all_sections: list[str | None] = section_names

        return formatting.render_multi(
            title=f"Social Investigate: {query}",
            sections=all_sections,
            results=all_results,
        )
