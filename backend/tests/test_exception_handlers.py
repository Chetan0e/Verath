import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from app.core.exception_handlers import (
    global_exception_handler,
    verath_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from app.core.exceptions import VerathException

app = FastAPI()

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(VerathException, verath_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

class DummyItem(BaseModel):
    name: str

@app.get("/error/generic")
async def generic_error():
    raise ValueError("Something went wrong")

@app.get("/error/verath")
async def verath_error():
    class CustomVerathError(VerathException):
        pass
    raise CustomVerathError("Custom Verath Error", details={"foo": "bar"})

@app.get("/error/http")
async def http_error():
    raise HTTPException(status_code=403, detail="Forbidden action")

@app.post("/error/validation")
async def validation_error(item: DummyItem):
    return item

client = TestClient(app, raise_server_exceptions=False)

def test_global_exception_handler():
    response = client.get("/error/generic")
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "Internal Server Error"
    assert "unexpected error occurred" in data["message"]
    assert data["path"] == "/error/generic"

def test_verath_exception_handler():
    response = client.get("/error/verath")
    assert response.status_code == 500  # Default for VerathException via http_exception_from_error if not mapped
    data = response.json()
    assert data["error"] == "CustomVerathError"
    assert data["message"] == "Custom Verath Error"
    assert data["details"] == {"foo": "bar"}
    assert data["path"] == "/error/verath"

def test_http_exception_handler():
    response = client.get("/error/http")
    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "AuthorizationError"
    assert data["message"] == "Forbidden action"
    assert data["path"] == "/error/http"

def test_validation_exception_handler():
    response = client.post("/error/validation", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "ValidationError"
    assert data["path"] == "/error/validation"
    assert "errors" in data["details"]
