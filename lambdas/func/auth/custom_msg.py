# from common import responses, dynamo
import json
from common import responses, dynamo
import os
from utils import global_util
from urllib import parse
from models.auth import profile

trigger_source_list = [
    "CustomEmailSender_SignUp",
    "CustomEmailSender_ResendCode",
    "CustomEmailSender_ForgotPassword",
    "CustomEmailSender_AdminCreateUser",
    "CustomEmailSender_VerifyUserAttribute"
]


def handler(event, context):
    print(f"{event=}")
    try:
        print('event: ', event)
        trigger = event["triggerSource"]
        if trigger in trigger_source_list:
            # frontend_base_url = DEFAULT_FRONTEND_BASE_URL
            DEFAULT_FRONTEND_BASE_URL = global_util.DEFAULT_FRONTEND_BASE_URL
            frontend_base_url = "DEFAULT_FRONTEND_BASE_URL"
            if event.get('request').get('clientMetadata'):
                print('frontend_base_url available')
                frontend_base_url = event.get('request').get('clientMetadata').get('FRONTEND_BASE_URL', DEFAULT_FRONTEND_BASE_URL)

            if 'email' not in event['request']['userAttributes']:
                return event

            print('email available')
            COGNITO_USER_ID_ATTRIBUTE = 'custom:userId'
            email = event['request']['userAttributes']['email']
            custom_user_id = event['request']['userAttributes'].get(COGNITO_USER_ID_ATTRIBUTE)
            name = event['request']['userAttributes'].get('name', "User")
            code = event['request']['code']

            decrypted_code = global_util.decrypt_code(code)
            print('decrypted code: ', decrypted_code)
            
            # DURATION_ALLOWED_EMAIL = 15 * 60  # 15 mins
            
            template_data = {
                "valid_for_mins": global_util.DURATION_ALLOWED_EMAIL//60
            }

            if trigger == "CustomEmailSender_SignUp":
                link = f"{frontend_base_url}/confirm-signup/?email={email}&code={parse.quote(decrypted_code)}"
                template_name = 'regular_signup_template'
                template_data['name'] = name
                template_data['link'] = link

            response = global_util.add_msg_to_sqs(global_util.get_sqs_email_msg(
                    target=email,
                    email_type='template',
                    data={
                        'template_name': template_name,
                        'template_data': template_data,
                    }
                )
            )
            EMAIL_MEDIUM = 'email'
            confirmation_item = profile.ConfirmationCodeModel(userId=custom_user_id, code=decrypted_code, destination=email,
                                                    medium=EMAIL_MEDIUM)
            db_response = add_db_confirmation_item(confirmation_item)
            print(f"{db_response=}")

            return event
        else:
            raise Exception('Invalid trigger source')
    except Exception as e:
        print("Failed")
        print(e)
        print("================")
        raise Exception(str(e))


    # return responses._200({"Success": "post-confirmation", "event": json.dumps(event)})
    return event

def add_db_confirmation_item(item):
    return dynamo.put(item.dict(),global_util.table_name )