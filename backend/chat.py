import asyncio
import os
import time
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
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"


async def chat_llm(request: RequestModel) -> AsyncIterable:
    callback_handler = AsyncIteratorCallbackHandler()

    chat_model = ChatBedrock(
        model_id=request.model_id,
        client=bedrock,
        model_kwargs=request.modelParameter,
        callbacks=[callback_handler],
        streaming=True,
    )

    text_input = request.user_input
    if len(chat_session.chats) == 0:
        initial_context = """
            I need some help getting the specifics needed to draw an architecture diagram.
            I will now give you my question or task and you can ask me subsequent questions one by one.
            Only ask the question and do not number your questions.
        """
        text_input = initial_context + text_input
    else:
        text_input = f"""
            Given the following conversation of chatbot and user:
            {chat_session.str_chat()}
            Proceed with new user response: "{text_input}" and ask one subsequent question in short if necessary.
            Only ask the question and no extra text.
        """

    task = asyncio.create_task(
        chat_model.agenerate(messages=[[HumanMessage(content=text_input)]])
    )
    logger.info(f"Task created for user: {request.userID}")
    logger.info(f"User chat history: {chat_session.chats}")
    print(f"Task created for user: {request.userID}")
    print(f"User chat history: {chat_session.chats}")
    response_content = ""
    try:
        async for token in callback_handler.aiter():
            response_content += token
            yield token
    except Exception as e:
        print(f"Caught exception: {e}")
    finally:
        callback_handler.done.set()
    chat_session.add_chat(request.user_input, response_content)
    await task


def generate_mermaid() -> str:
    model = ChatBedrock(
        model_id=chat_session.model_id,
        client=bedrock,
        model_kwargs=chat_session.model_kwargs,
    )
    if not chat_session.chats:
        raise HTTPException(status_code=404, detail="Please provide user requirements.")
    prompt = f"""
    Given the following conversation:
    {chat_session.str_chat()}
    Generate a mermaid code to represent the architecture.
    Make sure each component's name is detailed'.
    Also write texts on the arrows to represent the flow of data.
    Only generate the code and nothing else.
    """
    response = model.invoke(prompt)
    content = response.content

    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    if content.startswith("mermaid"):
        content = content[7:]

    last_index = content.rfind("```")
    if last_index != -1:
        content = content[:last_index]

    return content


@app.post("/chat-llm/")
async def stream_chat(request: RequestModel):
    generator = chat_llm(request)
    chat_session.user_id = request.userID
    chat_session.request_id = request.requestID
    chat_session.model_id = request.model_id
    chat_session.model_kwargs = request.modelParameter
    return StreamingResponse(generator, media_type="text/event-stream")


@app.get("/generate-mermaid/")
def generate_mermaid_code():
    mermaid_code = generate_mermaid()
    chat_session.flush()
    return mermaid_code


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
