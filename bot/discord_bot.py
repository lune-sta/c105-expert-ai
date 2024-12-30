import os
import logging
import re
import traceback
import asyncio

import discord

from retriever import retrieve_and_rerank
from generator import generate_answer

# Logger の設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger('discord').setLevel(logging.ERROR)
logging.getLogger('discord.http').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)

DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']

intents = discord.Intents.default()
intents.typing = False
discord_client = discord.Client(intents=intents)


async def generate_reply(messages: list) -> str:
    try:
        _, documents = await asyncio.to_thread(retrieve_and_rerank, messages)
        answer = await asyncio.to_thread(generate_answer, messages, documents)
    except Exception:
        reply = (
            f"エラーが発生しました：```\n"
            f"{traceback.format_exc()}```"
        )
        return reply

    reply = answer["text"]

    # 参考情報を付与
    if len(answer["references"]) > 0:
        reply += "\n\n📚参考：\n"
    for ref in answer["references"]:
        reply += ref + "\n"

    return reply


def _get_role(author) -> str:
    if author == discord_client.user:
        return "assistant"
    else:
        return "user"


def _remove_mentions(message: str) -> str:
    # Mention などの不要な文字を削除する
    return re.sub(r"<@\d+>", "", message).strip()


_processed_messages = {}


@discord_client.event
async def on_message(message):
    if message.id in _processed_messages:
        return

    _processed_messages[message.id] = True

    if not (
            discord_client.user.mentioned_in(message)
            and message.author != discord_client.user
    ):
        return

    if message.reference:
        # リプライツリーがある場合、さかのぼってログを取得する
        referenced_message = await message.channel.fetch_message(
            message.reference.message_id
        )
        messages = []

        messages.append(
            {
                "role": _get_role(referenced_message.author),
                "content": _remove_mentions(referenced_message.content),
            }
        )

        referenced_message = referenced_message.reference
        while referenced_message is not None:
            referenced_message = await message.channel.fetch_message(
                referenced_message.message_id
            )
            messages.append(
                {
                    "role": _get_role(referenced_message.author),
                    "content": _remove_mentions(referenced_message.content),
                }
            )
            referenced_message = referenced_message.reference
        messages.reverse()
        messages.append(
            {
                "role": _get_role(message.author),
                "content": _remove_mentions(message.content),
            }
        )
        messages.append({"role": "user", "content": message.content})
        response = await generate_reply(messages)
        await message.channel.send(response, reference=message)

    else:
        # リプライツリーがない場合
        response = await generate_reply([{"role": "user", "content": message.content}])
        await message.channel.send(response, reference=message)


if __name__ == "__main__":
    discord_client.run(DISCORD_BOT_TOKEN)
