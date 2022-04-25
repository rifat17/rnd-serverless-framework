# from common import responses, dynamo
from common import responses, dynamo
import os
from utils import global_util

def handler(event, context):
    print(f"{event=}")
    for message in event['Records']:
        isError = True
        try:
            print('event: ', event)
            # message = event['Records'][0]
            message_props = parse_message_properties(message)
            print('message prorps: ', message_props)
            
            
            if message_props['message_type'] == 'email':
                print(f"inside email message type")
                email_response = send_email(message_props)
            msg_delete_response = delete_sqs_message(message)
            isError = False

        except Exception as e:
            print(e)
        finally:
            if isError:
                raise Exception('message not deleted')




def send_email(message_props):
    if message_props['email_type'] == 'custom':
        return send_custom_email(message_props)
    else:
        return send_template_email(message_props)


def send_template_email(message_props):
    RECIPIENT_LIST = [email.strip() for email in message_props['target'].split(',')]
    CC_RECIPIENT_LIST = [email.strip() for email in message_props.get('cc_target', '').split(',')]
    CC_RECIPIENT_LIST = list(filter(None, CC_RECIPIENT_LIST))
    email_response = global_util.ses_client.send_templated_email(
        Source=global_util.EmailSendingFrom,
        Destination={
            'ToAddresses': RECIPIENT_LIST,
            'CcAddresses': CC_RECIPIENT_LIST
        },
        Template=message_props['template_name'],
        TemplateData=message_props['template_data']
        # TemplateData='{ \"REPLACEMENT_TAG_NAME\":\"REPLACEMENT_VALUE\" }'
    )

    print('email response: ', email_response)
    return email_response


def send_custom_email(message_props):
    RECIPIENT_LIST = [email.strip() for email in message_props['target'].split(',')]
    CC_RECIPIENT_LIST = [email.strip() for email in message_props.get('cc_target', '').split(',')]
    CC_RECIPIENT_LIST = list(filter(None, CC_RECIPIENT_LIST))
    SUBJECT = message_props['email_subject']
    BODY_TEXT = message_props['email_body_text']
    BODY_HTML = message_props['email_body_html']
    CHARSET = "UTF-8"

    email_response = global_util.ses_client.send_email(
        Destination={
            'ToAddresses': RECIPIENT_LIST,
            'CcAddresses': CC_RECIPIENT_LIST
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
                'Text': {
                    'Charset': CHARSET,
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
        Source=global_util.EmailSendingFrom
    )
    print('email response: ', email_response)
    return email_response



def parse_message_properties(message):
    props = {}
    for attr, val in message['messageAttributes'].items():
        props[attr] = val['stringValue']

    return props


def delete_sqs_message(message):
    delete_response = global_util.sqs_client.delete_message(
        QueueUrl=global_util.sqs_queue_url,
        ReceiptHandle=message['receiptHandle']
    )
    print('delete response: ', delete_response)