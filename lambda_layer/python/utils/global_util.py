import decimal
import hashlib
import json
import logging
import os
import base64
from typing import List
from decimal import Decimal
from enum import Enum


import aws_encryption_sdk
from aws_encryption_sdk.identifiers import CommitmentPolicy

import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics

# ========================== boto3 clients & resources ==========================

sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')
ses_client = boto3.client('ses')
sns_client = boto3.client('sns')
dynamodb_client = boto3.client('dynamodb')
dynamodb_resource = boto3.resource('dynamodb')
s3_resource = boto3.resource('s3')
sm_client = boto3.client('secretsmanager')
cognito_idp_client = boto3.client('cognito-idp')
cognito_identity_client = boto3.client('cognito-identity')
kms_client = boto3.client('kms')
iam_client = boto3.client('iam')
pinpoint_client = boto3.client('pinpoint')
chime_client = boto3.client('chime')
cloudwatch_logs_client = boto3.client('logs')

# ========================== Powertools ==========================
logger = Logger()
tracer = Tracer()
metrics = Metrics()

logger.setLevel(logging.INFO)


def get_formatted_validation_error(e):
    errors = []
    for err in e.errors():
        errors.append(f"{err['loc'][0]}: {err['msg']}")

    return ','.join(errors)


# ========================== environment variables ==========================
sqs_queue_url = os.environ.get('SQS_URL', None)
pinpoint_queue_url = os.environ.get('PINPOINT_QUEUE_URL', None)
userpool_id = os.environ.get('UserPoolID', None)
userpool_client_id = os.environ.get('UserPoolClientID', None)
identity_pool_id = os.environ.get('IdentityPoolId', None)
table_name = os.environ.get('TableName', None)
custom_key_arn = os.environ.get('CUSTOM_KEY_ARN', None)
region = os.environ.get('AWS_REGION', None)
stage_name = os.environ.get('STAGE_NAME', None)
application_id = os.environ.get('APPLICATION_ID', None)

EmailSendingFrom = os.environ.get('EmailSendingFrom', None)

meeting_sqs_queue_arn = os.environ.get('MEETING_SQS_QUEUE_ARN', None)
browser_log_group_name = os.environ.get('BROWSER_LOG_GROUP_NAME', None)
browser_meeting_event_log_group_name = os.environ.get('BROWSER_MEETING_EVENT_LOG_GROUP_NAME', None)
browser_event_ingestion_log_group_name = os.environ.get('BROWSER_EVENT_INGESTION_LOG_GROUP_NAME', None)
chime_endpoint = os.environ.get('CHIME_ENDPOINT', None)
capture_s3_destination_prefix = os.environ.get('CAPTURE_S3_DESTINATION_PREFIX', None)
aws_account_id = os.environ.get('AWS_ACCOUNT_ID', None)
meeting_use_event_bridge = os.environ.get('USE_EVENT_BRIDGE', False)

chime_chat_demo_name = os.environ.get('CHIME_CHAT_DEMO_NAME', None)
chime_chat_app_instance_arn = os.environ.get('CHIME_APP_INSTANCE_ARN', None)
websocket_endpoint_url = os.environ.get('WEBSOCKET_ENDPOINT_URL', None)


# ========================== SES email frontend site URL resolver ==========================

# ========================== Global variables ==========================
RestApiId = os.environ.get('RestApiId')
# DEFAULT_FRONTEND_BASE_URL = f"https://{RestApiId}.execute-api.us-east-1.amazonaws.com/{stage_name}"
DEFAULT_FRONTEND_BASE_URL = f"http://localhost:3002"

frontend_urls = {
    'dev': {
        'admin': "https://dev.d2fw1rx4bl6k51.amplifyapp.com",
        # 'client': "https://dev.d389oal1slpmvu.amplifyapp.com",
        'client': f"{DEFAULT_FRONTEND_BASE_URL}",
        'backend': "https://jxblaltleg.execute-api.us-west-2.amazonaws.com/dev"
    },
    'qa': {
        'admin': "https://qa.d2fw1rx4bl6k51.amplifyapp.com",
        'client': "https://qa.d389oal1slpmvu.amplifyapp.com",
        'backend': "https://jxblaltleg.execute-api.us-west-2.amazonaws.com/dev"
    }
}


def get_frontend_urls():
    return frontend_urls.get(stage_name, frontend_urls.get('dev'))


