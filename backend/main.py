import json
import logging
import os
from logging import getLogger

import boto3
from db_utils import get_db_connection
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_aws import ChatBedrock
from pydantic import BaseModel
from user_session import ChatSession, ChatSessionManager

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
conn = get_db_connection()
app = FastAPI()

origins = [
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fix the region_name -> us-west-2
bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")
session_manager = ChatSessionManager(conn=conn)


class ModelKWArgs(BaseModel):
    modelParameter: dict = {
        "temperature": 0.75,
        "max_tokens": 2000,
        "top_p": 0.9,
    }


MODEL = os.getenv("MODEL", "anthropic.claude-3-haiku-20240307-v1:0")


class RequestModel(ModelKWArgs):
    userID: str
    requestID: str
    user_input: str


class MermaidRequest(BaseModel):
    userID: str
    requestID: str


def chat_llm_no_stream(request: RequestModel, chat_session: ChatSession) -> dict:

    chat_model = ChatBedrock(
        model_id=MODEL,
        client=bedrock,
        model_kwargs=request.modelParameter,
        streaming=True,
    )
    if len(chat_session.chats) != 0:
        wants_to_draw_prompt = f"""
            There has been a conversation between the user and the chatbot about building an architecture diagram.
            The last conversation is as follows:
            {json.dumps(chat_session.chats[-1:])}

            You have to judge whether the user wants to draw the diagram or not.
            Given the user's input: {request.user_input}
            Does the user imply that they are done or draw a diagram?
            User may ask: Can you draw...? or I think this is it. or Done, or draw, etc.
            Don't say yes when user lists a bunch of components and their ideas.
            Respond with Yes or No. No extra text.
        """
        wants_to_draw = chat_model.invoke(wants_to_draw_prompt).content
        if "Yes" in wants_to_draw:
            chat_session.add_chat(request.user_input, wants_to_draw, conn=conn)
            return {
                "user_input": request.user_input,
                "wantsToDraw": True,
            }

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
            You are an Technical Chat Assistant and you are working on a project to build a diagram.
            Given the following conversation history of you and user:
            <start>
            {chat_session.str_chat()}
            user: {request.user_input}
            <end>
            Try to suggest the user a solution or ask a question (not necesarily a question). 
            DO NOT REPEAT the questions already answered by the user in the conversation above.
            If asking question, please vary the type of questions (yes/no, multiple choice, open-ended, etc.) to get the required information.
            And if the user is not sure or confused, suggest options.
            Only ask ONE question or suggestion at a time.
        """

    response = chat_model.invoke(text_input)
    logger.info(f"Task created for user: {request.userID}")
    logger.info(f"User chat history: {chat_session.chats}")

    response_content = response.content
    chat_session.add_chat(request.user_input, response_content, conn=conn)
    return {
        "user_input": request.user_input,
        "model_output": response_content,
        "wantsToDraw": False,
    }


def generate_mermaid(chat_session: ChatSession) -> dict:
    model = ChatBedrock(
        model_id=MODEL,
        client=bedrock,
        model_kwargs=chat_session.model_kwargs,
    )
    if not chat_session.chats:
        raise HTTPException(status_code=404, detail="Please provide user requirements.")
    prompt = f"""
    Given the following conversation:
    {chat_session.str_chat()}
    Try to extract user requirements from the conversation and use the context to create the diagram.
    Generate a mermaid code to represent the architecture, diagram, ER diagram or whichever is suitable depending on what user asks for.
    DO NOT INCLUDE the conversation in the diagram. Do no use user or bot in the diagram. 
    You are supposed to draw the archtecture, diagram or flowchart being discussed.
    You can also write texts on the arrows to represent the flow of data where necessary depending on the type of diagram (not everywhere).
        For ex. F -->|Transaction Succeeds| G[Publish PRODUCT_PURCHASED event]
    Make sure to cover all important components and they should have a detailed name.
    Use colors and styles to differentiate between components. Don't use too much styling.
    Only generate the mermaid code and nothing else.
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

    return {
        "mermaid_code": content,
        "userID": chat_session.user_id,
    }


@app.post("/chat-llm/")
def chat_llm(request: RequestModel):
    chat_session = session_manager.get_session(request.userID, request.requestID)
    try:
        response = chat_llm_no_stream(request, chat_session)
        chat_session.user_id = request.userID
        chat_session.request_id = request.requestID
        chat_session.model_id = MODEL
        chat_session.model_kwargs = request.modelParameter
        return response
    except Exception as e:
        logger.error(f"Error generating detailed solution: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating detailed solution: {str(e)}"
        )


@app.post("/generate-mermaid/")
def generate_mermaid_code(mermaid_request: MermaidRequest):
    session_manager.remove_session(mermaid_request.userID)
    chat_session = session_manager.get_session(
        mermaid_request.userID, mermaid_request.requestID
    )
    mermaid_response = generate_mermaid(chat_session)
    return mermaid_response


@app.post("/get-user-history/")
def get_user_history(mermaid_request: MermaidRequest):
    chat_session = session_manager.get_session(
        mermaid_request.userID, mermaid_request.requestID
    )
    chat_history = chat_session.chats
    return {"userID": mermaid_request.userID, "chat_history": chat_history}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
