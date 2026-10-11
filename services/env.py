import os

import dotenv

__all__ = ("get",)

dotenv.load_dotenv()


def get(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise KeyError(f"Env '{key}'")
    return value
