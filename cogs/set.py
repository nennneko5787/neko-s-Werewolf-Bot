from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from objects.save import ChannelSetting, GameSetting, GuildSetting, RoleSetting
from services.save import Config


class SetCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="init", description="ゲームを開始するために初期化を行います"
    )
    @app_commands.rename(
        announceChannel="アナウンスチャンネル",
        mainVoiceChannel="メインボイスチャンネル",
        werewolfChannel="人狼専用チャンネル",
        ghostChannel="霊界チャンネル",
    )
    async def initCommand(
        self,
        interaction: discord.Interaction,
        announceChannel: discord.TextChannel | None = None,
        mainVoiceChannel: discord.VoiceChannel | None = None,
        werewolfChannel: discord.TextChannel | None = None,
        ghostChannel: discord.TextChannel | None = None,
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        announceChannel = announceChannel or await guild.create_text_channel(
            "人狼ログ",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(send_messages=False),
                guild.me: discord.PermissionOverwrite(send_messages=True),
            },
        )
        mainVoiceChannel = mainVoiceChannel or await guild.create_voice_channel(
            "人狼村", user_limit=6
        )
        werewolfChannel = werewolfChannel or await guild.create_text_channel("人狼専用")
        ghostChannel = ghostChannel or await guild.create_text_channel("幽霊専用")

        Config.config.guildSettings[guild.id] = GuildSetting(
            gameSetting=GameSetting(
                firstVictim=False,
                nightSeconds=120,
                daySeconds=180,
                voteSeconds=90,
            ),
            roleSetting=RoleSetting(all=6, werewolf=2, fortuneTeller=1),
            channelSetting=ChannelSetting(
                announceChannelId=announceChannel.id,
                mainVoiceChannelId=mainVoiceChannel.id,
                werewolfChannelId=werewolfChannel.id,
                ghostChannelId=ghostChannel.id,
            ),
        )

        Config.save()

        await interaction.followup.send(
            embed=discord.Embed(
                title="初期化完了！",
                description=f"""
                    アナウンスチャンネル: {announceChannel.mention}
                    メインボイスチャンネル: {mainVoiceChannel.mention}
                    人狼専用チャンネル: {werewolfChannel.mention}

                    firstVictim=False, nightSeconds=120, daySeconds=180, voteSeconds=90

                    ※配役は 人狼2, 占い1 の適当な配役になっているため変更することをおすすめします。
                """.strip(),
            )
        )

    @app_commands.command(name="setgame", description="ゲーム設定を変更します")
    @app_commands.rename(
        firstVictim="初日犠牲者",
        nightSeconds="夜時間",
        daySeconds="昼時間",
        voteSeconds="投票時間",
    )
    async def setGameComand(
        self,
        interaction: discord.Interaction,
        firstVictim: bool,
        nightSeconds: int,
        daySeconds: int,
        voteSeconds: int,
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        Config.config.guildSettings[guild.id].gameSetting = GameSetting(
            firstVictim=firstVictim,
            nightSeconds=nightSeconds,
            daySeconds=daySeconds,
            voteSeconds=voteSeconds,
        )

        Config.save()

        await interaction.followup.send(
            embed=discord.Embed(
                title="ゲーム設定変更完了！",
                description=f"""
                    firstVictim: {firstVictim}
                    nightSeconds: {nightSeconds}
                    daySeconds: {daySeconds}
                    voteSeconds: {voteSeconds}
                """.strip(),
            )
        )

    @app_commands.command(name="setrole", description="配役を設定します")
    @app_commands.rename(
        all="最大人数",
        werewolf="人狼の数",
        fortuneTeller="占い師の数",
    )
    async def setRoleCommand(
        self,
        interaction: discord.Interaction,
        all: app_commands.Range[int, 4],
        werewolf: app_commands.Range[int, 1],
        fortuneTeller: app_commands.Range[int, 0],
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="サーバーで実行してください", color=discord.Color.red()
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        if (werewolf + fortuneTeller) > all:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="配役がおかしいです。",
                    description="人数を確認してください。",
                    color=discord.Color.red(),
                ),
            )

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

        await voice.edit(user_limit=all)

        Config.config.guildSettings[guild.id].roleSetting = RoleSetting(
            all=all, werewolf=werewolf, fortuneTeller=fortuneTeller
        )

        Config.save()

        await interaction.followup.send(
            embed=discord.Embed(
                title="配役変更完了！",
                description=f"""
                    最大人数: {all}
                    人狼: {werewolf}
                    占い師: {fortuneTeller}
                """.strip(),
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SetCog(bot))
