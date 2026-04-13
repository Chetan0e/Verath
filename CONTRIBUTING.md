# Contributing to SecondBrain

Thank you for your interest in contributing to SecondBrain! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [PR Guidelines](#pr-guidelines)
- [Adding a New Extraction Intent](#adding-a-new-extraction-intent)
- [Adding a New API Endpoint](#adding-a-new-api-endpoint)

## Development Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or MongoDB Atlas)
- Ollama (for local LLM)
- Node.js 18+ (for mobile app)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/secondbrain.git
cd secondbrain

# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python -c "import asyncio; from app.services.database import connect_to_mongo, create_indexes; asyncio.run(connect_to_mongo())"

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### Web Dashboard Setup

```bash
cd web
python -m http.server 8080
# Open http://localhost:8080
```

### Mobile App Setup

```bash
cd mobile
npm install
npx expo start
```

## Running Tests

### Unit Tests

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### End-to-End Tests

```bash
# Ensure backend is running on http://localhost:8002
make e2e

# Or manually
ENV=test pytest tests/test_e2e.py -v -s
```

### Linting

```bash
# Run Ruff linter
make lint

# Or manually
cd backend
ruff check app/
black --check app/

# Auto-fix with Black
black app/
```

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Maximum line length: 100 characters
- Use Ruff for linting and Black for formatting

### JavaScript/React Native

- Use ES6+ features
- Follow Airbnb JavaScript Style Guide
- Use meaningful variable and function names
- Add comments for complex logic

### Git Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(auth): add token refresh endpoint

Implement JWT token refresh with rotation to improve security.
The refresh endpoint validates the refresh token and issues a new
access token with a new refresh token, invalidating the old one.

Closes #123
```

## PR Guidelines

### Branch Strategy

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them
3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request with:
   - Clear title and description
   - Reference related issues
   - Screenshots for UI changes
   - Test results

### PR Review Process

1. Ensure all CI checks pass
2. Request review from maintainers
3. Address review feedback
4. Update PR as needed
5. Wait for approval and merge

### Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main

## Adding a New Extraction Intent

Extraction intents classify the type of memory (e.g., meeting, task, deadline). Here's how to add a new one:

### Step 1: Update Intent Classifier

Edit `backend/app/services/extractor.py`:

```python
# Add to intent patterns
INTENT_PATTERNS = {
    "meeting": [...],
    "task": [...],
    "deadline": [...],
    "your_new_intent": [
        r"keyword1",
        r"keyword2",
        # Add patterns for your intent
    ]
}
```

### Step 2: Add Tests

Create `backend/tests/test_your_new_intent.py`:

```python
import pytest
from app.services.extractor import extract_intent

def test_extract_your_new_intent():
    text = "text that should match your intent"
    result = extract_intent(text)
    assert result == "your_new_intent"
```

### Step 3: Update Documentation

Add your new intent to `API_REFERENCE.md` and `README.md`.

### Step 4: Run Tests

```bash
pytest tests/test_your_new_intent.py
pytest
```

## Adding a New API Endpoint

Here's a step-by-step guide to adding a new API endpoint:

### Step 1: Define Pydantic Models

Create request/response models in `backend/app/models/`:

```python
# backend/app/models/your_feature.py
from pydantic import BaseModel, Field
from typing import Optional

class YourRequest(BaseModel):
    field1: str = Field(..., description="Description")
    field2: Optional[int] = None

class YourResponse(BaseModel):
    result: str
    status: str
```

### Step 2: Create Service Function

Add business logic in `backend/app/services/`:

```python
# backend/app/services/your_service.py
import logging

logger = logging.getLogger(__name__)

async def process_your_feature(data: YourRequest) -> YourResponse:
    """Process your feature logic here."""
    try:
        # Your logic
        result = "processed"
        return YourResponse(result=result, status="success")
    except Exception as e:
        logger.error(f"Error processing: {e}")
        raise
```

### Step 3: Create Route Handler

Add endpoint in `backend/app/routes/`:

```python
# backend/app/routes/your_feature.py
from fastapi import APIRouter, Depends, HTTPException
from app.models.your_feature import YourRequest, YourResponse
from app.services.your_service import process_your_feature
from app.services.auth import get_current_user_id

router = APIRouter()

@router.post("/your-endpoint")
async def your_endpoint(
    request: YourRequest,
    user_id: str = Depends(get_current_user_id)
) -> YourResponse:
    """Description of your endpoint."""
    try:
        return await process_your_feature(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Register Router

Add to `backend/app/main.py`:

```python
from app.routes.your_feature import router as your_feature_router

app.include_router(your_feature_router)
```

### Step 5: Add Tests

Create `backend/tests/test_your_feature.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_your_endpoint_success():
    response = client.post(
        "/your-endpoint",
        json={"field1": "test"},
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
```

### Step 6: Update Documentation

Add endpoint to `API_REFERENCE.md`:

```markdown
### POST /your-endpoint

Description of your endpoint.

**Auth Required:** Yes

**Request Body:**
```json
{
  "field1": "string",
  "field2": "int (optional)"
}
```

**Response (200):**
```json
{
  "result": "string",
  "status": "string"
}
```
```

### Step 7: Run Tests

```bash
pytest tests/test_your_feature.py
pytest
make lint
```

## Reporting Issues

When reporting bugs or suggesting features:

1. Check existing issues first
2. Use the issue templates
3. Provide clear description
4. Include steps to reproduce
5. Add screenshots if applicable
6. Specify environment details

## Getting Help

- Check documentation in `docs/` folder
- Review existing code for patterns
- Ask questions in GitHub Discussions
- Contact maintainers for urgent issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
