import discord
from discord.ext import commands


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embedOrange = 0xeab148

    @commands.Cog.listener()
    async def on_ready(self):
        sendToChannels = []
        for guild in self.bot.guilds:
            channel = guild.text_channels[0]
            sendToChannels.append(channel)
        helloEmbed = discord.Embed(
            title="Hello There!",
            description="""
            Hello, I'm iamBot! Bạn có thể gõ 1 vài lệnh lệnh sau khi gõ tiền tố  **`'!'`** để kích hoạt chúng. Sử dụng **`!help`** để xem một số tùy chọn lệnh.""",
            colour=self.embedOrange
        )
        for channel in sendToChannels:
            await channel.send(embed=helloEmbed)

    @commands.command(
        name="help",
        aliases=["h"],
        help="Cung cấp mô tả của tất cả các lệnh được chỉ định"
    )
    async def help(self, ctx):
        helpCog = self.bot.get_cog('help_cog')
        musicCog = self.bot.get_cog('music_cog')
        commands = helpCog.get_commands() + musicCog.get_commands()
        commandDescription = ""

        for c in commands:
            commandDescription += f"**`!{c.name}`** {c.help}\n"
        commandsEmbed = discord.Embed(
            title="Commands List",
            description=commandDescription,
            colour=self.embedOrange
        )

        await ctx.send(embed=commandsEmbed)