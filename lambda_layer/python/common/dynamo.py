import boto3
from botocore.exceptions import ClientError

from utils import global_util

table = global_util.dynamodb_resource.Table(global_util.table_name)


def get(userId,table_name):
    
    try:
        
        response = table.get_item(Key={'userId': userId})
        print(f"{response=}")
        if response.get('Item') is None:
            raise ValueError("Not found")
        
        return response['Item']

    except ClientError as e:
        print(e.response['Error']['Message'])
        raise SystemError("Server Error")

def put(data,table_name):

    try:
        
        response = table.put_item(
            Item=data
        )
        print(f"{response=}")
        if response is None:
            raise ValueError("Error dynamo put")
        return data

    except ClientError as e:
        print(e.response['Error']['Message'])
        raise SystemError("Server Error")


def get_by_pk_sk(PK, SK):
    try:
        
        response = table.get_item(Key={'PK': PK, 'SK': SK})
        print(f"{response=}")
        if response.get('Item') is None:
            raise ValueError("Not found")
        
        return response['Item']

    except ClientError as e:
        print(e.response['Error']['Message'])
        raise SystemError("Server Error")