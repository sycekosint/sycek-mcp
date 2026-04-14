"""
BreachINT tools for the Sycek OSINT MCP server.

Tools registered:
  breach_search         — email / domain / phone / IP breach lookup          (3 credits)
  breach_whois          — WHOIS registration data for a domain               (1 credit)
  breach_reverse_whois  — pivot from a registrant field → all matching domains (2 credits)
  breach_caller_id      — phone number → registered name + linked socials    (2 credits)
  breach_gmail_osint    — Gmail account intelligence (display name, photo, recovery data) (2 credits)
  breach_full_profile   — breach_search + WHOIS (if domain) + gmail_osint
                          (if @gmail.com) in parallel                        (3–7 credits)
"""
import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from sycek_osint_mcp import client, formatting


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        description=(
            "Search the breach intelligence database for an email address, domain, "
            "username, phone number, or IP address. Automatically cross-references: "
            "Sycek's breach engine, Hudson Rock stealer logs (malware-sourced credentials), "
            "LeakIX (exposed services for domains), and Gmail OSINT (for @gmail.com). "
            "Results are cached — repeat calls for the same query return cached data. "
            "Costs 3 credits."
        )
    )
    async def breach_search(query: str, force_refresh: bool = False) -> str:
        """
        Args:
            query: Email, domain, username, phone number, or IP to investigate
            force_refresh: Set to true to bypass result cache (still costs 3 credits)
        """
        try:
            data = await client.api_post("/v1/breach/search", {
                "query": query,
                "force_refresh": force_refresh,
            })
        except Exception as e:
            return formatting.error_response(f"Breach Search: {query}", e)

        facts = _breach_facts(data)
        return formatting.render(f"Breach Search: {query}", facts, data)

    @mcp.tool(
        description=(
            "Fetch WHOIS registration data for a domain: registrant name, email, company, "
            "registrar, nameservers, creation/expiration dates, and domain status. "
            "Useful for pivoting from a breach result to the infrastructure owner. "
            "Costs 1 credit."
        )
    )
    async def breach_whois(domain: str) -> str:
        """
        Args:
            domain: Domain name to look up (e.g. example.com — without http://)
        """
        try:
            data = await client.api_get(f"/v1/breach/whois/{domain}")
        except Exception as e:
            return formatting.error_response(f"WHOIS: {domain}", e)

        facts = _whois_facts(data)
        return formatting.render(f"WHOIS: {domain}", facts, data)

    @mcp.tool(
        description=(
            "Reverse WHOIS lookup: find all domains registered by a specific registrant "
            "email, name, company, phone, or nameserver. Critical pivot technique — given "
            "an email address found in breach data, reveal all domains that person/org owns. "
            "Search fields: domain_keyword, domain_name, registrant_email, registrant_name, "
            "registrant_company, registrant_address, registrant_phone, registrar_name, "
            "name_servers. Costs 2 credits."
        )
    )
    async def breach_reverse_whois(
        search_term: str,
        search_field: str = "registrant_email",
        database: str = "current",
        page_size: int = 10,
    ) -> str:
        """
        Args:
            search_term: Value to search for (e.g. the registrant email)
            search_field: Which WHOIS field to match (default: registrant_email)
            database: 'current' for live registrations or 'historical' for expired/transferred
            page_size: Results per page (1–100)
        """
        try:
            data = await client.api_get("/v1/breach/reverse-whois", params={
                "search_term": search_term,
                "search_field": search_field,
                "database": database,
                "page_size": page_size,
            })
        except Exception as e:
            return formatting.error_response(f"Reverse WHOIS: {search_term}", e)

        count = data.get("total", data.get("count", len(data.get("domains", []))))
        facts = [
            f"Search field: {search_field}",
            f"Database: {database}",
            f"Domains found: {count}",
        ]
        return formatting.render(f"Reverse WHOIS: {search_term}", facts, data)

    @mcp.tool(
        description=(
            "Look up a phone number to find the registered owner name and linked social "
            "media accounts using the Eyecon Caller ID database. Provide the country code "
            "and number separately. Costs 2 credits."
        )
    )
    async def breach_caller_id(country_code: str, number: str) -> str:
        """
        Args:
            country_code: Dialing code without + sign (e.g. '1' for US, '44' for UK, '48' for Poland)
            number: Phone digits without country code or formatting (e.g. '5551234567')
        """
        try:
            data = await client.api_get("/v1/breach/caller-id", params={
                "country_code": country_code,
                "number": number,
            })
        except Exception as e:
            return formatting.error_response(f"Caller ID: +{country_code}{number}", e)

        name = data.get("name") or data.get("caller_name") or "Unknown"
        facts = [
            f"Number: +{country_code} {number}",
            f"Name: {name}",
            f"Social accounts: {len(data.get('social_accounts', []))}",
        ]
        return formatting.render(f"Caller ID: +{country_code} {number}", facts, data)

    @mcp.tool(
        description=(
            "Retrieve intelligence on a @gmail.com address: display name, profile picture, "
            "any exposed recovery email/phone, and account metadata. "
            "Only works with @gmail.com addresses. "
            "Costs 2 credits."
        )
    )
    async def breach_gmail_osint(email: str) -> str:
        """
        Args:
            email: A @gmail.com address to investigate
        """
        if not email.lower().endswith("@gmail.com"):
            return formatting.error_response(
                f"Gmail OSINT: {email}",
                ValueError("Only @gmail.com addresses are supported by this tool")
            )
        try:
            data = await client.api_get(f"/v1/breach/gmail-osint/{email}")
        except Exception as e:
            return formatting.error_response(f"Gmail OSINT: {email}", e)

        name = data.get("display_name") or data.get("name") or "Not found"
        facts = [
            f"Display name: {name}",
            f"Has profile photo: {bool(data.get('photo_url'))}",
            f"Recovery email exposed: {bool(data.get('recovery_email'))}",
            f"Recovery phone exposed: {bool(data.get('recovery_phone'))}",
        ]
        return formatting.render(f"Gmail OSINT: {email}", facts, data)

    @mcp.tool(
        description=(
            "Full breach profile for any target — runs the appropriate combination of "
            "breach_search (always), WHOIS (if input is a domain), and gmail_osint "
            "(if input is a @gmail.com address) in parallel. "
            "Use this as your starting point for any breach investigation. "
            "Cost: 3 credits minimum; up to 7 credits if WHOIS and Gmail OSINT both apply."
        )
    )
    async def breach_full_profile(query: str) -> str:
        """
        Args:
            query: Email, domain, username, phone, or IP to investigate
        """
        is_domain = "." in query and "@" not in query and " " not in query
        is_gmail = query.lower().endswith("@gmail.com")

        coros: list[Any] = [
            client.api_post("/v1/breach/search", {"query": query})
        ]
        section_names: list[str | None] = ["breach_search"]

        if is_domain:
            coros.append(client.api_get(f"/v1/breach/whois/{query}"))
            section_names.append("whois")

        if is_gmail:
            coros.append(client.api_get(f"/v1/breach/gmail-osint/{query}"))
            section_names.append("gmail_osint")

        results = await asyncio.gather(*coros, return_exceptions=True)

        return formatting.render_multi(
            title=f"Full Breach Profile: {query}",
            sections=section_names,
            results=list(results),
        )


