#!/usr/bin/env python3
"""
TestRail MCP Server

Exposes TestRail API as MCP tools for querying projects, suites, cases,
runs, results, milestones, and users.

Configuration via environment variables:
    TESTRAIL_URL       — your TestRail instance URL (e.g. https://mycompany.testrail.io)
    TESTRAIL_USERNAME  — TestRail username or email
    TESTRAIL_API_KEY   — TestRail API key (v2 password)

Usage:
    uv run testrail-mcp
    # or with stdio transport:
    uv run testrail-mcp --transport stdio

Example Hermes config:
    mcp_servers:
      testrail:
        command: "uv"
        args: ["run", "--directory", "/Users/ahmadilham/amartha_repo/testrail-mcp", "testrail-mcp"]
        env:
          TESTRAIL_URL: "https://your-instance.testrail.io"
          TESTRAIL_USERNAME: "your-email@amartha.com"
          TESTRAIL_API_KEY: "your-api-key"
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("testrail-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TESTRAIL_URL = os.getenv("TESTRAIL_URL", "").rstrip("/")
TESTRAIL_USERNAME = os.getenv("TESTRAIL_USERNAME", "")
TESTRAIL_API_KEY = os.getenv("TESTRAIL_API_KEY", "")


class TestRailClient:
    """Async HTTP client wrapper around the TestRail v2 API."""

    def __init__(self, base_url: str, username: str, api_key: str) -> None:
        self.base_url = f"{base_url}/index.php?/api/v2/"
        self.auth = (username, api_key)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=self.auth,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        logger.info("TestRail %s %s", method, url)
        resp = await client.request(method, url, **kwargs)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    async def get(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=body)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
app = Server("testrail-mcp")

# Global client instance — initialised on first use to respect env vars
_client: TestRailClient | None = None


def get_client() -> TestRailClient:
    global _client
    if _client is None:
        if not all([TESTRAIL_URL, TESTRAIL_USERNAME, TESTRAIL_API_KEY]):
            raise RuntimeError(
                "Missing TestRail credentials. Set TESTRAIL_URL, TESTRAIL_USERNAME, "
                "and TESTRAIL_API_KEY environment variables."
            )
        _client = TestRailClient(TESTRAIL_URL, TESTRAIL_USERNAME, TESTRAIL_API_KEY)
    return _client


def _fmt(obj: Any) -> str:
    """Pretty-print JSON for tool results."""
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tools: Projects
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_projects",
            description="Get all TestRail projects. Optionally filter by active/completed status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "is_completed": {
                        "type": "boolean",
                        "description": "Filter by completion status (omit for all).",
                    },
                },
            },
        ),
        Tool(
            name="get_project",
            description="Get a single TestRail project by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                },
                "required": ["project_id"],
            },
        ),
        # ---- Suites ----
        Tool(
            name="get_suites",
            description="Get all test suites for a TestRail project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_suite",
            description="Get a single test suite by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {
                        "type": "integer",
                        "description": "The ID of the test suite.",
                    },
                },
                "required": ["suite_id"],
            },
        ),
        # ---- Cases ----
        Tool(
            name="get_cases",
            description="Get test cases for a project and suite. Supports filtering by section, priority, type, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "suite_id": {
                        "type": "integer",
                        "description": "The ID of the test suite.",
                    },
                    "section_id": {
                        "type": "integer",
                        "description": "Filter by section ID (optional).",
                    },
                    "priority_id": {
                        "type": "integer",
                        "description": "Filter by priority (1=Critical, 2=High, 3=Medium, 4=Low) (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of cases to return (default: 250).",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Pagination offset (default: 0).",
                    },
                },
                "required": ["project_id", "suite_id"],
            },
        ),
        Tool(
            name="get_case",
            description="Get a single test case by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "integer",
                        "description": "The ID of the test case.",
                    },
                },
                "required": ["case_id"],
            },
        ),
        # ---- Sections ----
        Tool(
            name="get_sections",
            description="Get all sections for a project and suite.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "suite_id": {
                        "type": "integer",
                        "description": "The ID of the test suite.",
                    },
                },
                "required": ["project_id", "suite_id"],
            },
        ),
        # ---- Runs ----
        Tool(
            name="get_runs",
            description="Get test runs for a project. Filter by milestone, suite, or status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "milestone_id": {
                        "type": "integer",
                        "description": "Filter by milestone ID (optional).",
                    },
                    "suite_id": {
                        "type": "integer",
                        "description": "Filter by suite ID (optional).",
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "Filter by completion status (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum runs to return (default: 250).",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_run",
            description="Get a single test run by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "The ID of the test run.",
                    },
                },
                "required": ["run_id"],
            },
        ),
        # ---- Tests in a Run ----
        Tool(
            name="get_tests",
            description="Get all tests in a test run, with optional status filter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "The ID of the test run.",
                    },
                    "status_id": {
                        "type": "integer",
                        "description": "Filter by status (1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed) (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum tests to return (default: 250).",
                    },
                },
                "required": ["run_id"],
            },
        ),
        # ---- Results ----
        Tool(
            name="get_results",
            description="Get the latest results for all tests in a run, with optional status filter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "The ID of the test run.",
                    },
                    "status_id": {
                        "type": "integer",
                        "description": "Filter by status (1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed) (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 250).",
                    },
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="get_results_for_test",
            description="Get all results for a specific test.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {
                        "type": "integer",
                        "description": "The ID of the test.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 250).",
                    },
                },
                "required": ["test_id"],
            },
        ),
        Tool(
            name="add_result",
            description="Add a test result to a specific test in a run.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {
                        "type": "integer",
                        "description": "The ID of the test.",
                    },
                    "status_id": {
                        "type": "integer",
                        "description": "Status: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed.",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment/description of the result (optional).",
                    },
                    "elapsed": {
                        "type": "string",
                        "description": "Elapsed time, e.g. '5m 30s' (optional).",
                    },
                    "version": {
                        "type": "string",
                        "description": "Build/version string (optional).",
                    },
                    "defects": {
                        "type": "string",
                        "description": "Comma-separated defect IDs (optional).",
                    },
                },
                "required": ["test_id", "status_id"],
            },
        ),
        Tool(
            name="add_results_for_cases",
            description="Add results for multiple test cases in a run at once.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "The ID of the test run.",
                    },
                    "results": {
                        "type": "array",
                        "description": "Array of results. Each result: {case_id, status_id, comment?, elapsed?, version?}",
                        "items": {"type": "object"},
                    },
                },
                "required": ["run_id", "results"],
            },
        ),
        # ---- Write: Cases ----
        Tool(
            name="add_case",
            description="Create a new test case in a section.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {
                        "type": "integer",
                        "description": "The ID of the section to add the case to.",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the test case.",
                    },
                    "template_id": {
                        "type": "integer",
                        "description": "The ID of the template (field layout) (optional).",
                    },
                    "type_id": {
                        "type": "integer",
                        "description": "The ID of the case type (optional).",
                    },
                    "priority_id": {
                        "type": "integer",
                        "description": "Priority: 1=Critical, 2=High, 3=Medium, 4=Low (optional).",
                    },
                    "estimate": {
                        "type": "string",
                        "description": "Estimate, e.g. '30s' or '1m 45s' (optional).",
                    },
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone to link to the case (optional).",
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                    "custom_steps": {
                        "type": "string",
                        "description": "Test steps / request content. Plain text or HTML (e.g. a curl command) (optional).",
                    },
                    "custom_expected": {
                        "type": "string",
                        "description": "Expected result / response. Plain text or HTML (optional).",
                    },
                    "custom_preconds": {
                        "type": "string",
                        "description": "Preconditions. Plain text or HTML (optional).",
                    },
                    "custom_business_unit": {
                        "type": "integer",
                        "description": "Business unit ID (e.g. 24 = ACore - Growth). Required by TestRail for this project.",
                    },
                },
                "required": ["section_id", "title"],
            },
        ),
        Tool(
            name="update_case",
            description="Update an existing test case. Partial updates supported (only provided fields change).",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "integer",
                        "description": "The ID of the test case to update.",
                    },
                    "title": {
                        "type": "string",
                        "description": "The new title of the test case (optional).",
                    },
                    "type_id": {
                        "type": "integer",
                        "description": "The ID of the case type (optional).",
                    },
                    "priority_id": {
                        "type": "integer",
                        "description": "Priority: 1=Critical, 2=High, 3=Medium, 4=Low (optional).",
                    },
                    "estimate": {
                        "type": "string",
                        "description": "Estimate, e.g. '30s' or '1m 45s' (optional).",
                    },
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone to link to the case (optional).",
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                    "section_id": {
                        "type": "integer",
                        "description": "Move the case to this section ID (requires TestRail 6.5.2+) (optional).",
                    },
                    "custom_steps": {
                        "type": "string",
                        "description": "Test steps / request content. Plain text or HTML (e.g. a curl command) (optional).",
                    },
                    "custom_expected": {
                        "type": "string",
                        "description": "Expected result / response. Plain text or HTML (optional).",
                    },
                    "custom_preconds": {
                        "type": "string",
                        "description": "Preconditions. Plain text or HTML (optional).",
                    },
                    "custom_business_unit": {
                        "type": "integer",
                        "description": "Business unit ID (e.g. 24 = ACore - Growth).",
                    },
                },
                "required": ["case_id"],
            },
        ),
        # ---- Write: Runs ----
        Tool(
            name="add_run",
            description="Create a new test run in a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "suite_id": {
                        "type": "integer",
                        "description": "The ID of the test suite (required unless project is single-suite) (optional).",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the test run (optional).",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the test run (optional).",
                    },
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone to link to the run (optional).",
                    },
                    "assignedto_id": {
                        "type": "integer",
                        "description": "The ID of the user the run should be assigned to (optional).",
                    },
                    "include_all": {
                        "type": "boolean",
                        "description": "True to include all cases of the suite, false for a custom selection (optional).",
                    },
                    "case_ids": {
                        "type": "array",
                        "description": "Array of case IDs for a custom case selection (used when include_all is false) (optional).",
                        "items": {"type": "integer"},
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="update_run",
            description="Update an existing test run. Partial updates supported (only provided fields change).",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "The ID of the test run to update.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The new name of the test run (optional).",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the test run (optional).",
                    },
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone to link to the run (optional).",
                    },
                    "include_all": {
                        "type": "boolean",
                        "description": "True to include all cases of the suite, false for a custom selection (optional).",
                    },
                    "case_ids": {
                        "type": "array",
                        "description": "Array of case IDs for a custom case selection (used when include_all is false) (optional).",
                        "items": {"type": "integer"},
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                },
                "required": ["run_id"],
            },
        ),
        # ---- Write: Suites ----
        Tool(
            name="add_suite",
            description="Create a new test suite in a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the test suite.",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the test suite (optional).",
                    },
                },
                "required": ["project_id", "name"],
            },
        ),
        Tool(
            name="update_suite",
            description="Update an existing test suite. Partial updates supported (only provided fields change).",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {
                        "type": "integer",
                        "description": "The ID of the test suite to update.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The new name of the test suite (optional).",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the test suite (optional).",
                    },
                },
                "required": ["suite_id"],
            },
        ),
        # ---- Write: Milestones ----
        Tool(
            name="add_milestone",
            description="Create a new milestone in a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the milestone.",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the milestone (optional).",
                    },
                    "due_on": {
                        "type": "integer",
                        "description": "The due date as a UNIX timestamp (optional).",
                    },
                    "start_on": {
                        "type": "integer",
                        "description": "The scheduled start date as a UNIX timestamp (optional).",
                    },
                    "parent_id": {
                        "type": "integer",
                        "description": "The ID of the parent milestone (for sub-milestones) (optional).",
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                },
                "required": ["project_id", "name"],
            },
        ),
        Tool(
            name="update_milestone",
            description="Update an existing milestone. Partial updates supported (only provided fields change).",
            inputSchema={
                "type": "object",
                "properties": {
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone to update.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The new name of the milestone (optional).",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the milestone (optional).",
                    },
                    "due_on": {
                        "type": "integer",
                        "description": "The due date as a UNIX timestamp (optional).",
                    },
                    "start_on": {
                        "type": "integer",
                        "description": "The scheduled start date as a UNIX timestamp (optional).",
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "True if the milestone is completed (optional).",
                    },
                    "is_started": {
                        "type": "boolean",
                        "description": "True if the milestone is started (optional).",
                    },
                    "parent_id": {
                        "type": "integer",
                        "description": "The ID of the parent milestone (for sub-milestones) (optional).",
                    },
                    "refs": {
                        "type": "string",
                        "description": "Comma-separated list of references/requirements (optional).",
                    },
                },
                "required": ["milestone_id"],
            },
        ),
        # ---- Milestones ----
        Tool(
            name="get_milestones",
            description="Get all milestones for a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The ID of the project.",
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "Filter by completion status (optional).",
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_milestone",
            description="Get a single milestone by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "milestone_id": {
                        "type": "integer",
                        "description": "The ID of the milestone.",
                    },
                },
                "required": ["milestone_id"],
            },
        ),
        # ---- Users ----
        Tool(
            name="get_users",
            description="Get all users in the TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_user",
            description="Get a single user by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The ID of the user.",
                    },
                },
                "required": ["user_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    client = get_client()

    try:
        # -- Projects --
        if name == "get_projects":
            path = "get_projects"
            if "is_completed" in arguments:
                path += f"/&is_completed={int(arguments['is_completed'])}"
            data = await client.get(path)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_project":
            data = await client.get(f"get_project/{arguments['project_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Suites --
        elif name == "get_suites":
            data = await client.get(f"get_suites/{arguments['project_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_suite":
            data = await client.get(f"get_suite/{arguments['suite_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Cases --
        elif name == "get_cases":
            pid = arguments["project_id"]
            sid = arguments["suite_id"]
            params = []
            for key in ("section_id", "priority_id", "limit", "offset"):
                if key in arguments:
                    params.append(f"&{key}={arguments[key]}")
            qs = "".join(params)
            data = await client.get(f"get_cases/{pid}&suite_id={sid}{qs}")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_case":
            data = await client.get(f"get_case/{arguments['case_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Sections --
        elif name == "get_sections":
            pid = arguments["project_id"]
            sid = arguments["suite_id"]
            data = await client.get(f"get_sections/{pid}&suite_id={sid}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Runs --
        elif name == "get_runs":
            pid = arguments["project_id"]
            params = []
            for key in ("milestone_id", "suite_id", "is_completed", "limit"):
                if key in arguments:
                    val = arguments[key]
                    if isinstance(val, bool):
                        val = int(val)
                    params.append(f"&{key}={val}")
            qs = "".join(params)
            data = await client.get(f"get_runs/{pid}{qs}")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_run":
            data = await client.get(f"get_run/{arguments['run_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Tests --
        elif name == "get_tests":
            rid = arguments["run_id"]
            params = []
            for key in ("status_id", "limit"):
                if key in arguments:
                    params.append(f"&{key}={arguments[key]}")
            qs = "".join(params)
            data = await client.get(f"get_tests/{rid}{qs}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Results --
        elif name == "get_results":
            rid = arguments["run_id"]
            params = []
            for key in ("status_id", "limit"):
                if key in arguments:
                    params.append(f"&{key}={arguments[key]}")
            qs = "".join(params)
            data = await client.get(f"get_results_for_run/{rid}{qs}")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_results_for_test":
            tid = arguments["test_id"]
            limit = arguments.get("limit", 250)
            data = await client.get(f"get_results/{tid}&limit={limit}")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "add_result":
            body: dict[str, Any] = {"status_id": arguments["status_id"]}
            for field in ("comment", "elapsed", "version", "defects"):
                if field in arguments and arguments[field]:
                    body[field] = arguments[field]
            data = await client.post(f"add_result/{arguments['test_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "add_results_for_cases":
            data = await client.post(
                f"add_results_for_cases/{arguments['run_id']}",
                {"results": arguments["results"]},
            )
            return [TextContent(type="text", text=_fmt(data))]

        # -- Write: Cases --
        elif name == "add_case":
            body = {"title": arguments["title"]}
            for field in (
                "template_id", "type_id", "priority_id", "estimate", "milestone_id", "refs",
                "custom_steps", "custom_expected", "custom_preconds",
                "custom_business_unit", "custom_automation_type_new", "custom_platform",
                "custom_test_in_prod",
            ):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"add_case/{arguments['section_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "update_case":
            body = {}
            for field in (
                "title", "type_id", "priority_id", "estimate", "milestone_id", "refs", "section_id",
                "custom_steps", "custom_expected", "custom_preconds", "custom_business_unit",
            ):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"update_case/{arguments['case_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        # -- Write: Runs --
        elif name == "add_run":
            body = {}
            for field in (
                "suite_id", "name", "description", "milestone_id",
                "assignedto_id", "include_all", "case_ids", "refs",
            ):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"add_run/{arguments['project_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "update_run":
            body = {}
            for field in ("name", "description", "milestone_id", "include_all", "case_ids", "refs"):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"update_run/{arguments['run_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        # -- Write: Suites --
        elif name == "add_suite":
            body = {"name": arguments["name"]}
            if arguments.get("description") is not None:
                body["description"] = arguments["description"]
            data = await client.post(f"add_suite/{arguments['project_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "update_suite":
            body = {}
            for field in ("name", "description"):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"update_suite/{arguments['suite_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        # -- Write: Milestones --
        elif name == "add_milestone":
            body = {"name": arguments["name"]}
            for field in ("description", "due_on", "start_on", "parent_id", "refs"):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"add_milestone/{arguments['project_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "update_milestone":
            body = {}
            for field in (
                "name", "description", "due_on", "start_on",
                "is_completed", "is_started", "parent_id", "refs",
            ):
                if field in arguments and arguments[field] is not None:
                    body[field] = arguments[field]
            data = await client.post(f"update_milestone/{arguments['milestone_id']}", body)
            return [TextContent(type="text", text=_fmt(data))]

        # -- Milestones --
        elif name == "get_milestones":
            pid = arguments["project_id"]
            path = f"get_milestones/{pid}"
            if "is_completed" in arguments:
                path += f"/&is_completed={int(arguments['is_completed'])}"
            data = await client.get(path)
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_milestone":
            data = await client.get(f"get_milestone/{arguments['milestone_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        # -- Users --
        elif name == "get_users":
            data = await client.get("get_users")
            return [TextContent(type="text", text=_fmt(data))]

        elif name == "get_user":
            data = await client.get(f"get_user/{arguments['user_id']}")
            return [TextContent(type="text", text=_fmt(data))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as exc:
        logger.error("TestRail API error: %s %s", exc.response.status_code, exc.response.text)
        return [
            TextContent(
                type="text",
                text=f"TestRail API error ({exc.response.status_code}): {exc.response.text}",
            )
        ]
    except Exception as exc:
        logger.exception("Tool error")
        return [TextContent(type="text", text=f"Error: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the TestRail MCP server via stdio transport."""
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (reader, writer):
        await app.run(reader, writer, app.create_initialization_options())


if __name__ == "__main__":
    main()
