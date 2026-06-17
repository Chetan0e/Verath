# Retrieval Evaluation Benchmark

## Overview

This benchmark evaluates retrieval quality using deterministic synthetic memory datasets.

## Metrics

- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)
- Source-hit Accuracy

## Running

```bash
PYTHONPATH=. python -m app.evaluation.rag_benchmark
