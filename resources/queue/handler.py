# from common import responses, dynamo
import json
from common import responses, dynamo
import os


def hello(event, context):
    print(f"{event=}")
    
    # return responses._200({"Success": "post-confirmation", "event": json.dumps(event)})
    return event