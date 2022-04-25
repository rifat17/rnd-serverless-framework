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

def handler(event, context):
    print(f"{event=}")
    try:
        parsed_event = APIGatewayProxyEvent(event)
        parsed_body: profile.LogoutModel = parse(event=parsed_event.body, model=profile.LogoutModel)
        response = cognito_signout_user(parsed_body.accessToken)
        return global_util.get_response(
            status=200,
            error=False,
            code="USER_LOGGED_OUT",
            message="Logged out",
        )
    except ValidationError as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="VALIDATION_ERROR",
            message=global_util.get_formatted_validation_error(e),
        )
    except global_util.cognito_idp_client.exceptions.UserNotFoundException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="USER_NOT_FOUND",
            message="No user found with provided email/phone!",
        )
    except global_util.cognito_idp_client.exceptions.UserNotConfirmedException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="USER_NOT_CONFIRMED",
            message="User account not confirmed! Check email/sms for account confirmation code",
        )
    except global_util.cognito_idp_client.exceptions.TooManyRequestsException as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="TOO_MANY_REQUESTS",
            message="Request limit exceeded! Please retry after a short while",
        )
    except Exception as e:
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            message=str(e),
        )


def cognito_signout_user(access_token):
    signout_user_response = global_util.cognito_idp_client.global_sign_out(
        AccessToken=access_token
    )
    print(f"{signout_user_response=}")
    return signout_user_response
