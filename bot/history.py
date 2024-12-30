import os
import json
from typing import TypedDict
from datetime import datetime

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute

from clients import bedrock_runtime_client
import config

"""
DynamoDBでSlackの履歴を管理する。
app_mentionイベントではスレッド固有のIDが取得できないため、AIの力で会話の続きなのか判断させる。
https://api.slack.com/events/app_mention
制約がないなら他のイベントやAPIを使った方がよさそう。
"""


class HistoryModel(Model):
    class Meta:
        table_name = os.environ.get("HISTORY_TABLE_NAME", "")

    ch_user = UnicodeAttribute(hash_key=True)
    timestamp = NumberAttribute(range_key=True)
    role = UnicodeAttribute()
    text = UnicodeAttribute()
    ttl = NumberAttribute()


_tool_name = "send_conversation_status"
_tool_definition = {
    "toolSpec": {
        "name": _tool_name,
        "description": "Send the continuity of the topic",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "is_continue": {
                        "type": "boolean",
                        "description": "The conversation context is the same"
                        " (the topic is continuing) if true, otherwise false.",
                    }
                },
                "required": ["is_continue"],
            }
        },
    }
}

_prompt = """スレッドIDがないため、新しいメッセージが過去ログの続きなのか分からないデータがあります。
<messages>タグではユーザーとの会話の過去ログが、<new_message>ではユーザーの新しいメッセージが与えられます。
あなたは過去ログと新しいメッセージが同じスレッドの会話かどうか（話が継続しているか）を判断して下さい。
判断が難しい場合は継続していると答えて下さい。回答には $tool_name$ ツールのみを使用してください。

<messages>
$messages$
</messages>

<new_message>
$new_message
</new_message>
"""


class Message(TypedDict):
    role: str
    text: str


def _is_conversation_continuous(messages: list[Message], new_message: Message) -> bool:
    prompt = (
        _prompt.replace("tool_name", _tool_name)
        .replace("$messages$", json.dumps(messages, indent=2, ensure_ascii=False))
        .replace("$new_message$", json.dumps(new_message, indent=2, ensure_ascii=False))
    )

    response = bedrock_runtime_client.converse(
        modelId=config.CHEAP_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        toolConfig={
            "tools": [_tool_definition],
            "toolChoice": {
                "tool": {
                    "name": _tool_name,
                },
            },
        },
    )
    answer = response["output"]["message"]["content"][0]["toolUse"]["input"][
        "is_continue"
    ]
    return answer


def fetch_history(channel_id: str, user_id: str, text: str) -> list[Message]:
    new_message = {"role": "user", "text": text}
    messages = []
    query_result = HistoryModel.query(
        hash_key=f"{channel_id}#{user_id}", scan_index_forward=True
    )

    for message in query_result:
        messages.append({"role": message.role, "text": message.text})
    is_continue = _is_conversation_continuous(messages, new_message)

    if is_continue:
        messages.append(new_message)
        return messages
    else:
        with HistoryModel.batch_write() as batch:
            for item in query_result:
                batch.delete(item)

        return [new_message]


def save_message(channel_id: str, user_id: str, message: Message):
    timestamp = int(datetime.now().timestamp())
    if message["role"] == "assistant":
        timestamp += 1

    new_message = HistoryModel()
    new_message.ch_user = f"{channel_id}#{user_id}"
    new_message.timestamp = timestamp
    new_message.role = message["role"]
    new_message.text = message["text"]
    # TTL 1week
    new_message.ttl = timestamp + 60 * 60 * 24 * 7
    new_message.save()
