# from common import responses, dynamo
import json
import os

import ksuid
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.parser import parse
from common import responses
from models.auth import profile
from pydantic import ValidationError
from utils import model_util, global_util

table_name = os.environ.get("TableName")
cognito_user_pool = os.environ.get("UserPoolID")
CustomRole = os.environ.get("CustomRole")


def users_exists(param):
    try:
        pk = param.get("PK")
        sk = param.get("SK")
        item = global_util.get_db_item(pk=pk, sk=sk, table_name=table_name)
        return item
    except ValueError as e:
        return False


def handler(event, context):
    try:
        parsed_event = APIGatewayProxyEvent(event)
        parsed_body: profile.SigninModel = parse(event=parsed_event.body, model=profile.SigninModel)
        account_id = event['requestContext']['accountId']
        cognito_user = global_util.get_cognito_user_by_email_phone(find_text=parsed_body.emailOrPhone,
                                                                   medium=parsed_body.medium)

        if cognito_user.get('UserStatus') == 'UNCONFIRMED':
            return global_util.get_response(
                status=400,
                error=True,
                code="USER_NOT_CONFIRMED",
                message="User account not confirmed! Check email/sms for account confirmation code",
            )

        auth_response = global_util.cognito_idp_client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': cognito_user.get('Username'),
                'PASSWORD': parsed_body.password
            },
            ClientId=global_util.userpool_client_id
        )
        print("auth response: ", auth_response)

        # login_param = f"cognito-idp.{region}.amazonaws.com/{global_util.userpool_id}"
        login_param = f"cognito-idp.us-east-1.amazonaws.com/{global_util.userpool_id}"

        id_response = global_util.cognito_identity_client.get_id(
            AccountId=account_id,
            IdentityPoolId=global_util.identity_pool_id,
            Logins={
                login_param: auth_response['AuthenticationResult']['IdToken']
            }
        )
        identity_id = id_response['IdentityId']
        print("Identity ID: ", identity_id)
        print(f'{CustomRole=}')
        resp = global_util.cognito_identity_client.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins={
                login_param: auth_response['AuthenticationResult']['IdToken']
            },
            # CustomRoleArn=f'{CustomRole}'
        )
        token_response = {
            "idToken": auth_response["AuthenticationResult"]['IdToken'],
            "accessToken": auth_response["AuthenticationResult"]['AccessToken'],
            "refreshToken": auth_response["AuthenticationResult"]['RefreshToken'],
            "expiresIn": auth_response["AuthenticationResult"]['ExpiresIn'],
            "tokenType": auth_response["AuthenticationResult"]['TokenType'],
            "accessKey": resp['Credentials']['AccessKeyId'],
            "secretKey": resp['Credentials']['SecretKey'],
            "sessionToken": resp['Credentials']['SessionToken'],
        }
        print("resp", resp)
        return global_util.get_response(
            status=200,
            error=False,
            message="Sign in successful",
            data=token_response
        )
    except ValidationError as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="VALIDATION_ERROR",
            # message=get_formatted_validation_error(e),
            message=str(e),
        )
    except global_util.cognito_idp_client.exceptions.UserNotConfirmedException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="USER_NOT_CONFIRMED",
            message="User account not confirmed! Check email/sms for account confirmation code",
        )
    except global_util.cognito_idp_client.exceptions.UserNotFoundException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="USER_NOT_FOUND",
            message="No user found with provided email/phone!",
        )
    except global_util.cognito_idp_client.exceptions.TooManyRequestsException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="TOO_MANY_REQUESTS",
            message="Request limit exceeded! Please retry after a short while",
        )
    except global_util.cognito_idp_client.exceptions.NotAuthorizedException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="SIGNIN_NOT_AUTHORIZED",
            message="Incorrect username or password",
        )
    except Exception as e:
        print(str(e))
        return global_util.get_response(
            status=500,
            error=True,
            code="NA",
            message=str(e),
        )
