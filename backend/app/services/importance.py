from app.services.llm import ask_llm
import re

def score_importance(text: str) -> float:
    """Score importance of text from 0 to 1 using LLM."""
    prompt = f"""
Rate the importance of this text from 0.0 to 1.0:

"{text}"

Consider:
- Deadlines, appointments, time-sensitive information
- Instructions, action items, commitments
- Emotional significance, personal revelations
- Learning moments, key insights
- Contact information, important details

Return only a number between 0.0 and 1.0.
"""
    
    try:
        response = ask_llm(prompt)
        # Extract numeric value from response
        numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
        if numbers:
            score = float(numbers[0])
            return min(max(score, 0.0), 1.0)  # Ensure within bounds
        return 0.5  # Default if no number found
    except Exception as e:
        print(f"Error scoring importance: {e}")
        return 0.5  # Default middle importance

def categorize_importance(score: float) -> str:
    """Categorize importance score into levels."""
    if score >= 0.8:
        return "critical"
    elif score >= 0.6:
        return "high"
    elif score >= 0.4:
        return "medium"
    elif score >= 0.2:
        return "low"
    else:
        return "minimal"
