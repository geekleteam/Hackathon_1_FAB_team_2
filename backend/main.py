import logging
import os
from logging import getLogger

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_aws import ChatBedrock
from pydantic import BaseModel
from user_session import ChatSession, ChatSessionManager

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
app = FastAPI()

# os.environ["AWS_PROFILE"] = "yash-geekle"
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
session_manager = ChatSessionManager()


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
    modelID: str = "anthropic.claude-3-haiku-20240307-v1:0"


class MermaidRequest(BaseModel):
    userID: str


def chat_llm_no_stream(request: RequestModel, chat_session: ChatSession) -> dict:

    chat_model = ChatBedrock(
        model_id=request.modelID,
        client=bedrock,
        model_kwargs=request.modelParameter,
        streaming=True,
    )
    if len(chat_session.chats) != 0:
        wants_to_draw_prompt = f"""
            There has been a conversation between the user and the chatbot about building an architecture diagram.
            You have to judge whether the user wants to draw the diagram or not.
            Given the user's input: {request.user_input}
            Does the user imply that they are done or draw a diagram?
            User may ask: Can you draw...? or I think this is it. or Done, or draw, etc.
            Don't say yes when user lists a bunch of components and their ideas.
            Respond with Yes or No. 
        """
        wants_to_draw = chat_model.invoke(wants_to_draw_prompt).content
        if "Yes" in wants_to_draw:
            chat_session.add_chat(request.user_input, wants_to_draw)
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
            Given the following conversation of chatbot and user:
            {chat_session.str_chat()}
            Proceed with new user response: "{text_input}" and ask one subsequent question in fewer than 100 words if necessary.
            Try to suggest the options for the user to choose from along with the question. 
            Please vary the type of questions (yes/no, multiple choice, open-ended, etc.) to get the required information.
            Only ask the question and no extra text.
        """

    response = chat_model.invoke(text_input)
    logger.info(f"Task created for user: {request.userID}")
    logger.info(f"User chat history: {chat_session.chats}")

    response_content = response.content
    chat_session.add_chat(request.user_input, response_content)
    return {
        "user_input": request.user_input,
        "model_output": response_content,
        "wantsToDraw": False,
    }


def generate_mermaid(chat_session: ChatSession) -> dict:
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
    Make sure each component's name is detailed.
    Also write texts on the arrows to represent the flow of data. 
        For ex. F -->|Transaction Succeeds| G[Publish PRODUCT_PURCHASED event] --> END
    If you're using style, dont use quotes after it. You often make that mistake.
    Only generate the code and nothing else.
    Include as many components as possible and each component should have a detailed name.
    Use colors and styles to differentiate between components. Be creative.
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
    chat_session = session_manager.get_session(request.userID)
    try:
        response = chat_llm_no_stream(request, chat_session)
        chat_session.user_id = request.userID
        chat_session.request_id = request.requestID
        chat_session.model_id = request.modelID
        chat_session.model_kwargs = request.modelParameter
        return response
    except Exception as e:
        logger.error(f"Error generating detailed solution: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating detailed solution: {str(e)}"
        )


@app.post("/generate-mermaid/")
def generate_mermaid_code(mermaid_request: MermaidRequest):
    chat_session = session_manager.get_session(mermaid_request.userID)
    mermaid_response = generate_mermaid(chat_session)
    return mermaid_response


@app.post("/get-user-history/")
def get_user_history(mermaid_request: MermaidRequest):
    chat_session = session_manager.get_session(mermaid_request.userID)
    chat_history = chat_session.chats
    return {"userID": mermaid_request.userID, "chat_history": chat_history}


@app.post("/delete-user-history/")
def get_user_history(mermaid_request: MermaidRequest):
    session_manager.remove_session(mermaid_request.userID)

    return {"userID": mermaid_request.userID, "status": "deleted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
