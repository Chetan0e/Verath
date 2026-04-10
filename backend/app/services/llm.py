import requests

from app.config import MODEL_NAME, OLLAMA_URL


def ask_llm(prompt: str) -> str:
    """Ask LLM a question using Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=180,
        )
        response.raise_for_status()
        payload = response.json()
        if "response" not in payload:
            raise ValueError("response not returned by Ollama")
        return payload["response"]
    except Exception as e:
        print(f"Error asking LLM: {e}")
        return f"Error: Could not get response from LLM. {str(e)}"

def ask_llm_with_context(prompt: str, context: str = "") -> str:
    """Ask LLM with additional context."""
    full_prompt = f"""
Context:
{context}

Question:
{prompt}

Answer clearly and concisely:
"""
    return ask_llm(full_prompt)
