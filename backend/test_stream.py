import json

import requests


def post_resp(url, payload):
    response = requests.post(url, json=payload)
    response = response.json()
    print(json.dumps(response, indent=4))


user_input = (
    "A data processing component, a db component, model registry, cloudwatch, etc"
)
payload = {
    "userID": "user123",
    "requestID": "request123",
    "user_input": user_input,
    "modelParameter": {"temperature": 0.75, "max_tokens": 2000, "top_p": 0.9},
}
url = "http://127.0.0.1:8000/chat-llm"

payload = {"userID": "user123"}
# url = "http://127.0.0.1:8000/generate-mermaid"
url = "http://127.0.0.1:8000/get-user-history"


print("User Input:", user_input)
print("Response:")
post_resp(url, payload)


"""
Input: Create a flowdiagram to deploy a microservice on cloud.
Q1: To create a flow diagram to deploy a microservice on the cloud, I would need some more information. Could you please provide the following details:

What cloud platform are you planning to use for your microservice deployment?
A1. AWS

Q2: What are the specific components or services you nee
A2: AWS Lambda

"""
