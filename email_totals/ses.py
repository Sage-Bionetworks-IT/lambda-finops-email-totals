import logging
import os

import boto3
from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

ses_client = boto3.client('ses')


def valid_recipient(email, team_sage):
    """
    Determine if a given recipient should receive an email
    """

    restrict = os.environ['RESTRICT']
    approved = os.environ['APPROVED'].split(',')
    skiplist = os.environ['SKIPLIST'].split(',')

    # TODO: check recipient email against skiplist and approved list
    # then check the domain for a sage domain, and check team sage for
    # a synapse domain

    return True


def build_email_body(summary):
    """
    Generate an HTML and a plain-text message body for a summary entry
    """

    # TODO: process a block of our summary data
    html = "html"
    text = "text"

    LOG.debug(html)
    LOG.debug(text)

    return html, text


def send_report_email(recipient, body_html, body_text):
    """
    Send e-mail through SES
    """

    sender = os.environ['SENDER']
    subject = "AWS Monthly Cost Report"

    # Python3 uses UTF-8
    charset = "UTF-8"

    # Try to send the email.
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject,
                },
            },
            Source=sender,
        )

    # Display an error if something goes wrong.
    except ClientError as e:
        LOG.exception(e)
    else:
        LOG.info(f"Email sent! Message ID: {response['MessageId']}")
