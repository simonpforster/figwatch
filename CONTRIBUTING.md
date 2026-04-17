# Contributing to FigWatch

## Project structure

```
server.py              Docker entrypoint — webhook HTTP server
macos/
  FigWatch.py          macOS menu bar app (PyObjC)
  setup.py             py2app build config
figwatch/              shared core package
  domain.py            WorkItem, trigger config, constants
  processor.py         audit pipeline — ack, skill, reply
  skills.py            skill discovery, introspection, execution
  watcher.py           FigmaWatcher — comment polling (macOS path)
  ack_updater.py       live queue-position updates
  webhook_monitor.py   missed webhook detection
  queue_stats.py       queue depth tracking
  metrics.py           OpenTelemetry metric definitions
  logging_config.py    structured logging (text + JSON)
  log_context.py       per-audit contextual log fields
  providers/
    figma.py           Figma REST API client
    ai/                AI provider abstraction
  handlers/            shared utilities
  skills/              bundled skill .md files + references
tests/                 pytest test suite
docs/                  documentation
```

## Development setup

### Prerequisites

- Python 3.11
- Docker and Docker Compose (for server work)

### Server (Docker)

```bash
cp .env.example .env          # fill in your values
docker compose up -d --build  # start the server
docker compose logs -f        # watch logs
```

For local webhook testing, use [ngrok](https://ngrok.com):

```bash
ngrok http 8080
```

Then register a webhook pointing at your ngrok URL — see [docs/docker.md](docs/docker.md#5-register-the-webhook-with-figma).

### macOS app

```bash
make install   # install py2app + PyObjC (once)
make build     # build macos/dist/FigWatch.app
make clean     # remove build artefacts
```

### Running tests

```bash
pip install -e ".[dev]"
pytest
```

## How the code is organised

FigWatch has two entrypoints that share a common core:

- **macOS app** (`macos/FigWatch.py`) — polls Figma for comments on a timer, dispatches work to queue-backed workers, renders UI via PyObjC.
- **Server** (`server.py`) — receives Figma `FILE_COMMENT` webhooks over HTTP, dispatches work to a `ThreadPoolExecutor`.

Both entrypoints call the same pipeline in `figwatch/processor.py`: acknowledge the comment, run the skill via an AI provider, post the reply.

### Adding a new AI provider

1. Create `figwatch/providers/ai/your_provider.py` implementing the `AIProvider` protocol (see `__init__.py`)
2. Add your provider to `make_provider()` in `figwatch/providers/ai/__init__.py`
3. Add any new env vars to `.env.example` and `docker-compose.yml`

### Adding a built-in skill

1. Create a directory under `figwatch/skills/` with a `skill.md` file
2. Add a default trigger mapping in `figwatch/domain.py` (`DEFAULT_TRIGGERS`)
3. Add reference files alongside `skill.md` if the skill needs them

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Include a short description of what changed and why
- Add or update tests if you're changing core logic
- Run `pytest` before submitting

## Code style

- No linter is enforced yet — match the style of surrounding code
- Use type hints for function signatures in new code
- Keep imports sorted: stdlib, third-party, local
