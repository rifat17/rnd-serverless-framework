# from common import responses, dynamo
from common import responses, dynamo
import os

table_name = os.environ.get("TableName")

def handler(event, context):
    print(f"{event=}")
    pathParameters = event.get('pathParameters')
    if pathParameters is None or pathParameters.get('userId') is None:
        return responses._400({"message": "missing the ID from the path"})

    userId = pathParameters.get('userId')
    try:
        user = dynamo.get(userId, table_name)
        return responses._200(user)

    except (SystemError, ValueError) as e:
        return responses._400({"message": str(e)})
    
