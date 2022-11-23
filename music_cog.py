import discord
from discord_components import Select, SelectOption, Button
from discord.ext import commands
import asyncio
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import json
import os
from youtube_dl import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_playing = {}
        self.is_paused = {}
        self.musicQueue = {}
        self.queueIndex = {}

        self.YTDL_OPTIONS = {'format': 'bestaudio', 'nonplaylist': 'True'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

        self.embedBlue = 0x2c76dd
        self.embedRed = 0xdf1141
        self.embedGreen = 0x0eaa51

        self.vc = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            id = int(guild.id)
            self.musicQueue[id] = []
            self.queueIndex[id] = 0
            self.vc[id] = None
            self.is_paused[id] = self.is_playing[id] = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        id = int(member.guild.id)
        if member.id != self.bot.user.id and before.channel != None and after.channel != before.channel:
            remainingChannelMembers = before.channel.members
            if len(remainingChannelMembers) == 1 and remainingChannelMembers[0].id == self.bot.user.id and self.vc[id].is_connected():
                self.is_playing[id] = self.is_paused[id] = False
                self.musicQueue[id] = []
                self.queueIndex[id] = 0
                await self.vc[id].disconnect()

    def now_playing_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title="Đang phát",
            description=f'[{title}]({link})',
            colour=self.embedBlue,
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f'Bài hát được thêm bởi: {str(author)}', icon_url=avatar)
        return embed

    def added_song_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title="Bài hát đã được thêm vào hàng đợi!",
            description=f'[{title}]({link})',
            colour=self.embedRed,
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f'Bài hát được thêm bởi: {str(author)}', icon_url=avatar)
        return embed

    def removed_song_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(
            title="Bài hát đã bị xóa khỏi hàng đợi!",
            description=f'[{title}]({link})',
            colour=self.embedRed,
        )
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(
            text=f'Bài hát được thêm bởi: {str(author)}', icon_url=avatar)
        return embed

    async def join_VC(self, ctx, channel):
        id = int(ctx.guild.id)
        if self.vc[id] == None or not self.vc[id].is_connected():
            self.vc[id] = await channel.connect()

            if self.vc[id] == None:
                await ctx.send("Không thể kết nối với voice channel.")
                return
        else:
            await self.vc[id].move_to(channel)

    def get_YT_title(self, videoID):
        params = {"format": "json",
                  "url": "https://www.youtube.com/watch?v=%s" % videoID}
        url = "https://www.youtube.com/oembed"
        queryString = parse.urlencode(params)
        url = url + "?" + queryString
        with request.urlopen(url) as response:
            responseText = response.read()
            data = json.loads(responseText.decode())
            return data['title']

    def search_YT(self, search):
        queryString = parse.urlencode({'search_query': search})
        htmContent = request.urlopen(
            'http://www.youtube.com/results?' + queryString)
        searchResults = re.findall(
            '/watch\?v=(.{11})', htmContent.read().decode())
        return searchResults[0:10]

    def extract_YT(self, url):
        with YoutubeDL(self.YTDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except:
                return False
        return {
            'link': 'https://www.youtube.com/watch?v=' + url,
            'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
            'source': info['formats'][0]['url'],
            'title': info['title']
        }

    def play_next(self, ctx):
        id = int(ctx.guild.id)
        if not self.is_playing[id]:
            return
        if self.queueIndex[id] + 1 < len(self.musicQueue[id]):
            self.is_playing[id] = True
            self.queueIndex[id] += 1

            song = self.musicQueue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            coro = ctx.send(embed=message)
            fut = run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass

            self.vc[id].play(discord.FFmpegPCMAudio(
                song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            self.queueIndex[id] += 1
            self.is_playing[id] = False

    async def play_music(self, ctx):
        id = int(ctx.guild.id)
        if self.queueIndex[id] < len(self.musicQueue[id]):
            self.is_playing[id] = True
            self.is_paused[id] = False

            await self.join_VC(ctx, self.musicQueue[id][self.queueIndex[id]][1])

            song = self.musicQueue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            await ctx.send(embed=message)

            self.vc[id].play(discord.FFmpegPCMAudio(
                song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            await ctx.send("Không có bài hát nào trong hàng đợi để phát!")
            self.queueIndex[id] += 1
            self.is_playing[id] = False

    @ commands.command(
        name="play",
        aliases=["pl"],
        help="Phát (hoặc tiếp tục) âm thanh của một video YouTube cụ thể"
    )
    async def play(self, ctx, *args):
        search = " ".join(args)
        id = int(ctx.guild.id)
        try:
            userChannel = ctx.author.voice.channel
        except:
            await ctx.send("Bạn phải kết nối với voice channel!")
            return
        if not args:
            if len(self.musicQueue[id]) == 0:
                await ctx.send("Không có bài hát nào được phát trong hàng đợi!")
                return
            elif not self.is_playing[id]:
                if self.musicQueue[id] == None or self.vc[id] == None:
                    await self.play_music(ctx)
                else:
                    self.is_paused[id] = False
                    self.is_playing[id] = True
                    self.vc[id].resume()
            else:
                return
        else:
            song = self.extract_YT(self.search_YT(search)[0])
            if type(song) == type(True):
                await ctx.send("Không thể tải xuống bài hát. Định dạng không chính xác, hãy thử một số từ khóa khác.")
            else:
                self.musicQueue[id].append([song, userChannel])

                if not self.is_playing[id]:
                    await self.play_music(ctx)
                else:
                    message = self.added_song_embed(ctx, song)
                    await ctx.send(embed=message)

    @ commands.command(
        name="add",
        aliases=["a"],
        help="Thêm kết quả tìm kiếm đầu tiên vào hàng đợi"
    )
    async def add(self, ctx, *args):
        search = " ".join(args)
        try:
            userChannel = ctx.author.voice.channel
        except:
            await ctx.send("Bạn phải kết nối với voice channel!")
            return
        if not args:
            await ctx.send("Bạn cần chỉ định một bài hát sẽ được thêm vào!")
        else:
            song = self.extract_YT(self.search_YT(search)[0])
            if type(song) == type(False):
                await ctx.send("Không thể tải xuống bài hát. Định dạng không chính xác, hãy thử từ khóa khác!")
                return
            else:
                self.musicQueue[ctx.guild.id].append([song, userChannel])
                message = self.added_song_embed(ctx, song)
                await ctx.send(embed=message)

    @ commands.command(
        name="remove",
        aliases=["rm"],
        help="Xóa bài hát cuối cùng trong hàng đợi"
    )
    async def remove(self, ctx):
        id = int(ctx.guild.id)
        if self.musicQueue[id] != []:
            song = self.musicQueue[id][-1][0]
            removeSongEmbed = self.removed_song_embed(ctx, song)
            await ctx.send(embed=removeSongEmbed)
        else:
            await ctx.send("Không có bài hát nào cần xóa trong hàng đợi!")
        self.musicQueue[id] = self.musicQueue[id][:-1]
        if self.musicQueue[id] == []:
            if self.vc[id] != None and self.is_playing[id]:
                self.is_playing[id] = self.is_paused[id] = False
                await self.vc[id].disconnect()
                self.vc[id] = None
            self.queueIndex[id] = 0
        elif self.queueIndex[id] == len(self.musicQueue[id]) and self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] -= 1
            await self.play_music(ctx)

    @ commands.command(
        name="search",
        aliases=["find", "sr"],
        help="Cung cấp danh sách kết quả tìm kiếm trên YouTube"
    )
    async def search(self, ctx, *args):
        search = " ".join(args)
        songNames = []
        selectionOptions = []
        embedText = ""

        if not args:
            await ctx.send("Bạn phải chỉ định cụm từ tìm kiếm để sử dụng lệnh này")
            return
        try:
            userChannel = ctx. author.voice.channel
        except:
            await ctx.send("Bạn cần phải kết nối với voice channel.")
            return

        await ctx.send("Đang lấy kết quả tìm kiếm . . .")

        songTokens = self.search_YT(search)

        for i, token in enumerate(songTokens):
            url = 'https://www.youtube.com/watch?v=' + token
            name = self.get_YT_title(token)
            songNames.append(name)
            embedText += f"{i+1} - [{name}]({url})\n"

        for i, title in enumerate(songNames):
            selectionOptions.append(SelectOption(
                label=f"{i+1} - {title[:95]}", value=i))

        searchResults = discord.Embed(
            title="Kết quả tìm kiếm",
            description=embedText,
            colour=self.embedRed
        )
        selectionComponents = [
            Select(
                placeholder="Chọn một tùy chọn",
                options=selectionOptions
            ),
            Button(
                label="Cancel",
                custom_id="Cancel",
                style=4
            )
        ]
        message = await ctx.send(embed=searchResults, components=selectionComponents)
        try:
            tasks = [
                asyncio.create_task(self.bot.wait_for(
                    "button_click",
                    timeout=60.0,
                    check=None
                ), name="button"),
                asyncio.create_task(self.bot.wait_for(
                    "select_option",
                    timeout=60.0,
                    check=None
                ), name="select")
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finished = list(done)[0]

            for task in pending:
                try:
                    task.cancel()
                except asyncio.CancelledError:
                    pass

            if finished == None:
                searchResults.title = "Tìm kiếm không thành công"
                searchResults.description = ""
                await message.delete()
                await ctx.send(embed=searchResults)
                return

            action = finished.get_name()

            if action == "button":
                searchResults.title = "Tìm kiếm không thành công"
                searchResults.description = ""
                await message.delete()
                await ctx.send(embed=searchResults)
            elif action == "select":
                result = finished.result()
                chosenIndex = int(result.values[0])
                songRef = self.extract_YT(songTokens[chosenIndex])
                if type(songRef) == type(True):
                    await ctx.send("Không thể tải xuống bài hát. Định dạng không chính xác, hãy thử từ khóa khác.")
                    return
                embedReponse = discord.Embed(
                    title=f"Option #{chosenIndex + 1} Selected",
                    description=f"[{songRef['title']}]({songRef['link']}) được thêm vào hàng đợi!",
                    colour=self.embedRed
                )
                embedReponse.set_thumbnail(url=songRef['thumbnail'])
                await message.delete()
                await ctx.send(embed=embedReponse)
                self.musicQueue[ctx.guild.id].append([songRef, userChannel])
        except:
            searchResults.title = "Tìm kiếm không thành công"
            searchResults.description = ""
            await message.delete()
            await ctx.send(embed=searchResults)

    @ commands.command(
        name="pause",
        aliases=["stop", "pa"],
        help="Tạm dừng bài hát hiện tại đang được phát"
    )
    async def pause(self, ctx):
        id = int(ctx.guild.id)
        if not self.vc[id]:
            await ctx.send("Hiện tại không có âm thanh nào để tạm dừng.")
        elif self.is_playing[id]:
            await ctx.send("Đã tạm dừng âm thanh!")
            self.is_playing[id] = False
            self.is_paused[id] = True
            self.vc[id].pause()

    @ commands.command(
        name="resume",
        aliases=["re"],
        help="Tiếp tục một bài hát bị tạm dừng"
    )
    async def resume(self, ctx):
        id = int(ctx.guild.id)
        if not self.vc[id]:
            await ctx.send("Không có âm thanh nào được phát vào lúc này.")
        elif self.is_paused[id]:
            await ctx.send("Âm thanh hiện đang phát!")
            self.is_playing[id] = True
            self.is_paused[id] = False
            self.vc[id].resume()

    @ commands.command(
        name="previous",
        aliases=["pre", "pr"],
        help="Phát bài hát trước đó trong hàng đợi"
    )
    async def previous(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] == None:
            await ctx.send("Bạn cần phải ở trong một VC để sử dụng lệnh này.")
        elif self.queueIndex[id] <= 0:
            await ctx.send("Không có bài hát trước đó trong hàng đợi. Phát lại bài hát hiện tại.")
            self.vc[id].pause()
            await self.play_music(ctx)
        elif self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] -= 1
            await self.play_music(ctx)

    @ commands.command(
        name="skip",
        aliases=["sk"],
        help="Bỏ qua bài hát tiếp theo trong hàng đợi."
    )
    async def skip(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] == None:
            await ctx.send("Bạn cần phải ở trong một VC để sử dụng lệnh này.")
        elif self.queueIndex[id] >= len(self.musicQueue[id]) - 1:
            await ctx.send("Không có bài hát tiếp theo trong hàng đợi. Phát lại bài hát hiện tại.")
            self.vc[id].pause()
            await self.play_music(ctx)
        elif self.vc[id] != None and self.vc[id]:
            self.vc[id].pause()
            self.queueIndex[id] += 1
            await self.play_music(ctx)

    @ commands.command(
        name="queue",
        aliases=["list", "q"],
        help="Liệt kê một vài bài hát tiếp theo trong hàng đợi."
    )
    async def queue(self, ctx):
        id = int(ctx.guild.id)
        returnValue = ""
        if self.musicQueue[id] == []:
            await ctx.send("Không có bài hát nào trong hàng đợi.")
            return

        for i in range(self.queueIndex[id], len(self.musicQueue[id])):
            upNextSongs = len(self.musicQueue[id]) - self.queueIndex[id]
            if i > 5 + upNextSongs:
                break
            returnIndex = i - self.queueIndex[id]
            if returnIndex == 0:
                returnIndex = "Playing"
            elif returnIndex == 1:
                returnIndex = "Next"
            returnValue += f"{returnIndex} - [{self.musicQueue[id][i][0]['title']}]({self.musicQueue[id][i][0]['link']})\n"

            if returnValue == "":
                await ctx.send("Không có bài hát nào trong hàng đợi.")
                return

        queue = discord.Embed(
            title="Hàng đợi hiện tại",
            description=returnValue,
            colour=self.embedGreen
        )
        await ctx.send(embed=queue)

    @ commands.command(
        name="clear",
        aliases=["cl"],
        help="Xóa tất cả các bài hát khỏi hàng đợi"
    )
    async def clear(self, ctx):
        id = int(ctx.guild.id)
        if self.vc[id] != None and self.is_playing[id]:
            self.is_playing = self.is_paused = False
            self.vc[id].stop()
        if self.musicQueue[id] != []:
            await ctx.send("Hàng đợi âm nhạc đã bị xóa.")
            self.musicQueue[id] = []
        self.queueIndex = 0

    @ commands.command(
        name="join",
        aliases=["j"],
        help="Kết nối iamBot với voice channel"
    )
    async def join(self, ctx):
        if ctx.author.voice:
            userChannel = ctx.author.voice.channel
            await self.join_VC(ctx, userChannel)
            await ctx.send(f'iamBot đã tham gia {userChannel}')
        else:
            await ctx.send("Bạn cần kết nối với voice channel.")

    @ commands.command(
        name="leave",
        aliases=["l"],
        help="Xóa iamBot khỏi voice channel và xóa hàng đợi"
    )
    async def leave(self, ctx):
        id = int(ctx.guild.id)
        self.is_playing[id] = self.is_paused[id] = False
        self.musicQueue[id] = []
        self.queueIndex[id] = 0
        if self.vc[id] != None:
            await ctx.send("iamBot đã rời khỏi cuộc trò chuyện")
            await self.vc[id].disconnect()
            self.vc[id] = None