from datetime import datetime


def format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat()
