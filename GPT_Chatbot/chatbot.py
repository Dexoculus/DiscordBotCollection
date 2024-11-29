import os
import discord
import openai

from Token import *

# API 키 설정
openai.api_key = GPT_tokon
DISCORD_BOT_TOKEN = discord_token

# 디스코드 클라이언트 설정
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 사용자별 대화 기록 저장
chat_history = {}

@client.event
async def on_ready():
    print(f'로그인 성공: {client.user}')

@client.event
async def on_message(message):
    # 봇 자신의 메시지는 무시
    if message.author == client.user:
        return

    # 메시지가 특정 프리픽스로 시작하는지 확인 (선택 사항)
    # 만약 모든 메시지에 응답하려면 이 부분을 제거하세요.
    if not message.content.startswith('!'):
        return

    user_id = message.author.id

    # 사용자별로 대화 기록 관리
    if user_id not in chat_history:
        chat_history[user_id] = []

    # 사용자 메시지 추가
    chat_history[user_id].append({"role": "user", "content": message.content})

    try:
        # OpenAI API에 대화 기록 전달
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=chat_history[user_id]
        )

        # 응답 내용 추출
        reply = response.choices[0].message.content

        # 봇의 응답 추가
        chat_history[user_id].append({"role": "assistant", "content": reply})

        # 채널에 응답 전송
        await message.channel.send(reply)

    except Exception as e:
        # 에러 처리
        await message.channel.send("죄송합니다. 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        print(f"에러 발생: {e}")

# 봇 실행
client.run(DISCORD_BOT_TOKEN)
