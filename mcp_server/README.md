# Local MCP Server

This folder contains a separate local-only MCP server for safe project inspection and backend discovery.

It does not replace the app's existing MCP server at `packages/api/mcp_server.py`. This adapter exists so AI clients can inspect the repository, backend routes, OCR support, and possible dataset or training artifacts without changing the main app architecture.

## What MCP Means Here

This server exposes safe read-oriented tools over stdio using Python MCP (`FastMCP`).

It is intended for local development only.

## Install

Windows PowerShell:

```powershell
cd mcp_server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
cd mcp_server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```powershell
cd mcp_server
python server.py
```

The server uses stdio by default and is not exposed over the network.

## Environment

Optional environment variables:

- `BACKEND_URL` default: `http://127.0.0.1:8000`
- `GEMINI_API_KEY` only needed for `run_ocr_on_image_path`

The server loads the project root `.env` if present.

## Example Client Config

See `example_mcp_config.json`.

You must replace the placeholder absolute path with your own local path.

Example shape:

```json
{
  "mcpServers": {
    "project-local-mcp": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/mcp_server/server.py"],
      "env": {
        "BACKEND_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

## Tools

- `health_check()`
- `inspect_project_structure()`
- `list_available_routes()`
- `list_datasets()`
- `get_training_status()`
- `read_recent_training_log(lines: int = 100)`
- `run_ocr_on_image_path(image_path: str)`
- `get_latest_eval_metrics()`

## Notes On Current Behavior

- This repo is mainly a transcript audit and OCR application, not a model-training repository.
- Dataset and training tools may return fixture-style files or honest "not available" responses when no matching artifacts exist.
- OCR uses the existing local parser from `packages/core/pdf_parser.py` when possible.
- Route discovery prefers `BACKEND_URL/openapi.json` and falls back to importing the FastAPI app directly.

## Safety Notes

- No delete tools are exposed.
- No overwrite tools are exposed.
- No long-running jobs are started.
- `.env` files are not surfaced by the tree scanner.
- Large binary/model folders are excluded from project inspection.
- The server is intended for local stdio use only.

## Troubleshooting

If `health_check()` fails:

- make sure the backend is running
- verify `BACKEND_URL`
- confirm `http://127.0.0.1:8000/health` is reachable

If `run_ocr_on_image_path()` fails:

- ensure `GEMINI_API_KEY` is available
- pass an existing local image or PDF path

If your MCP client cannot connect:

- verify the absolute path in the client config
- make sure the venv has `mcp[cli]` installed
- try running `python server.py` manually first
