import json

def log_event(event):
    """
    Logs the given event for debugging purposes.
    """
    print("Event:", json.dumps(event, indent=2))
