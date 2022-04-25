from common import responses, dynamo
import json
import os

import ksuid
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.parser import parse
from common import responses
from models.auth import profile
from pydantic import ValidationError
from utils import model_util, global_util

# table_name = os.environ.get("TableName")
# cognito_user_pool = os.environ.get("UserPoolID")


def users_exists(param):
    try:
        pk = param.get("PK")
        sk = param.get("SK")
        item = global_util.get_db_item(pk=pk, sk=sk, table_name=global_util.table_name)
        print(f"{item=}")
        return item
    except ValueError as e:
        return False


def handler(event, context):
    try:
        userId = str(ksuid.ksuid())
        parsed_event = APIGatewayProxyEvent(event)
        parsed_body: profile.UserSignup = parse(event=parsed_event.body, model=profile.UserSignup)
        dynamo_user = profile.ExistingEmailPhoneModel(
                    emailOrPhone=parsed_body.emailOrPhone,
                    medium=parsed_body.medium,
                    userId=userId,
                )
        if users_exists(dynamo_user.get_user_pk_sk()):
            return global_util.get_response(
                status=400,
                error=True,
                code="USERNAME_ALREADY_EXISTS",
                message="Email/Phone already exists!",
            )
        
        cognito_response = add_cognito_user(parsed_body, event, userId)
        dynamo_user = profile.ExistingEmailPhoneModel(
            userId=userId,
            emailOrPhone=parsed_body.emailOrPhone,
            medium=parsed_body.medium
        )
        dynamo_response = dynamo.put(dynamo_user.dict(), global_util.table_name)

        return global_util.get_response(
            status=200,
            error=False,
            code="SIGNUP_SUCCESSFUL",
            message="User signup successful. You will receive an email/sms containing a confirmation code. "
                    "Please confirm your account before signing in.",
            data=cognito_response
        )
    except ValidationError as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="VALIDATION_ERROR",
            message=global_util.get_formatted_validation_error(e),
        )
    except global_util.cognito_idp_client.exceptions.InvalidPasswordException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="INVALID_PASSWORD",
            message="Invalid password format! (Must contain 1 lowercase letter, 1 uppercase latter and 1 number)!",
        )
    except global_util.cognito_idp_client.exceptions.UsernameExistsException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="USERNAME_ALREADY_EXISTS",
            message="Email/Phone already exists!",
        )
    except global_util.cognito_idp_client.exceptions.CodeDeliveryFailureException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="CODE_DELIVERY_FAILED",
            message="Failed to deliver account confirmation code!",
        )
    except Exception as e:
        print(str(e))
        return global_util.get_response(
            status=500,
            error=True,
            code="NA",
            message=str(e),
        )


def add_cognito_user(user_model: profile.UserSignup, event, userId):
    cognito_response = global_util.cognito_idp_client.sign_up(
        ClientId=global_util.userpool_client_id,
        Username=userId,
        Password=user_model.password,
        UserAttributes=[
            {
                'Name': 'email',
                'Value': user_model.emailOrPhone,
            },
            {
                'Name': 'custom:signupMedium',
                'Value': user_model.medium,
            },
            {
                'Name': 'custom:userId',
                'Value': userId,
            },
        ],
        ClientMetadata={
            "FRONTEND_BASE_URL": event.get('headers', {}).get('origin', global_util.get_frontend_urls().get('client'))
        },
    )
    return cognito_response

# pip install -t python/lib/python3.8/site-packages -r ../lambda_layer/python/requirements.txt
# https://medium.com/@dorian599/serverless-aws-lambda-layers-and-python-dependencies-92741138bf31
# https://github.com/serverless/serverless-python-requirements
