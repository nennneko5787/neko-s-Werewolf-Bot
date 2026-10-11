from pydantic import BaseModel, Field


class RoleSetting(BaseModel):
    all: int = 7
    werewolf: int = 2
    fortuneTeller: int = 1


class ChannelSetting(BaseModel):
    announceChannelId: int
    mainVoiceChannelId: int
    werewolfChannelId: int
    ghostChannelId: int


class GameSetting(BaseModel):
    firstVictim: bool = False
    nightSeconds: int = 120
    daySeconds: int = 180
    voteSeconds: int = 90


class GuildSetting(BaseModel):
    roleSetting: RoleSetting
    channelSetting: ChannelSetting
    gameSetting: GameSetting


class SaveJson(BaseModel):
    guildSettings: dict[int, GuildSetting] = Field({})
