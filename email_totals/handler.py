# Monthly Cost Reporting using Lambda function

import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import synapseclient as syn
from botocore.exceptions import ClientError


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


# Create Cost Explorer service client using saved credentials
ce_client = boto3.client('ce')

# Create a new SES client
ses_client = boto3.client('ses')

# Name of the Cost Category containing email addresses
email_category = 'Owner Email'

# For identifying Sage users
sagebase_email = '@sagebase.org'
sagebio_email = '@sagebionetworks.org'
synapse_email = '@synapse.org'
synapse_team_sage = '273957'

# Create a Synapse client
syn_client = syn.Synapse(cache_root_dir='/tmp/synapse')

#--------------------------------------------------------------------------------------------------
# Reporting periods

# This will run at the beginning of the month, looking at the previous month
# and comparing change to the month before that.

# The Start date is inclusive, and the End date is exclusive

today = datetime.now()

target_month = {}
compare_month = {}

# Special-case the two cases where we cross year boundaries
if today.month == 1:
    # in Jan, look at Dec and Nov of last year
    target_month['Start'] = f'{today.year - 1}-12-01'
    target_month['End'] = f'{today.year}-01-01'

    compare_month['Start'] = f'{today.year - 1}-11-01'
    compare_month['End'] = f'{today.year - 1}-12-01'

elif today.month == 2:
    # in Feb, look at Jan of this year and Dec of last year
    target_month['Start'] = f'{today.year}-01-01'
    target_month['End'] = f'{today.year}-02-01'

    compare_month['Start'] = f'{today.year - 1}-12-01'
    compare_month['End'] = f'{today.year}-01-01'

else:
    # no year boundary, look at the previous two months
    target_month['Start'] = f'{today.year}-{(today.month - 2):02}-01'
    target_month['End'] = f'{today.year}-{(today.month - 1):02}-01'

    compare_month['Start'] = f'{today.year}-{(today.month - 3):02}-01'
    compare_month['End'] = f'{today.year}-{(today.month - 2):02}-01'

LOG.info(f"Target month: {target_month}")
LOG.info(f"Compare month: {compare_month}")


# get list of synapse users in team Sage

def get_team_sage_emails():
    '''
    Get a list of Team Sage emails from Synapse
    '''

    team_sage = []

    syn_team = syn_client.getTeam(synapse_team_sage)
    syn_members = syn_client.getTeamMembers(syn_team)
    for m in syn_members:
        email = m['member']['userName'] + synapse_email
        team_sage.append(email)

    return team_sage


# Get cost information

def get_ce_costinfo(period):
    '''
    Get email cost category information for the given time period
    '''

    # Retrieve cost and usage metrics for specified account
    response = ce_client.get_cost_and_usage(
        TimePeriod=period,
        Granularity='MONTHLY',
        Metrics=[
            'UnblendedCost',
        ],
        GroupBy=[{
            'Type': 'COST_CATEGORY',
            'Key': email_category,
        }],
    )

    return response['ResultsByTime']


def get_email_totals(costinfo):
    '''
    Transform cost category information into a simple dictionary of user totals
    '''

    all_costs = {}
    for result in costinfo:
        for group in result['Groups']:
            amount = float(group['Metrics']['UnblendedCost']['Amount'])

            if len(group['Keys']) == 1:
                # The key has the format "<category name>$<category value>"
                # so everything after the first '$' will be the email address
                long_key = group['Keys'][0]
                short_key = long_key.split('$', maxsplit=1)[1]

                if short_key in all_costs:
                    all_costs[short_key] += amount
                else:
                    all_costs[short_key] = amount
            else:
                raise ValueError(f"Too many keys: {group['Keys']}")
    return all_costs


