from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from pathlib import Path
from typing import Any

from .models import Deal, KnowledgeHit

LOGGER = logging.getLogger(__name__)


class LocalKnowledgeProvider:
    name = "Vybe fallback"
    live = False

    def __init__(self, knowledge_path: Path):
        self.knowledge_path = knowledge_path
        self.entries = self._load()

    def search(self, deal: Deal, limit: int = 4) -> list[KnowledgeHit]:
        query_tokens = _tokens(" ".join([deal.industry, deal.segment, deal.competitor, *deal.objections, deal.customer_context]))
        scored = []
        for entry in self.entries:
            haystack = _tokens(" ".join(str(entry.get(key, "")) for key in ("title", "category", "summary", "guidance")))
            score = len(query_tokens & haystack)
            if any("pricing" in item.lower() for item in deal.objections) and "value" in haystack:
                score += 3
            if any("security" in item.lower() for item in deal.objections) and "security" in haystack:
                score += 3
            if any("implementation" in item.lower() for item in deal.objections) and "implementation" in haystack:
                score += 3
            if any("stakeholder" in item.lower() for item in deal.objections) and "stakeholder" in haystack:
                score += 3
            scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            KnowledgeHit(
                title=str(entry.get("title", "Vault reference")),
                category=str(entry.get("category", "Knowledge")),
                summary=str(entry.get("summary", "")),
                guidance=str(entry.get("guidance", "")),
                relevance_score=score,
            )
            for score, entry in scored[:limit]
        ]

    def _load(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.knowledge_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not load Vault fallback data: %s", exc)
            return []


class VybeMCPProvider:
    name = "Vybe MCP"
    live = True

    def __init__(self, command: str, args: list[str], cwd: str | None = None):
        self.command = command
        self.args = args
        self.cwd = cwd

    def search(self, deal: Deal, limit: int = 4) -> list[KnowledgeHit]:
        query = " ".join([deal.industry, *deal.objections, deal.customer_context])
        return asyncio.run(self._search(query, limit))

    async def _search(self, query: str, limit: int) -> list[KnowledgeHit]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("The optional MCP client is not installed") from exc

        server = StdioServerParameters(command=self.command, args=self.args, cwd=self.cwd)
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "vault_search",
                    arguments={"query": query, "max_results": limit},
                )
        return _parse_mcp_result(result)


class ResilientKnowledgeProvider:
    name = "Vybe Vault"

    def __init__(self, local: LocalKnowledgeProvider, remote: VybeMCPProvider | None = None):
        self.local = local
        self.remote = remote
        self.live = remote is not None

    def search(self, deal: Deal, limit: int = 4) -> list[KnowledgeHit]:
        if self.remote:
            try:
                hits = self.remote.search(deal, limit)
                if hits:
                    return hits
            except Exception as exc:
                LOGGER.warning("Vybe MCP search failed; using local knowledge: %s", exc)
        return self.local.search(deal, limit)


def build_knowledge_provider(project_root: Path) -> ResilientKnowledgeProvider:
    local = LocalKnowledgeProvider(project_root / "data" / "knowledge.json")
    command = os.getenv("VYBE_MCP_COMMAND")
    if not command:
        return ResilientKnowledgeProvider(local)
    raw_args = os.getenv("VYBE_MCP_ARGS", "")
    try:
        args = json.loads(raw_args) if raw_args.strip().startswith("[") else shlex.split(raw_args)
    except json.JSONDecodeError:
        args = shlex.split(raw_args)
    return ResilientKnowledgeProvider(
        local,
        VybeMCPProvider(command, [str(item) for item in args], os.getenv("VYBE_MCP_CWD")),
    )


def _parse_mcp_result(result: Any) -> list[KnowledgeHit]:
    texts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    raw = "\n".join(texts)
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        return [KnowledgeHit("Vybe Vault result", "Vault", raw[:500], raw[:1000], relevance_score=1)] if raw else []
    if isinstance(values, dict):
        values = values.get("results", [])
    return [
        KnowledgeHit(
            title=str(item.get("title", "Vault reference")),
            category=str(item.get("category", "Knowledge")),
            summary=str(item.get("summary", "")),
            guidance=str(item.get("guidance", item.get("summary", ""))),
            relevance_score=int(item.get("relevance_score", 0) or 0),
        )
        for item in values
        if isinstance(item, dict)
    ]


def _tokens(value: str) -> set[str]:
    return {token for token in value.lower().replace("/", " ").split() if len(token) > 2}
