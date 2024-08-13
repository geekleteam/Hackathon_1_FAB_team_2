from fastapi import HTTPException
from fastapi.responses import RedirectResponse
import workos
import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv()
workos.api_key = os.environ["WORK_OS_API_KEY"]
workos.client_id = os.environ["WORK_OS_CLIENT_ID"]
client_id = os.environ["WORK_OS_CLIENT_ID"]
# Configure logging
logging.basicConfig(level=logging.INFO)

async def get_authorization_url():
    organization = os.environ["WORK_OS_ORGANIZATION_ID"]
    redirect_uri = "http://localhost:8000/callback"

    authorization_url = workos.client.sso.get_authorization_url(
        organization=organization,
        redirect_uri=redirect_uri,
    )

    logging.info(f"Authorization URL: {authorization_url}")
    return RedirectResponse(authorization_url)

async def handle_callback(code: str):
    try:
        logging.info(f"Received code: {code}")
        profile_and_token = workos.client.sso.get_profile_and_token(
            code=code,
        )
        profile = profile_and_token.profile

        logging.info(f"Profile: {profile}")

        organization = os.environ["WORK_OS_ORGANIZATION_ID"]

        if profile["organization_id"] != organization:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return RedirectResponse(url="/")
    except workos.exceptions.BadRequestException as e:
        logging.error(f"BadRequestException: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Exception: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")