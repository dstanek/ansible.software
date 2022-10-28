from pathlib import Path

class SoftwareException(Exception):
    def __init__(self, msg, **context):
        super().__init__(msg)
        self.context = _sanitize(context)


def _sanitize(data: dict) -> dict:
    for key, value in data.items():
        if isinstance(value, Path):
            data[key] = str(value)
        elif isinstance(value, dict):
            data[key] = _sanitize(value)
    return data
