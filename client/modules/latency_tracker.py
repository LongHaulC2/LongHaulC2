latency_status = {"value": 0, "color": "#10b981"}


def update_latency_metrics(ms: float, error: bool = False):
    """Updates the global latency state for the UI."""
    latency_status["value"] = int(ms)
    if error:
        latency_status["color"] = "#ef4444"
    elif ms < 150:
        latency_status["color"] = "#10b981"
    elif ms < 500:
        latency_status["color"] = "#f59e0b"
    else:
        latency_status["color"] = "#ef4444"
