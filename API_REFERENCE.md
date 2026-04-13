# SecondBrain API Reference

Complete API documentation for SecondBrain backend.

Base URL: `http://localhost:8002`

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### POST /auth/signup

Create a new user account.

**Request Body:**
```json
{
  "username": "string (required, min 3 chars)",
  "password": "string (required, min 6 chars)"
}
```

**Response (201):**
```json
{
  "message": "User created successfully",
  "username": "string"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

---

### POST /auth/login

Login and receive access/refresh tokens.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "access_token": "string",
  "refresh_token": "string"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

---

### POST /auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

**Response (200):**
```json
{
  "access_token": "string",
  "refresh_token": "string"
}
```

---

### POST /auth/logout

Logout and blacklist current token.

**Auth Required:** Yes

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

---

## Memory Endpoints

### POST /record

Submit text for memory extraction and storage.

**Auth Required:** Yes

**Request Body:**
```json
{
  "text": "string (required)",
  "speaker": "string (optional)"
}
```

**Response (200):**
```json
{
  "memory_id": "string",
  "intent": "string",
  "entities": {...},
  "importance": 0.8
}
```

---

### GET /timeline

Get paginated timeline of memories with optional filters.

**Auth Required:** Yes

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 20, max: 100)
- `start_date` (string, ISO 8601, optional)
- `end_date` (string, ISO 8601, optional)
- `speaker` (string, optional)
- `intent` (string, optional)

**Response (200):**
```json
{
  "timeline": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### GET /query

Semantic search across memories.

**Auth Required:** Yes

**Query Parameters:**
- `q` (string, required) - Search query

**Response (200):**
```json
{
  "answer": "string",
  "sources": [...]
}
```

**Example:**
```bash
curl "http://localhost:8002/query?q=meeting%20with%20Sarah" \
  -H "Authorization: Bearer <token>"
```

---

### DELETE /memory/{id}

Delete a specific memory.

**Auth Required:** Yes

**Path Parameters:**
- `id` (string) - Memory ID

**Response (200):**
```json
{
  "message": "Memory deleted successfully"
}
```

---

### GET /graph

Get memory graph visualization data.

**Auth Required:** Yes

**Query Parameters:**
- `limit` (int, default: 100, max: 500)

**Response (200):**
```json
{
  "nodes": [
    {
      "id": "string",
      "text": "string",
      "intent": "string",
      "importance": 0.8
    }
  ],
  "links": [
    {
      "source": "string",
      "target": "string",
      "type": "string"
    }
  ]
}
```

---

### GET /export

Export memories in various formats.

**Auth Required:** Yes

**Query Parameters:**
- `format` (string, required) - "json", "csv", or "pdf"
- `intent_filter` (string, optional)
- `start_date` (string, ISO 8601, optional)
- `end_date` (string, ISO 8601, optional)

**Response (200):**
- JSON: Returns JSON object with memories array
- CSV: Returns CSV file as attachment
- PDF: Returns PDF file as attachment

**Example:**
```bash
curl "http://localhost:8002/export?format=csv" \
  -H "Authorization: Bearer <token>" \
  -o memories.csv
```

---

## Advanced Endpoints

### GET /summary

Get daily summary of memories.

**Auth Required:** Yes

**Response (200):**
```json
{
  "summary": "string"
}
```

---

### GET /insights

Get key insights extracted from memories.

**Auth Required:** Yes

**Response (200):**
```json
{
  "insights": [...]
}
```

---

### GET /statistics

Get memory statistics.

**Auth Required:** Yes

**Response (200):**
```json
{
  "total": 100,
  "by_intent": {...},
  "by_speaker": {...},
  "avg_importance": 0.7,
  "recent_count": 5
}
```

---

### POST /cache/invalidate

Invalidate cache for current user.

**Auth Required:** Yes

**Response (200):**
```json
{
  "message": "Cache invalidated for user {user_id}"
}
```

---

### GET /cache/stats

Get cache statistics (admin endpoint).

**Auth Required:** Yes

**Response (200):**
```json
{
  "size": 10,
  "keys": [...]
}
```

---

## WebSocket

### WS /ws/updates

Real-time updates for dashboard.

**Query Parameters:**
- `token` (string, required) - JWT access token

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/updates?token=<access_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle updates
};
```

**Message Types:**
- `ping` - Keep-alive
- `pong` - Keep-alive response
- `memory_added` - New memory added
- `reminder_fired` - Reminder triggered

---

## Pipeline Endpoints

### POST /pipeline/extract

Extract entities and intent from text.

**Auth Required:** Yes

**Request Body:**
```json
{
  "text": "string"
}
```

**Response (200):**
```json
{
  "intent": "string",
  "entities": {...},
  "importance": 0.8,
  "memory_id": "string"
}
```

---

### POST /pipeline/validate

Check if text is a duplicate.

**Auth Required:** Yes

**Request Body:**
```json
{
  "text": "string"
}
```

**Response (200):**
```json
{
  "is_duplicate": false
}
```

---

## Reminder Endpoints

### GET /reminders/upcoming

Get upcoming reminders.

**Auth Required:** Yes

**Query Parameters:**
- `hours` (int, default: 24)

**Response (200):**
```json
{
  "reminders": [...]
}
```

---

### POST /reminders/create

Create a manual reminder.

**Auth Required:** Yes

**Request Body:**
```json
{
  "text": "string",
  "due_date": "string (ISO 8601)"
}
```

**Response (200):**
```json
{
  "reminder_id": "string",
  "message": "Reminder created"
}
```

---

## Status Endpoint

### GET /status

Health check endpoint.

**Auth Required:** No

**Response (200):**
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "chromadb": "connected",
  "ollama": "connected"
}
```

---

## Error Responses

All endpoints may return error responses:

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```