def filter_email_list(all_totals, team_sage):
    '''
    Remove external and invalid emails from the dictionary
     * Don't send emails for totals less than a specified minimum
     * Don't send emails to synapse users that are not members of team Sage
     * Optionally only send emails to an approved list of recipients (for testing)
    '''

    report_dict = {}

    # get the minimum user total for sending an email
    min_value = float(os.environ['MINIMUM'])

    # get the list of approved recipients from an environment variable
    restrict_to = os.environ['APPROVED'].split(',')

    # if this environment variable is set, only send emails to recipients
    # listed as approved recipients, otherwise send all valid emails
    if os.environ['RESTRICT'] == 'True':
        restrict_send = True
        LOG.warning(f'Only sending emails to: {restrict_to}')
    else:
        restrict_send = False

    # loop over all our totals
    for k, v in all_totals.items():
        if v < min_value:
            LOG.warning(f"Skipping entry less than ${min_value}: {k} (${v})")

        elif restrict_send:
            if k in restrict_to:
                report_dict[k] = v
            else:
                LOG.warning(f"Restricting email: {k} (${v})")

        else:
            if k.endswith(sagebase_email) or k.endswith(sagebio_email):
                report_dict[k] = v

            elif k.endswith(synapse_email):
                if k in team_sage:
                    report_dict[k] = v
                else:
                    LOG.warning(f"Skipping external synapse user: {k} (${v})")

            else:
                LOG.warning(f"Skipping invalid email: {k} (${v})")

    return report_dict


#--------------------------------------------------------------------------------------------------
# Compile HTML for E-mail Body

def create_and_send_emails(target_totals, compare_totals):
    '''
    Build an HTML email from a string template and give it to our SES client
    '''

    html_title = '<h2>AWS Monthly Cost Report Summary</h2><br/>'

    def _build_email(target_total, previous_total):
        '''
        The actual string template for the email
        '''

        if previous_total:
            pct_change = (target_total / previous_total) - 1
        else:
            pct_change = 1

        return ('You are receiving this email because you have been tagged as a '
                f'resource owner in AWS. Your tagged resources total ${target_total:.2f} '
                f'for the past month ({pct_change:.2%} change from the month prior). '
                'You can use AWS Cost Explorer to analyze those expenses: '
                '<a href="https://sagebionetworks.jira.com/wiki/spaces/IT/pages/2756935685/Using+AWS+Cost+Explorer">'
                'Using AWS Cost Explorer</a>')


    for email, total in target_totals.items():
        LOG.debug(f'Processing email for {email} (${total})')

        compare_total = None
        if email in compare_totals:
            compare_total = compare_totals[email]

        email_body = html_title + _build_email(total, compare_total)

        send_report_email(email, email_body)


#--------------------------------------------------------------------------------------------------
# Compile and send HTML E-mail

def send_report_email(recipient, body_html):

    sender = os.environ['SENDER']
    subject = "AWS Monthly Cost Report for Selected Accounts"

    # The email body for recipients with non-HTML email clients.
    body_text = ("Amazon SES\r\n"
                "An HTML email was sent to this address."
                )

    # The character encoding for the email.
    charset = "UTF-8"

    # Try to send the email.
    try:
        #Provide the contents of the email.
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


#--------------------------------------------------------------------------------------------------
# Lambda Handler

def lambda_handler(context=None, event=None):
    '''
    Entry point

    Analyze per-user totals with month-over-month change, and send a brief email
    '''

    # get team sage from synapse
    sage_emails = get_team_sage_emails()
    LOG.debug(f"Team Sage: {sage_emails}")

    # get target month data from ce
    target_info = get_ce_costinfo(target_month)
    LOG.debug(f"Target month info: {target_info}")

    # get compare month data from ce
    compare_info = get_ce_costinfo(compare_month)
    LOG.debug(f"Compare month info: {compare_info}")

    # transform data into convenient format
    all_target_totals = get_email_totals(target_info)
    all_compare_totals = get_email_totals(compare_info)

    # filter out external users and miniscule totals
    sage_target_totals = filter_email_list(all_target_totals, sage_emails)
    sage_compare_totals = filter_email_list(all_compare_totals, sage_emails)

    # TODO: process account owner tags and amend owner totals

    # send user emails
    create_and_send_emails(sage_target_totals, sage_compare_totals)

    # TODO: also send cost center totals to PIs
