# from common import responses, dynamo
import os
import time
from aws_lambda_powertools.utilities.parser import parse, ValidationError
from common import responses, dynamo
from utils import global_util
from models.auth import profile

def handler(event, context):
    print(f"{event=}")
    try:
        # queryStringParameters = event.get('queryStringParameters', {})
        # print(f"{queryStringParameters=}")
        # event['body'] = {
        #     'emailOrPhone': queryStringParameters.get('email'),
        #     'confirmationCode': queryStringParameters.get('code'),
        # }

        parsed_body: profile.CodeValidityModel = parse(event=event['body'], model=profile.CodeValidityModel)
        cognito_user = global_util.get_cognito_user_by_email_phone(find_text=parsed_body.emailOrPhone, medium=parsed_body.medium)
        username = cognito_user.get('Username')
        user_id = cognito_user.get('custom:userId')

        print(f"{cognito_user=}")
        confirmation_item = get_confirmation_code(user_id)
        code_item: profile.ConfirmationCodeModel = profile.ConfirmationCodeModel(**confirmation_item)
        is_valid, resp_code, msg = is_confirmation_code_valid(code_item, parsed_body)
        if is_valid:
            confirmation_response = confirm_signup(username, parsed_body.confirmationCode)
            # add_student_group_response = add_user_to_group(username, CLIENT_ROLE)
            # update_aurora_user(user_id, parsed_body.medium)
            db_update_response = update_db_user_status(cognito_user, parsed_body.medium)

            return global_util.get_response(
                status=200,
                error=False,
                code="SIGNUP_CONFIRMED",
                message="Sign-up confirmed. You can now log into your account",
            )
        else:
            return global_util.get_response(
                status=400,
                error=True,
                code=resp_code,
                message=msg,
            )
            
    except ValidationError as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="VALIDATION_ERROR",
            message=get_formatted_validation_error(e),
        )
    except global_util.cognito_idp_client.exceptions.AliasExistsException as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="ALIAS_ALREADY_EXISTS",
            message="Account already exists with provided email/phone!",
        )
    except global_util.cognito_idp_client.exceptions.UserNotFoundException as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="USER_NOT_FOUND",
            message="No user found with provided email/phone!",
        )
    except global_util.cognito_idp_client.exceptions.ExpiredCodeException as e:
        # redundant, this will be caught using DB validation time
        return global_util.get_response(
            status=400,
            error=True,
            code="CONFIRMATION_CODE_EXPIRED",
            message="Confirmation code has expired!",
        )
    except global_util.cognito_idp_client.exceptions.CodeMismatchException as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="CONFIRMATION_CODE_MISMATCH",
            message="Confirmation code does not match!",
        )
    except global_util.cognito_idp_client.exceptions.TooManyRequestsException as e:
        return global_util.get_response(
            status=400,
            error=True,
            code="TOO_MANY_REQUESTS",
            message="Request limit exceeded! Please retry after a short while",
        )
    except global_util.cognito_idp_client.exceptions.InvalidLambdaResponseException as e:
        # this error is thrown if error in post-confirmation
        return global_util.get_response(
            status=400,
            error=True,
            code="POST_CONFIRMATION_ERROR",
            message="Error during post confirmation",
        )
    except Exception as e:
        print(str(e))
        print(e)
        return global_util.get_response(
            status=400,
            error=True,
            code="POST_CONFIRMATION_ERROR",
            message="Error during post confirmation",
        )


def get_confirmation_code(userId):
    dummy_confirmation_item = profile.ConfirmationCodeModel(userId=userId, code="123456", destination="test@test.com",
                                                    medium='email')
    pksk_dict = dummy_confirmation_item.get_user_pk_sk()
    PK = pksk_dict.get('PK')
    SK = pksk_dict.get('SK')

    user = dynamo.get_by_pk_sk(PK=PK, SK=SK)

    return user

def is_confirmation_code_valid(code_item:profile.ConfirmationCodeModel, parsed_body: profile.CodeValidityModel):
    current_time = int(time.time())
    created_at = int(str(code_item.createdAt))
    db_code = str(code_item.code)

    if db_code != parsed_body.confirmationCode:
        return False, "INVALID_CODE", "Invalid code provided"
    if parsed_body.medium == 'email' and (current_time - created_at) > global_util.DURATION_ALLOWED_EMAIL:
        return False, "CONFIRMATION_CODE_EXPIRED", "Confirmation code has expired"

    return True, "CODE_VALID", "Confirmation code is valid"


def confirm_signup(username, confirmationCode):
    confirmation_response = global_util.cognito_idp_client.confirm_sign_up(
        ClientId=global_util.userpool_client_id,
        Username=username,
        ConfirmationCode=confirmationCode
    )
    return confirmation_response

def update_db_user_status(cognito_user, medium):
    return True
    # dummy_user_model: UserModel = UserModel(userId=cognito_user.get(COGNITO_USER_ID_ATTRIBUTE), name='test',
    #                                         signupRole=CLIENT_ROLE, role=CLIENT_ROLE, signupMedium=EMAIL_MEDIUM)
    # response = dynamodb_client.transact_write_items(
    #     TransactItems=[
    #         {
    #             'Update': {
    #                 'TableName': ct_table_name,
    #                 'Key': {
    #                     "PK": {'S': dummy_user_model.PK},
    #                     "SK": {'S': dummy_user_model.SK},
    #                 },
    #                 "ConditionExpression": "attribute_exists(PK)",
    #                 "UpdateExpression": "SET isActivated = :activated, emailVerified = :e_verified, phoneVerified = :p_verified",
    #                 "ExpressionAttributeValues": {
    #                     ":activated": {'BOOL': True},
    #                     ":e_verified": {'BOOL': medium == EMAIL_MEDIUM},
    #                     ":p_verified": {'BOOL': medium == PHONE_MEDIUM},
    #                 }
    #             }
    #         },
    #     ]
    # )
    # return response
