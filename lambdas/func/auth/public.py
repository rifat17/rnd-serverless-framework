import json
import os
from utils import global_util

def handler(event, context):
    print(f"{event=}")
    print(f"{os.environ=}")
    body = {
        "message": "Welcome to Public Api",
        # "input": event,
    }

    return global_util.get_response(
        status=200,
        error=False,
        message="Api Call successful",
        data=body
        )