def get_sqs_email_msg(target="a.hasib.rifat@gmail.com", cc_target='', email_type="custom", data={}):
    if email_type == 'custom':
        email_subject = data.get('email_subject', 'Test Email')
        email_body_text = data.get('email_body_text', 'Test Email')
        email_body_html = data.get('email_body_html', 'Test Email')

        r_dict = {
            'message_type': {
                'DataType': 'String',
                'StringValue': 'email'
            },
            'target': {
                'DataType': 'String',
                'StringValue': target
            },
            'email_type': {
                'DataType': 'String',
                'StringValue': email_type
            },
            'email_subject': {
                'DataType': 'String',
                'StringValue': email_subject
            },
            'email_body_text': {
                'DataType': 'String',
                'StringValue': email_body_text
            },
            'email_body_html': {
                'DataType': 'String',
                'StringValue': email_body_html
            }
        }
        if cc_target != '':
            r_dict['cc_target'] = {
                'DataType': 'String',
                'StringValue': cc_target
            }

        return r_dict


    else:
        r_dict = {
            'message_type': {
                'DataType': 'String',
                'StringValue': 'email'
            },
            'target': {
                'DataType': 'String',
                'StringValue': target
            },
            'email_type': {
                'DataType': 'String',
                'StringValue': email_type
            },
            'template_name': {
                'DataType': 'String',
                'StringValue': data.get('template_name', 'User_Registration')
            },
            'template_data': {
                'DataType': 'String',
                'StringValue': json.dumps(data.get('template_data', {}))
            }
        }
        if cc_target != '':
            r_dict['cc_target'] = {
                'DataType': 'String',
                'StringValue': cc_target
            }
        return r_dict


def prepare_sqs_msg_data(data, msg_type):
    print(f"prepare_sqs_msg_data=> {data=}\n{msg_type=}")
    return {
        'message_type': {
            'DataType': 'String',
            'StringValue': msg_type
        },
        'report_data': {
            'DataType': 'String',
            'StringValue': json.dumps(data)
        },
    }


def add_msg_to_sqs(msg_attr, queue_url=sqs_queue_url):
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        DelaySeconds=5,
        MessageAttributes=msg_attr,
        MessageBody=('sms/email sender')
    )
    return response


# ========================== Generic response ==========================
def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        # should float be used? rounding, precision issues
        # return float(obj)
        return str(obj)
    raise TypeError


def get_hashed_value(password):
    # not yet production ready
    return str(hashlib.sha224(password.encode('utf-8')).hexdigest())


def get_response(status=400, error=True, code="GENERIC", message="NA", data={}, headers={}):
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    final_headers = {**default_headers, **headers}
    return {
        "statusCode": status,
        "headers": final_headers,
        "body": json.dumps({
            "error": error,
            "code": code,
            "message": message,
            "data": data
        }, default=str),  # default=decimal_default),
    }


def get_db_item(pk, sk, table_name):
    table = dynamodb_resource.Table(table_name)
    db_response = table.get_item(
        Key={
            "PK": pk,
            "SK": sk,
        }
    )
    item = db_response.get('Item', None)
    if item is None:
        raise ValueError('Item not found')

    return item

if custom_key_arn:
    encryption_client = aws_encryption_sdk.EncryptionSDKClient(
        commitment_policy=CommitmentPolicy.FORBID_ENCRYPT_ALLOW_DECRYPT)
    kms_key_provider = aws_encryption_sdk.StrictAwsKmsMasterKeyProvider(key_ids=[
        custom_key_arn,
    ])


def decrypt_code(code):
    decrypted_plaintext, decryptor_header = encryption_client.decrypt(
        source=base64.b64decode(code),
        key_provider=kms_key_provider
    )
    return decrypted_plaintext.decode()




def get_dynamodb_type_value(value):
    val_type = type(value)
    if val_type == str or isinstance(value, Enum):
        return {"S": value}
    elif val_type == bool:
        return {"BOOL": value}
    elif val_type == int or val_type == float or val_type == Decimal:
        return {"N": str(value)}
    elif val_type == list or val_type == List:
        return {"L": [get_dynamodb_type_value(v) for v in value]}
    elif val_type == dict:
        temp_dict = dict()
        for k, v in value.items():
            temp_dict[k] = get_dynamodb_type_value(v)
        return {"M": temp_dict}
    else:
        print(val_type)
        raise Exception("Dynamodb type not supported")


DURATION_ALLOWED_EMAIL = 15 * 60  # 15 mins
EXISTING_EMAIL_PHONE = 'EXISTING#EMAIL#PHONE'


class UserMatchNotFound(Exception):
    pass


def parse_cognito_user_dict(attributes):
    cognito_user = {}
    for item in attributes:
        cognito_user[item['Name']] = item['Value']
    return cognito_user

    
def get_cognito_user_by_email_phone(find_text="", medium="email", user_pool_id=userpool_id):
    # filter_str = f"{COGNITO_FILTER_RESOLVER.get(medium)}=\"{find_text}\""
    filter_str = f"email=\"{find_text}\""
    print("filter_str: ", filter_str)
    cognito_response = cognito_idp_client.list_users(
        UserPoolId=user_pool_id,
        # Limit=0,  # limit=1 to get single user does not work
        Filter=filter_str
    )
    print("cognito_response: ", cognito_response)

    if len(cognito_response.get("Users", [])) == 0:
        raise UserMatchNotFound('No user found with provided email/phone!')

    if len(cognito_response.get("Users", [])) != 1:
        raise Exception(f"Invalid {medium} provided!")

    response_user = cognito_response.get("Users")[0]
    print('response_user: ', response_user)
    cognito_user = parse_cognito_user_dict(response_user['Attributes'])
    cognito_user['Username'] = response_user.get('Username')
    cognito_user['UserStatus'] = response_user.get('UserStatus')
    print("cognito user: ", cognito_user)
    return cognito_user
