import asyncio
import random
from collections import Counter
from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from objects.enum import DayScene, WinType
from objects.game import Day, Game, Roles
from objects.save import GuildSetting
from services.save import Config


class WolfCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.targetContextMenu = app_commands.ContextMenu(
            name="ターゲットを指定（人狼）",
            callback=self.choiceTargetContextMenu,
        )
        self.bot.tree.add_command(self.targetContextMenu)

        self.voteTargetContextMenu = app_commands.ContextMenu(
            name="投票先を指定（人狼）",
            callback=self.choiceVoteTargetContextMenu,
        )
        self.bot.tree.add_command(self.voteTargetContextMenu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            "ターゲットを指定（人狼）",
            type=discord.AppCommandType.user,
        )
        self.bot.tree.remove_command(
            "投票先を指定（人狼）",
            type=discord.AppCommandType.user,
        )

    @commands.Cog.listener("on_voice_state_update")
    async def onVoiceStateUpdate(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        voiceId = Config.config.guildSettings[
            member.guild.id
        ].channelSetting.mainVoiceChannelId
        game = Config.games.get(member.guild.id)
        if not game:
            return

        if after.channel is not None and after.channel.id == voiceId:
            if member in game.ghosts or game.day.scene == DayScene.NIGHT:
                await member.edit(mute=True, deafen=True)
            else:
                await member.edit(mute=False, deafen=False)

    @app_commands.command(name="game", description="ゲームを開始します")
    async def gameCommand(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        # アナウンスチャンネル
        announceChannel = cast(
            discord.TextChannel | None,
            guild.get_channel(
                Config.config.guildSettings[guild.id].channelSetting.announceChannelId
            ),
        )
        if not announceChannel:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="アナウンスチャンネルが存在しません。",
                    description="再初期化をおすすめします。",
                    color=discord.Color.red(),
                ),
            )

        # メインボイスチャンネル
        voice = cast(
            discord.VoiceChannel | None,
            guild.get_channel(
                Config.config.guildSettings[guild.id].channelSetting.mainVoiceChannelId
            ),
        )
        if not voice:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="メインボイスチャンネルが存在しません。",
                    description="再初期化をおすすめします。",
                    color=discord.Color.red(),
                ),
            )

        # 人狼チャンネル
        werewolfChannel = cast(
            discord.TextChannel | None,
            guild.get_channel(
                Config.config.guildSettings[guild.id].channelSetting.werewolfChannelId
            ),
        )
        if not werewolfChannel:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="人狼専用チャンネルが存在しません。",
                    description="再初期化をおすすめします。",
                    color=discord.Color.red(),
                ),
            )

        # 霊界チャンネル
        ghostChannel = cast(
            discord.TextChannel | None,
            guild.get_channel(
                Config.config.guildSettings[guild.id].channelSetting.ghostChannelId
            ),
        )
        if not ghostChannel:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="霊界チャンネルが存在しません。",
                    description="再初期化をおすすめします。",
                    color=discord.Color.red(),
                ),
            )

        # メンバーに権限を与える
        members = voice.members.copy()
        for member in members.copy():
            await voice.set_permissions(member, speak=True, send_messages=True)

        # 人狼抽選からの抽選から外す
        villagers = members.copy()
        werewolfs = random.choices(
            villagers, k=Config.config.guildSettings[guild.id].roleSetting.werewolf
        )
        for member in werewolfs:
            villagers.remove(member)
            await werewolfChannel.set_permissions(
                member, read_messages=True, send_messages=True
            )
            await voice.set_permissions(member, speak=True, send_messages=True)
            await member.send("あなたは 人狼 です")

        # 占い師抽選からの抽選から外す
        tellers = random.choices(
            villagers, k=Config.config.guildSettings[guild.id].roleSetting.fortuneTeller
        )
        for member in tellers:
            villagers.remove(member)
            await voice.set_permissions(member, speak=True, send_messages=True)
            await member.send("あなたは 占い師 です")

        for member in villagers:
            await voice.set_permissions(member, speak=True, send_messages=True)
            await member.send("あなたは 村人 です")

        # チャンネルの権限を設定する
        await voice.set_permissions(
            guild.default_role, speak=False, send_messages=False
        )
        await werewolfChannel.set_permissions(guild.default_role, read_messages=False)
        await ghostChannel.set_permissions(guild.default_role, read_messages=False)

        Config.games[guild.id] = Game(
            guildId=guild.id,
            roles=Roles(
                werewolfs=werewolfs, fortuneTellers=tellers, villagers=villagers
            ),
            members=members,
            day=Day(days=0, scene=DayScene.NIGHT),
            announceChannel=announceChannel,
            mainVoiceChannel=voice,
            werewolfChannel=werewolfChannel,
            ghostChannel=ghostChannel,
        )

        await self.night(
            Config.games[guild.id],
            Config.config.guildSettings[guild.id],
        )

    async def choiceTargetContextMenu(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="内部エラーです。",
                    description="報告をお願いします。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        game = Config.games.get(member.guild.id)
        if not game:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="現在ゲームは開催されていません。", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if game.day.scene != DayScene.NIGHT:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="夜ではありません。", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if interaction.user.id == member.id:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="自分自身にアクションを起こすことはできません。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        if member in game.ghosts:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="既に死んでいるメンバーにアクションを起こすことはできません。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        if interaction.user in game.roles.werewolfs:
            if member in game.roles.werewolfs:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title="身内噛みはできません。", color=discord.Color.red()
                    ),
                    ephemeral=True,
                )

            game.werewolfTarget = member
        elif interaction.user in game.roles.fortuneTellers:
            game.actionTargets[interaction.user] = member

        await interaction.followup.send(
            embed=discord.Embed(
                title=f"ターゲットを {member.mention} に指定しました。",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    async def choiceVoteTargetContextMenu(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="内部エラーです。",
                    description="報告をお願いします。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        game = Config.games.get(member.guild.id)
        if not game:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="現在ゲームは開催されていません。", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if game.day.scene != DayScene.VOTE:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="投票時間ではありません。", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        if member in game.ghosts:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="既に死んでいるメンバーにアクションを起こすことはできません。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

        game.voteTargets[interaction.user] = member

        await interaction.followup.send(
            embed=discord.Embed(
                title=f"投票先を {member.mention} に指定しました。",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    async def die(
        self,
        member: discord.Member,
        game: Game,
    ):
        game.ghosts.append(member)
        await game.ghostChannel.set_permissions(member, read_messages=True)
        await game.announceChannel.send(f"{member.mention} が死亡しました")
        await game.ghostChannel.send(
            f"あなたは死亡しました。このチャンネルで会話することができます。\n{member.mention}"
        )

    async def gameEndCheck(
        self,
        game: Game,
        guildSetting: GuildSetting,
    ) -> bool:
        winType: WinType | None = None

        werewolfDeadCount = 0
        for member in game.roles.werewolfs:
            if member in game.ghosts:
                werewolfDeadCount += 1

        if len(game.roles.werewolfs) - werewolfDeadCount <= 0:
            winType = WinType.VILLAGER
        elif len(
            set(game.roles.fortuneTellers + game.roles.villagers) ^ set(game.ghosts)
        ) <= len(game.roles.werewolfs):
            winType = WinType.WEREWOLF

        if winType is None:
            return False

        match winType:
            case WinType.VILLAGER:
                await game.announceChannel.send(
                    embed=discord.Embed(
                        title="人狼が全滅",
                        description="人狼が全滅したため、村人の勝利！！",
                        color=discord.Color.green(),
                    )
                )
            case WinType.WEREWOLF:
                await game.announceChannel.send(
                    embed=discord.Embed(
                        title="村人が全滅",
                        description="村人が全滅したため、人狼の勝利！！",
                        color=discord.Color.red(),
                    )
                )

        await game.announceChannel.send(
            "## 役職\n"
            + "\n".join(
                [
                    f"{member.mention}: {game.getMemberRole(member)}"
                    for member in game.members
                ]
            )
        )

        await game.announceChannel.send("ゲーム終了")

        del Config.games[game.guildId]
        return True

    async def night(
        self,
        game: Game,
        guildSetting: GuildSetting,
    ):
        for member in game.members:
            if member.voice is None:
                await game.announceChannel.send(
                    f"{member.mention} ボイスチャンネルに接続してください。"
                )
                continue
            if member in game.ghosts:
                continue
            if member in game.roles.werewolfs:
                await game.werewolfChannel.set_permissions(
                    member, read_messages=True, send_messages=True
                )

            await member.edit(mute=True, deafen=True)

        game.day.scene = DayScene.NIGHT
        game.day.days += 1

        await game.announceChannel.send(
            embed=discord.Embed(
                title=f"{game.day.days}日目夜",
                description="人狼に気をつけてください...",
                color=discord.Color.dark_blue(),
            )
        )

        nightSeconds = guildSetting.gameSetting.nightSeconds
        for i in range(nightSeconds):
            if (nightSeconds - i) % 10 == 0:
                await game.announceChannel.send(f"夜時間残り{nightSeconds - i}秒")

            await asyncio.sleep(1)

        if guildSetting.gameSetting.firstVictim and game.day.days == 1:
            deadPlayerName = random.choice(["初日犠牲者", "初日犠牲者ちゃん", "村人A"])
            await game.announceChannel.send(f"{deadPlayerName} が死亡しました")
        else:
            if game.werewolfTarget is None:
                for member in game.roles.werewolfs:
                    await self.die(
                        member,
                        game,
                    )
            else:
                await self.die(
                    game.werewolfTarget,
                    game,
                )
            game.werewolfTarget = None

        for member in game.roles.fortuneTellers:
            target = game.actionTargets[member]
            if target is None:
                await self.die(
                    member,
                    game,
                )
            else:
                await member.send(f"{target} は {game.getMemberRole(member)} です")
        game.actionTargets.clear()

        if not await self.gameEndCheck(game, guildSetting):
            await self.day(game, guildSetting)

    async def day(
        self,
        game: Game,
        guildSetting: GuildSetting,
    ):
        for member in game.members:
            if member.voice is None:
                print(f"{member.display_name} isn't joined the voice channel. Skipping")
                continue
            if member in game.ghosts:
                continue
            if member in game.roles.werewolfs:
                await game.werewolfChannel.set_permissions(
                    member, read_messages=True, send_messages=False
                )

            await member.edit(mute=False, deafen=False)

        game.day.scene = DayScene.DAY

        await game.announceChannel.send(
            embed=discord.Embed(
                title=f"{game.day.days}日目昼",
                description="議論を開始してください...",
                color=discord.Color.yellow(),
            )
        )

        daySeconds = guildSetting.gameSetting.daySeconds
        for i in range(daySeconds):
            if (daySeconds - i) % 10 == 0:
                await game.announceChannel.send(f"昼時間残り{daySeconds - i}秒")

            await asyncio.sleep(1)

        if not await self.gameEndCheck(game, guildSetting):
            await self.vote(game, guildSetting)

    async def vote(
        self,
        game: Game,
        guildSetting: GuildSetting,
    ):
        game.day.scene = DayScene.VOTE

        await game.announceChannel.send(
            embed=discord.Embed(
                title=f"{game.day.days}日目投票時間",
                description="誰を処刑するか、投票で決めましょう...",
                color=discord.Color.orange(),
            )
        )

        voteSeconds = guildSetting.gameSetting.voteSeconds
        for i in range(voteSeconds):
            if (voteSeconds - i) % 10 == 0:
                await game.announceChannel.send(f"投票時間残り{voteSeconds - i}秒")

            await asyncio.sleep(1)

        for member in game.members:
            if member not in game.voteTargets:
                game.voteTargets[member] = random.choice(
                    list(set(game.members) ^ set(game.ghosts))
                )
                await game.announceChannel.send(
                    f"{member.mention} は時間内に投票しなかったためランダム投票となります"
                )

        counter = Counter(game.voteTargets.values())
        punishTarget = counter.most_common(1)[0][0]
        game.voteTargets.clear()

        await game.announceChannel.send(
            "### 投票結果"
            + "\n".join(
                [
                    f"{member.mention} -> {target.mention}"
                    for member, target in game.voteTargets.items()
                ]
            )
        )

        await game.announceChannel.send(
            f"投票の結果、 {punishTarget.mention} が処刑されます。"
        )
        await self.die(
            punishTarget,
            game,
        )

        if not await self.gameEndCheck(game, guildSetting):
            await self.night(game, guildSetting)


async def setup(bot: commands.Bot):
    await bot.add_cog(WolfCog(bot))
