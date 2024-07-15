import json
import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ["db_host"],
        dbname=os.environ["db_name"],
        user=os.environ["db_user"],
        password=os.environ["db_password"],
        port=os.environ["db_port"],
    )
    logger.info("Connection to DB established..")
    return conn


def push_user_chat_to_db(user_id: str, request_id: str, chat: dict[str, str], conn):
    cursor = conn.cursor()
    table = os.environ.get("table_name", "chat_history")
    cursor.execute(
        f"INSERT INTO {table} (user_id, request_id, chat) VALUES ('{user_id}', '{request_id}', '{json.dumps(chat)}')"
    )
    conn.commit()
    cursor.close()
    logger.info("Chat pushed to DB..")


def fetch_user_chat_from_db(
    user_id: str, request_id: str, conn
) -> list[dict[str, str]]:
    cursor = conn.cursor()
    table = os.environ.get("table_name", "chat_history")
    cursor.execute(
        f"SELECT chat FROM {table} WHERE user_id = '{user_id}' AND request_id = '{request_id}'"
    )
    chat = cursor.fetchall()
    cursor.close()
    logger.info("Chat fetched from DB..")
    return chat
