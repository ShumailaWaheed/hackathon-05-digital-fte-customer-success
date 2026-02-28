"""MCP Server entry point — registers all 7 tools for incubation phase.

Constitution Principle VIII: Every tool must exist in MCP form (Stage 1)
and production @function_tool form (Stage 2).

Usage with Claude Code:
  Add to MCP config: { "command": "python", "args": ["incubation/mcp_server/server.py"] }
"""

import asyncio
import json
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.search_knowledge_base import search_knowledge_base
from tools.create_ticket import create_ticket
from tools.get_customer_history import get_customer_history
from tools.escalate_to_human import escalate_to_human
from tools.send_response import send_response
from tools.analyze_sentiment import analyze_sentiment
from tools.generate_daily_report import generate_daily_report

server = Server("customer-success-fte")

# Tool registry
TOOL_HANDLERS = {
    "search_knowledge_base": search_knowledge_base,
    "create_ticket": create_ticket,
    "get_customer_history": get_customer_history,
    "escalate_to_human": escalate_to_human,
    "send_response": send_response,
    "analyze_sentiment": analyze_sentiment,
    "generate_daily_report": generate_daily_report,
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_knowledge_base",
            description="Search the knowledge base using semantic similarity (pgvector).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "max_results": {"type": "integer", "default": 5, "description": "Max results to return"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="create_ticket",
            description="Create a support ticket for an inbound message. MUST be called first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer UUID"},
                    "issue": {"type": "string", "description": "Issue description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                    "channel": {"type": "string", "enum": ["gmail", "whatsapp", "webform"]},
                    "metadata": {"type": "object", "default": {}},
                },
                "required": ["customer_id", "issue", "channel"],
            },
        ),
        Tool(
            name="get_customer_history",
            description="Retrieve full cross-channel conversation history for a customer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer UUID"},
                },
                "required": ["customer_id"],
            },
        ),
        Tool(
            name="escalate_to_human",
            description="Escalate a ticket to a human agent with full context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket UUID"},
                    "reason": {"type": "string", "description": "Escalation reason"},
                },
                "required": ["ticket_id", "reason"],
            },
        ),
        Tool(
            name="send_response",
            description="Send a response via the appropriate channel with auto-formatting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket UUID"},
                    "message": {"type": "string", "description": "Response message"},
                    "channel": {"type": "string", "enum": ["gmail", "whatsapp", "webform"]},
                },
                "required": ["ticket_id", "message", "channel"],
            },
        ),
        Tool(
            name="analyze_sentiment",
            description="Analyze sentiment of a message. Returns float 0.0 (negative) to 1.0 (positive).",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message text to analyze"},
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="generate_daily_report",
            description="Generate daily sentiment and metrics report.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["date"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error in {name}: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
