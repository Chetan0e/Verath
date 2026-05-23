# Contributing to Verath

Thank you for your interest in improving Verath. This guide covers how to set up a development environment, follow project conventions, and submit changes.

## Code of conduct

Be respectful and constructive. Focus on the technical merits of proposals and reviews.

## Ways to contribute

- Report bugs with reproducible steps and environment details
- Suggest features via GitHub Discussions or issues
- Improve documentation (README, API examples, comments)
- Fix issues or add tests with pull requests
- Review open pull requests

## Development setup

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ (web & mobile) |
| MongoDB | 6.0+ (local or Atlas) |
| Docker | Optional, for `docker-compose` |
| Groq and/or Gemini API keys | For LLM and embeddings |

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/Verath.git
cd Verath
cp .env.example .env
```

Edit `.env` with a valid `MONGO_URI`, `SECRET_KEY` (32+ characters), and at least one of `GROQ_API_KEY` or `GEMINI_API_KEY`.

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx ruff black
```

Start the API:

```bash
# From repo root
make dev
# Or
cd backend && python run.py
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Create MongoDB indexes (recommended once per environment):

```bash
make migrate
```

### 3. Web client

```bash
cd web
npm install
npm run dev
```

Runs at [http://localhost:5173](http://localhost:5173). After login, the legacy dashboard is served from `web/legacy/`.

### 4. Mobile app (optional)

```bash
cd mobile
npm install
```

Set `BASE_URL` in `mobile/services/api.js` to your machine's LAN IP (not `localhost` on a physical device).

```bash
npx expo start
```

### 5. Docker (optional)

```bash
docker-compose up -d
```

Starts MongoDB and the backend container.

## Project layout

| Path | Purpose |
|------|---------|
| `backend/app/` | FastAPI application (routes, services, pipeline, workers) |
| `backend/tests/` | Pytest suite |
| `web/src/` | React + Vite auth landing |
| `web/legacy/` | Dashboard UI (HTML/CSS/JS) |
| `mobile/` | Expo / React Native client |
| `scripts/` | CLI utilities (`record_cli.py`) |

## Making changes

### Branch naming

- `feature/short-description`
- `fix/issue-description`
- `docs/what-you-updated`

### Commit messages

Use clear, imperative sentences:

- `Add pagination to timeline endpoint`
- `Fix Chroma rebuild when collection is missing`
- `Document WebSocket auth in README`

### Python style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Run **Ruff** before committing:

  ```bash
  cd backend && ruff check app/
  ```

- Prefer `async` route handlers when calling async database or HTTP code
- Use existing logging via `app.core.logging_config.logger`
- Add type hints on new public functions where practical
- Keep business logic in `app/services/`, not in route handlers

### JavaScript / React style

- Match existing patterns in `mobile/` and `web/src/`
- Reuse shared components (`Button`, `Input`, `ErrorBoundary`)
- Validate forms with `web/src/utils/validation.js` patterns

### Tests

Run the full suite from the repo root:

```bash
make test
```

Or targeted tests:

```bash
cd backend
pytest tests/test_health.py -v
pytest tests/test_auth.py -v
pytest tests/test_e2e.py -v -s
```

Add or update tests when you change:

- Authentication or authorization
- Memory storage, deletion, or export
- Pipeline / background worker behavior
- Privacy or reminder logic

CI runs on pushes and PRs to `main`: lint with Ruff, then pytest with coverage.

### Environment variables

New settings belong in `backend/app/config.py` with:

- A `Field(...)` definition
- A comment in `.env.example`
- A row in the README configuration table (if user-facing)

Never commit `.env` or API keys.

## Pull request checklist

Before opening a PR:

- [ ] Branch is up to date with `main`
- [ ] `ruff check app/` passes (backend changes)
- [ ] `pytest` passes (backend changes)
- [ ] README or CONTRIBUTING updated if behavior or setup changed
- [ ] No secrets or personal data in the diff
- [ ] Scope is focused (one feature or fix per PR when possible)

### PR description template

```markdown
## Summary
What changed and why.

## Test plan
- [ ] Step you ran to verify
- [ ] Edge case checked

## Screenshots (if UI)
```

## Reporting bugs

Include:

1. OS and Python version
2. Steps to reproduce
3. Expected vs actual behavior
4. Relevant logs from `backend/logs/` (redact tokens)
5. Whether MongoDB is local or Atlas

## Security issues

Do not open public issues for vulnerabilities. Email the maintainer privately with details and allow time for a fix before disclosure.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
