import os
import logging
import re
import traceback

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger

from history import fetch_history, save_message
from retriever import retrieve_and_rerank
from generator import generate_answer

logger = Logger()

SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
)


def _remove_mentions(text: str) -> str:
    # メンションからテキストのみを抽出する
    mention_pattern = r"<@\w+>"
    cleaned_text = re.sub(mention_pattern, "", text)
    return cleaned_text


def _remove_after_backticks(text: str) -> str:
    # AIが """python みたいにコードブロックに言語情報を付けてくれるが、いらないので削除する
    return re.sub(r"```(\w+)", "```", text)


@app.event("app_mention")
def mention_handler(body, say):
    event = body["event"]
    text = _remove_mentions(event["text"])
    channel = event["channel"]
    thread_ts = event["ts"]

    try:
        messages = fetch_history(channel, event["user"], text)
        _, documents = retrieve_and_rerank(messages)
        answer = generate_answer(messages, documents)
        answer["references"] = [
            ref.replace("http://", "https://") for ref in answer["references"]
        ]

        save_message(channel, event["user"], {"role": "user", "text": text})
        save_message(
            channel, event["user"], {"role": "assistant", "text": answer["text"]}
        )

        logger.info(
            "Successfully generated answer",
            extra={
                "client_msg_id": event["client_msg_id"],
                "references": answer["references"],
            },
        )
    except Exception:
        reply = (
            f"エラーが発生しました：```\n"
            f"client_msg_id: {event['client_msg_id']}\n"
            f"{traceback.format_exc()}```"
        )
        say(text=reply, channel=channel, thread_ts=thread_ts)
        return

    reply = _remove_after_backticks(answer["text"])

    # 参考情報を付与
    if len(answer["references"]) > 0:
        reply += "\n\n📚参考：\n"
    for ref in answer["references"]:
        reply += ref + "\n"

    say(text=reply, channel=channel, thread_ts=thread_ts)


def handler(event, context):
    if event["headers"].get("x-slack-retry-num"):
        # 再送の場合はスルーする
        return {"statucCode": 200}

    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
