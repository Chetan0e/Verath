"""
Benchmark: combined LLM call (ExtractionPipeline._llm_refine) vs two sequential calls.

Config:
  Model:       llama-3.3-70b-versatile
  Temperature: 0.7
  Max tokens:  1000
  Runs:        5 per sample text

Note: measures raw Groq API latency only. Does not capture parsing overhead,
fallback logic, or full service pipeline. Primary claim is API calls per
recording 2 → 1; latency reduction is directional, not a production guarantee.
"""
import asyncio
import json
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.groq_service import generate_response

SAMPLES = [
    "Let's meet the product team tomorrow at 3pm to review the launch checklist.",
    "I need to submit the Q3 financial report by Friday end of day.",
    "Remember to call Sarah about the budget approval for the new project.",
    "The deadline for the design handoff has been moved to next Monday.",
    "Grocery list: milk, eggs, bread, and coffee for the office.",
]


async def time_sequential(text: str) -> float:
    """Simulate the old pipeline: two separate calls."""
    t = time.perf_counter()
    await generate_response(
        f'Summarize this text into one sentence: "{text}"'
    )
    await generate_response(
        f'Rate the importance of this text from 0.0 to 1.0. Return only the number: "{text}"'
    )
    return (time.perf_counter() - t) * 1000


async def time_combined(text: str) -> float:
    """New pipeline: single _llm_refine call."""
    t = time.perf_counter()
    await generate_response(
        f'Analyze this text and return ONLY JSON with intent, summary, importance, entities: "{text}"',
        response_format={"type": "json_object"},
    )
    return (time.perf_counter() - t) * 1000


async def main():
    print(f"{'Sample':<50} {'Sequential (ms)':>16} {'Combined (ms)':>14} {'Saved':>8}")
    print("-" * 92)
    total_seq, total_comb = 0.0, 0.0
    for sample in SAMPLES:
        seq_ms = await time_sequential(sample)
        comb_ms = await time_combined(sample)
        total_seq += seq_ms
        total_comb += comb_ms
        label = sample[:48] + ".." if len(sample) > 48 else sample
        print(f"{label:<50} {seq_ms:>14.0f}ms {comb_ms:>12.0f}ms {(1 - comb_ms/seq_ms)*100:>7.0f}%")
    print("-" * 92)
    avg_seq, avg_comb = total_seq / len(SAMPLES), total_comb / len(SAMPLES)
    print(f"{'Average':<50} {avg_seq:>14.0f}ms {avg_comb:>12.0f}ms {(1 - avg_comb/avg_seq)*100:>7.0f}%")


if __name__ == "__main__":
    asyncio.run(main())