import discord
from discord.ext import commands
import asyncio
import yt_dlp
import json
import os
from async_timeout import timeout
from collections import deque
from Token import token

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
 
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# 설정 파일 경로
CONFIG_FILE = 'config.json'

# 허용된 채널 ID를 저장할 변수 초기화
allowed_channel_id = None

# yt-dlp 인스턴스 생성
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# 설정 파일 로드 및 저장 함수
def load_config():
    global allowed_channel_id
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            allowed_channel_id = data.get('allowed_channel_id', None)
    else:
        allowed_channel_id = None

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'allowed_channel_id': allowed_channel_id}, f)

# 봇 이벤트 및 글로벌 체크 함수
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    load_config()

@bot.check
async def globally_block_dms(ctx):
    if allowed_channel_id is not None and ctx.channel.id != allowed_channel_id:
        await ctx.send("이 채널에서는 명령어를 사용할 수 없습니다.")
        return False
    return True

# 오디오 소스 클래스 정의
class YTDLSource(discord.PCMVolumeTransformer):
    """YouTube에서 오디오를 추출하여 Discord에서 재생할 수 있는 소스를 생성합니다."""
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        """주어진 URL에서 오디오 소스를 생성합니다."""
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception as e:
            print(f"오디오 소스를 가져오는 중 오류 발생: {e}")
            return None

        if 'entries' in data:
            # 재생 목록의 첫 번째 아이템 선택
            data = data['entries'][0]

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)

# MusicPlayer 클래스 정의
class MusicPlayer:
    def __init__(self, guild, text_channel):
        self.guild = guild
        self.text_channel = text_channel
        self.queue = deque()
        self.next = asyncio.Event()
        self.current = None
        self.history = []

        self.bot_loop = bot.loop
        self.task = self.bot_loop.create_task(self.player_loop())

    async def player_loop(self):
        while True:
            self.next.clear()

            # 현재 곡이 설정되어 있으면 그것을 재생
            if self.current:
                source = self.current
                self.current = None  # 재설정
            else:
                if not self.queue:
                    try:
                        async with timeout(300):  # 5분 대기
                            await asyncio.sleep(1)
                            continue
                    except asyncio.TimeoutError:
                        return await self.destroy(self.guild)

                source = self.queue.popleft()

            if not isinstance(source, YTDLSource):
                # 소스를 변환
                source = await YTDLSource.from_url(source)

            if source is None:
                await self.text_channel.send("오디오를 가져오는 데 실패했습니다.")
                continue

            self.history.append(source)

            # 음성 클라이언트 가져오기
            voice_client = self.guild.voice_client

            # 재생 시작
            voice_client.play(source, after=lambda _: self.bot_loop.call_soon_threadsafe(self.play_next_song))
            await self.text_channel.send(f"현재 재생 중: {source.title}")

            await self.next.wait()

    def play_next_song(self):
        self.next.set()

    async def skip(self):
        if self.guild.voice_client.is_playing():
            self.guild.voice_client.stop()

    async def prev(self):
        if len(self.history) >= 2:
            # 현재 곡 제거
            current_song = self.history.pop()
            # 이전 곡 가져오기
            previous_song = self.history.pop()
            # 현재 곡을 대기열의 맨 앞에 추가
            if self.current:
                self.queue.appendleft(self.current)
            else:
                self.queue.appendleft(current_song)
            # 이전 곡을 현재 곡으로 설정
            self.current = previous_song
            await self.skip()
            await self.text_channel.send(f"이전 곡 재생: {previous_song.title}")
        else:
            await self.text_channel.send("이전 곡이 없습니다.")

    async def destroy(self, guild):
        await guild.voice_client.disconnect()
        del players[guild.id]

# 플레이어 인스턴스를 저장할 딕셔너리
players = {}

# 명령어 구현
@bot.command(name='setchannel', help='명령어를 받을 채널을 설정합니다. (관리자 전용)')
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    global allowed_channel_id
    allowed_channel_id = ctx.channel.id
    save_config()
    await ctx.send(f"이제부터 이 채널에서만 명령어를 받습니다.")

@bot.command(name='play', help='음악을 재생하거나 대기열에 추가합니다. 사용법: !play [YouTube URL]')
async def play(ctx, *, url):
    # 사용자가 음성 채널에 있는지 확인
    if not ctx.author.voice:
        await ctx.send("음성 채널에 먼저 접속해주세요.")
        return

    # 봇이 음성 채널에 접속하지 않았다면 접속
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    # 플레이어 가져오기 또는 생성
    player = players.get(ctx.guild.id)
    if not player:
        player = MusicPlayer(ctx.guild, ctx.channel)
        players[ctx.guild.id] = player

    # 음악 추가
    player.queue.append(url)
    await ctx.send(f"대기열에 추가됨: {url}")

@bot.command(name='pause', help='현재 재생 중인 음악을 일시정지합니다.')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("음악을 일시정지했습니다.")
    else:
        await ctx.send("현재 재생 중인 음악이 없습니다.")

@bot.command(name='resume', help='일시정지된 음악을 다시 재생합니다.')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("음악을 다시 재생합니다.")
    else:
        await ctx.send("일시정지된 음악이 없습니다.")

@bot.command(name='stop', help='재생을 중지하고 음성 채널에서 퇴장합니다.')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        player = players.get(ctx.guild.id)
        if player:
            player.queue.clear()
            player.history.clear()
        await ctx.send("재생을 중지하고 음성 채널에서 퇴장합니다.")
    else:
        await ctx.send("봇이 음성 채널에 접속해 있지 않습니다.")

@bot.command(name='queue', help='현재 대기열을 표시합니다.')
async def show_queue(ctx):
    player = players.get(ctx.guild.id)
    if player and player.queue:
        message = '\n'.join([f"{idx+1}. {song.title if isinstance(song, YTDLSource) else song}" for idx, song in enumerate(player.queue)])
        await ctx.send(f"대기열 목록:\n{message}")
    else:
        await ctx.send("대기열이 비어 있습니다.")

@bot.command(name='skip', help='현재 곡을 건너뜁니다.')
async def skip(ctx):
    player = players.get(ctx.guild.id)
    if player:
        await player.skip()
        await ctx.send("현재 곡을 건너뜁니다.")
    else:
        await ctx.send("재생 중인 음악이 없습니다.")

@bot.command(name='clear', help='대기열과 재생 기록을 모두 비웁니다.')
async def clear(ctx):
    player = players.get(ctx.guild.id)
    if player:
        player.queue.clear()
        player.history.clear()
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.send("대기열과 재생 기록을 모두 비웠습니다.")
    else:
        await ctx.send("대기열이 비어 있습니다.")

# 오류 처리: 명령어가 없을 때
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("알 수 없는 명령어입니다. '!help'를 입력하여 사용 가능한 명령어를 확인하세요.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("이 명령어를 사용할 권한이 없습니다.")
    else:
        print(f"Unhandled error: {error}")
        await ctx.send("명령어 실행 중 오류가 발생했습니다.")

# 봇 실행
async def main():
    async with bot:
        await bot.start(token)

# 프로그램 시작
if __name__ == '__main__':
    asyncio.run(main())
