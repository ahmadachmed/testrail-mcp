# TestRail MCP Server

MCP (Model Context Protocol) server for TestRail — exposes TestRail test management
API as MCP tools that any MCP-compatible agent (including Hermes Agent) can use.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- TestRail instance with API access enabled

## Setup

```bash
cd ~/amartha_repo/testrail-mcp

# Install deps (uv)
uv sync

# Or with pip
pip install -e .
```

Set environment variables:

```bash
export TESTRAIL_URL="https://your-instance.testrail.io"
export TESTRAIL_USERNAME="your-email@amartha.com"
export TESTRAIL_API_KEY="your-api-key"
```

> **API Key**: Go to TestRail → My Settings → API Keys. The key is the "password"
> in HTTP Basic Auth (username = your email, password = API key).

## Usage

### Run directly

```bash
uv run testrail-mcp
```

### Hermes Agent Integration

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  testrail:
    command: "uv"
    args: ["run", "--directory", "/Users/ahmadilham/amartha_repo/testrail-mcp", "testrail-mcp"]
    env:
      TESTRAIL_URL: "https://your-instance.testrail.io"
      TESTRAIL_USERNAME: "your-email@amartha.com"
      TESTRAIL_API_KEY: "your-api-key"
```

Then restart Hermes Agent. Tools will appear as `mcp_testrail_get_projects`, etc.

## Available Tools

| Tool                    | Description                              |
|-------------------------|------------------------------------------|
| `get_projects`          | List all TestRail projects               |
| `get_project`           | Get a single project by ID               |
| `get_suites`            | Get test suites for a project            |
| `get_suite`             | Get a single suite by ID                 |
| `get_cases`             | Get test cases (filters: section, prio)  |
| `get_case`              | Get a single test case by ID             |
| `get_sections`          | Get sections in a project/suite          |
| `get_runs`              | Get test runs (filters: milestone, etc.) |
| `get_run`               | Get a single test run by ID              |
| `get_tests`             | Get tests in a run (filter by status)    |
| `get_results`           | Get results for a test run               |
| `get_results_for_test`  | Get all results for a specific test      |
| `add_result`            | Add a single test result                 |
| `add_results_for_cases` | Bulk-add results for multiple cases      |
| `add_case`              | Create a new test case in a section      |
| `update_case`           | Update an existing test case             |
| `add_run`               | Create a new test run in a project       |
| `update_run`            | Update an existing test run              |
| `add_suite`             | Create a new test suite in a project     |
| `update_suite`          | Update an existing test suite            |
| `add_milestone`         | Create a new milestone in a project      |
| `update_milestone`      | Update an existing milestone             |
| `get_milestones`        | Get milestones for a project             |
| `get_milestone`         | Get a single milestone by ID             |
| `get_users`             | Get all users                            |
| `get_user`              | Get a single user by ID                  |

### Status IDs

| ID | Status   |
|----|----------|
| 1  | Passed   |
| 2  | Blocked  |
| 3  | Untested |
| 4  | Retest   |
| 5  | Failed   |

### Priority IDs

| ID | Priority |
|----|----------|
| 1  | Critical |
| 2  | High     |
| 3  | Medium   |
| 4  | Low      |
