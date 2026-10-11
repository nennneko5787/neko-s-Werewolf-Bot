import json
import os
from pathlib import Path

from objects.game import Game
from objects.save import SaveJson


class Config:
    config: SaveJson
    games: dict[int, Game]

    @classmethod
    def load(cls):
        cls.games = {}

        if not os.path.exists("config.json"):
            Path("config.json").write_text(
                SaveJson().model_dump_json(indent=2),
                encoding="utf-8",
            )

        cls.config = SaveJson.model_validate(
            json.loads(Path("config.json").read_text(encoding="utf-8"))
        )

    @classmethod
    def save(cls) -> None:
        Path("config.json").write_text(
            cls.config.model_dump_json(indent=2),
            encoding="utf-8",
        )
