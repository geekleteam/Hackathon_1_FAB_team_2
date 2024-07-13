import asyncio
import os
from logging import getLogger
from typing import AsyncIterable

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.schema import HumanMessage
from langchain_aws import ChatBedrock
from pydantic import BaseModel
from user_session import ChatSession

logger = getLogger(__name__)
app = FastAPI()

os.environ["AWS_PROFILE"] = "yash-geekle"
origins = [
    "*",
]
chat_session = ChatSession()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fix the region_name -> us-west-2
bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")


class ModelKWArgs(BaseModel):
    modelParameter: dict = {
        "temperature": 0.75,
        "max_tokens": 2000,
        "top_p": 0.9,
    }


class RequestModel(ModelKWArgs):
    userID: str
    requestID: str
    user_input: str
    model_id: str = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


async def chat_llm(request: RequestModel) -> AsyncIterable:
    callback_handler = AsyncIteratorCallbackHandler()

    chat_model = ChatBedrock(
        model_id=request.model_id,
        client=bedrock,
        model_kwargs=request.modelParameter,
        callbacks=[callback_handler],
        streaming=True,
    )

    task = asyncio.create_task(
        chat_model.agenerate(messages=[[HumanMessage(content=request.user_input)]])
    )

    try:
        async for token in callback_handler.aiter():
            yield token
    except Exception as e:
        print(f"Caught exception: {e}")
    finally:
        callback_handler.done.set()

    await task


@app.post("/chat-llm/")
async def stream_chat(request: RequestModel):
    generator = chat_llm(request)
    chat_session.user_id = request.userID
    chat_session.request_id = request.requestID
    chat_session.model_id = request.model_id
    chat_session.model_kwargs = request.modelParameter
    return StreamingResponse(generator, media_type="text/event-stream")


@app.get("flush-chat/")
async def flush_chat():
    chat_session.flush()
    return {"message": "Chat flushed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
