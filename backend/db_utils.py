import json
import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ["db_host"],
            dbname=os.environ["db_name"],
            user=os.environ["db_user"],
            password=os.environ["db_password"],
            port=os.environ["db_port"],
        )
        logger.info("Connection to DB established..")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to DB: {str(e)}")
        raise e


def push_user_chat_to_db(user_id: str, request_id: str, chat: dict[str, str], conn):
    cursor = conn.cursor()
    table = os.environ.get("table_name", "chat_history")
    try:
        cursor.execute(
            f"INSERT INTO {table} (user_id, request_id, chat) VALUES ('{user_id}', '{request_id}', '{json.dumps(chat)}')"
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error pushing chat to DB: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
    logger.info("Chat pushed to DB..")
    logger.info(chat)


def fetch_user_chat_from_db(
    user_id: str, request_id: str, conn
) -> list[dict[str, str]]:
    cursor = conn.cursor()
    table = os.environ.get("table_name", "chat_history")
    try:
        cursor.execute(
            f"SELECT chat FROM {table} WHERE user_id = '{user_id}' AND request_id = '{request_id}'"
        )
        chat = [c[0] for c in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching chat from DB: {str(e)}")
        chat = []
        conn.rollback()
    finally:
        cursor.close()
    logger.info("Chat fetched from DB..")
    logger.info(chat)
    return chat
