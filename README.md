# TestRail MCP Server

MCP (Model Context Protocol) server for TestRail — exposes TestRail test management
API as MCP tools that any MCP-compatible AI agent (Claude Desktop, Hermes Agent, Cursor, etc.) can use.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- TestRail instance with API access enabled

## Setup

```bash
# Clone the repo
git clone https://github.com/ahmadachmed/testrail-mcp.git
cd testrail-mcp

# Install deps (uv — recommended)
uv sync

# Or with pip
pip install -e .
```

### Environment Variables

Set these in your shell or in your MCP client config:

| Variable            | Description                                      |
|---------------------|--------------------------------------------------|
| `TESTRAIL_URL`      | Your TestRail instance URL (e.g. `https://your-instance.testrail.io`) |
| `TESTRAIL_USERNAME` | Your TestRail email                              |
| `TESTRAIL_API_KEY`  | Your TestRail API key                            |

> **Getting an API Key**: Go to TestRail → My Settings → API Keys → Add Key.
> The key acts as a password in HTTP Basic Auth (username = your email, password = API key).

## Usage

### Run directly

```bash
uv run testrail-mcp
```

### MCP Client Configuration

#### Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  testrail:
    command: "uv"
    args: ["run", "--directory", "/path/to/testrail-mcp", "testrail-mcp"]
    env:
      TESTRAIL_URL: "https://your-instance.testrail.io"
      TESTRAIL_USERNAME: "your-email@example.com"
      TESTRAIL_API_KEY: "your-api-key"
```

Then restart Hermes Agent. Tools will appear with the `mcp_testrail_` prefix.

#### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/testrail-mcp", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@example.com",
        "TESTRAIL_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Available Tools

### Projects
| Tool              | Description                        |
|-------------------|------------------------------------|
| `get_projects`    | List all TestRail projects         |
| `get_project`     | Get a single project by ID         |

### Suites
| Tool          | Description                              |
|---------------|------------------------------------------|
| `get_suites`  | Get test suites for a project            |
| `get_suite`   | Get a single suite by ID                 |
| `add_suite`   | Create a new test suite in a project     |
| `update_suite`| Update an existing test suite            |

### Sections
| Tool           | Description                                   |
|----------------|-----------------------------------------------|
| `get_sections` | Get sections in a project/suite               |

### Cases
| Tool           | Description                                   |
|----------------|-----------------------------------------------|
| `get_cases`    | Get test cases (filters: section, priority)   |
| `get_case`     | Get a single test case by ID                  |
| `add_case`     | Create a new test case in a section           |
| `update_case`  | Update an existing test case                  |

### Runs & Tests
| Tool           | Description                                   |
|----------------|-----------------------------------------------|
| `get_runs`     | Get test runs (filters: milestone, suite)     |
| `get_run`      | Get a single test run by ID                   |
| `add_run`      | Create a new test run in a project            |
| `update_run`   | Update an existing test run                   |
| `get_tests`    | Get tests in a run (filter by status)         |

### Results
| Tool                     | Description                                  |
|--------------------------|----------------------------------------------|
| `get_results`            | Get results for a test run                   |
| `get_results_for_test`   | Get all results for a specific test           |
| `add_result`             | Add a single test result                     |
| `add_results_for_cases`  | Bulk-add results for multiple cases           |

### Milestones
| Tool                | Description                              |
|---------------------|------------------------------------------|
| `get_milestones`    | Get milestones for a project             |
| `get_milestone`     | Get a single milestone by ID             |
| `add_milestone`     | Create a new milestone in a project      |
| `update_milestone`  | Update an existing milestone             |

### Users
| Tool         | Description              |
|--------------|--------------------------|
| `get_users`  | Get all users            |
| `get_user`   | Get a single user by ID  |

## Reference

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
