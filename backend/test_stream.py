import requests


def get_stream(url, payload: dict):
    s = requests.Session()
    with s.post(url, json=payload, stream=True) as response:
        for line in response.iter_content():
            print(line.decode("utf-8"), end="")


def get_resp(url):
    # get request
    response = requests.get(url)
    print(response.text)


get_resp("http://127.0.0.1:8000/generate-mermaid/")

# payload = {
#     "userID": "user123",
#     "requestID": "request123",
#     "user_input": "AWS Lambda, AWS API Gateway, AWS S3, etc whatever you want",
#     "modelParameter": {"temperature": 0.75, "max_tokens": 2000, "top_p": 0.9},
# }
# url = "http://127.0.0.1:8000/chat-llm"
# get_stream(url, payload)


"""
Input: Create a flowdiagram to deploy a microservice on cloud.
Q1: To create a flow diagram to deploy a microservice on the cloud, I would need some more information. Could you please provide the following details:

What cloud platform are you planning to use for your microservice deployment?
A1. AWS

Q2: What are the specific components or services you nee
A2: AWS Lambda

"""
