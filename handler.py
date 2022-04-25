import json
import os

def hello(event, context):
    print(f"{event=}")
    print(f"{os.environ=}")
    body = {
        "message": "Go Serverless v3.0! Your function executed successfully!",
        "input": event,
    }

    return {"statusCode": 200, "body": json.dumps(body)}

