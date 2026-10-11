import enum


class DayScene(enum.Enum):
    NIGHT = 0
    DAY = 1
    VOTE = 2


class WinType(enum.StrEnum):
    WEREWOLF = "WEREWOLF"
    VILLAGER = "VILLAGER"
