from dataclasses import dataclass, field

import discord

from objects.enum import DayScene


@dataclass(kw_only=True, slots=True, weakref_slot=True)
class Roles:
    werewolfs: list[discord.Member]
    villagers: list[discord.Member]
    fortuneTellers: list[discord.Member]


@dataclass(kw_only=True, slots=True, weakref_slot=True)
class Day:
    days: int
    scene: DayScene


@dataclass(kw_only=True, slots=True, weakref_slot=True)
class Game:
    guildId: int
    roles: Roles
    members: list[discord.Member]
    ghosts: list[discord.Member] = field(default_factory=list)
    day: Day
    voteTargets: dict[discord.Member, discord.Member] = field(default_factory=dict)
    werewolfTarget: discord.Member | None = field(default=None)
    actionTargets: dict[discord.Member, discord.Member | None] = field(
        default_factory=dict
    )

    announceChannel: discord.TextChannel
    mainVoiceChannel: discord.VoiceChannel
    werewolfChannel: discord.TextChannel
    ghostChannel: discord.TextChannel

    def getMemberRole(self, member: discord.Member) -> str:
        if member in self.roles.werewolfs:
            return "人狼"
        elif member in self.roles.fortuneTellers:
            return "占い師"
        else:
            return "村人"
