import boto3
import json
from django.conf import settings

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
)

def get_five_question(skill):
    body = {
        "inputText":"give me 5 question for {} skill".format(skill),
        "textGenerationConfig":{
            "maxTokenCount":296,
            "stopSequences":[],
            "temperature":0.5,
            "topP":0.9
        }
    }

    data = {
        "modelId": "amazon.titan-text-lite-v1",
        "contentType": "application/json",
        "accept": "*/*",
        "body": json.dumps(body)
    }

    response = bedrock.invoke_model(
        body=data["body"],
        modelId=data["modelId"],
        accept=data["accept"],
        contentType=data["contentType"]
    )
    response_body = json.loads(response['body'].read())
    return response_body


def get_single_question(skill):
    body = {
        "inputText":"give me a question for {} skill".format(skill),
        "textGenerationConfig":{
            "maxTokenCount":296,
            "stopSequences":[],
            "temperature":0.5,
            "topP":0.9
        }
    }

    data = {
        "modelId": "amazon.titan-text-lite-v1",
        "contentType": "application/json",
        "accept": "*/*",
        "body": json.dumps(body)
    }

    response = bedrock.invoke_model(
        body=data["body"],
        modelId=data["modelId"],
        accept=data["accept"],
        contentType=data["contentType"]
    )
    response_body = json.loads(response['body'].read())
    return response_body


# META Model
# bedrock = boto3.client(
#     service_name="bedrock-runtime",
#     region_name="us-east-1",
#     aws_access_key_id=settings.AWS_ACCESS_KEY,
#     aws_secret_access_key=settings.AWS_SECRET_KEY,
# )
# body = {
#     "prompt":"give me 5 questions for css",
#     "maxTokens":96,
#     "temperature":0.7,
#     "topP":1,
#     "stopSequences":[],
#     "countPenalty":{"scale":0},
#     "presencePenalty":{"scale":0},
#     "frequencyPenalty":{"scale":0}
# }
# data = {
#     "modelId": "ai21.j2-mid-v1",
#     "contentType": "application/json",
#     "accept": "*/*",
#     "body": json.dumps(body)
# }

# response = bedrock.invoke_model(
#     body=data["body"],
#     modelId=data["modelId"],
#     accept=data["accept"],
#     contentType=data["contentType"]
# )
# response_body = json.loads(response['body'].read())
# questions = response_body.get("completions", [{"data": []}])[0].get("data", {}).get("text")

# questions = re.sub('[0-9]. ', '', questions)
# questions = questions.split("\n")[-1:-6:-1]