# ── Fact extractors ────────────────────────────────────────────────────────────

def _breach_facts(data: dict[str, Any]) -> list[str]:
    facts = []
    # Try common response shapes
    records = (
        data.get("records")
        or data.get("breaches")
        or data.get("results")
        or []
    )
    facts.append(f"Breach records found: {len(records)}")

    # Hudson Rock stealer log presence
    hr = data.get("hudson_rock") or data.get("stealer_logs") or {}
    if hr:
        is_compromised = hr.get("is_compromised") or hr.get("found", False)
        facts.append(f"Hudson Rock stealer log: {'CONFIRMED' if is_compromised else 'Not found'}")

    # LeakIX exposure
    leakix = data.get("leakix") or {}
    leak_count = leakix.get("total", 0) if isinstance(leakix, dict) else 0
    if leak_count:
        facts.append(f"LeakIX exposed services: {leak_count}")

    # Most recent breach date
    if records:
        dates = [r.get("breach_date") or r.get("date") for r in records if r.get("breach_date") or r.get("date")]
        if dates:
            facts.append(f"Most recent breach: {max(dates)}")

    return facts or ["No breach data found for this query"]


def _whois_facts(data: dict[str, Any]) -> list[str]:
    facts = []
    registrant = data.get("registrant", {}) or {}
    if registrant.get("email"):
        facts.append(f"Registrant email: {registrant['email']}")
    if registrant.get("name"):
        facts.append(f"Registrant name: {registrant['name']}")
    if registrant.get("organization"):
        facts.append(f"Organization: {registrant['organization']}")
    if data.get("registrar"):
        facts.append(f"Registrar: {data['registrar']}")
    if data.get("creation_date"):
        facts.append(f"Created: {data['creation_date']}")
    if data.get("expiration_date"):
        facts.append(f"Expires: {data['expiration_date']}")
    return facts or ["WHOIS data returned but no parsed fields available"]
