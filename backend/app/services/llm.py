from app.services.groq_service import generate_response


async def ask_llm(query, context, user_id):
    """
    Backward-compatible LLM wrapper expected by legacy tests/routes.
    """

    prompt = f"""
Context:
{context}

Question:
{query}
"""

    response = await generate_response(prompt)

    return response, [], 0.85