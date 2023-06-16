# Monthly Cost Reporting using Lambda function

import json
import logging
import os
import time
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

# 'Other' value used in CostCenter tag
cost_center_other = 'Other / 000001'

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

def get_reporting_periods(today):
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
        target_month['Start'] = f'{today.year}-{(today.month - 1):02}-01'
        target_month['End'] = f'{today.year}-{(today.month):02}-01'

        compare_month['Start'] = f'{today.year}-{(today.month - 2):02}-01'
        compare_month['End'] = f'{today.year}-{(today.month - 1):02}-01'

    LOG.info(f"Target month: {target_month}")
    LOG.info(f"Compare month: {compare_month}")

    return target_month, compare_month


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


def get_ce_email_category(period):
    '''
    Get cost category information grouped by owner email and account
    '''

    response = ce_client.get_cost_and_usage(
        TimePeriod=period,
        Granularity='MONTHLY',
        Metrics=[
            'UnblendedCost',
        ],
        GroupBy=[{
            'Type': 'COST_CATEGORY',
            'Key': email_category,
        },{
            'Type': 'DIMENSION',
            'Key': 'LINKED_ACCOUNT',
        }],
    )

    return response['ResultsByTime']


def get_summary_by_email(costinfo):
    '''
    Transform cost category information into a useful dictionary of user totals per account

    Output schema:

    ```
    user1@sagebase.org:
        total: 100.0
        account_totals:
            111122223333: 10.0
            444455556666: 90.0
    user2@synapse.org: ...
    ```

    '''

    all_costs = {}
    for result in costinfo:
        for group in result['Groups']:
            amount = float(group['Metrics']['UnblendedCost']['Amount'])

            if len(group['Keys']) == 2:
                # Keys preserve the order defined in the GroupBy parameter

                # The category key has the format "<category name>$<category value>"
                # so everything after the first '$' will be the email address
                email = group['Keys'][0].split('$', maxsplit=1)[1]

                account_id = group['Keys'][1]

                if email not in all_costs:
                    all_costs[email] = {}
                    all_costs[email]['total'] = 0.0
                    all_costs[email]['account_totals'] = {}

                all_costs[email]['account_totals'][account_id] = amount
                all_costs[email]['total'] += amount

            else:
                raise ValueError(f"Invalid number of keys: {group['Keys']}")

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

    # get the recipient skiplist from an environment variable
    skiplist = os.environ['SKIPLIST'].split(',')

    # if this environment variable is set, only send emails to recipients
    # listed as approved recipients, otherwise send all valid emails
    if os.environ['RESTRICT'] == 'True':
        restrict_send = True
        LOG.warning(f'Only sending emails to: {restrict_to}')
    else:
        restrict_send = False

    # loop over all our totals
    for k, v in all_totals.items():
        total = v['total']
        if total < min_value:
            LOG.info(f"Skipping entry less than ${min_value}: {k} (${total})")

        elif k in skiplist:
            LOG.info(f"Recipient in skiplist: {k} (${total})")

        elif restrict_send:
            if k in restrict_to:
                report_dict[k] = v
            else:
                LOG.info(f"NOT sending email: {k} (${total})")

        else:
            if k.endswith(sagebase_email) or k.endswith(sagebio_email):
                report_dict[k] = v

            elif k.endswith(synapse_email):
                if k in team_sage:
                    report_dict[k] = v
                else:
                    LOG.info(f"Skipping external synapse user: {k} (${total})")

            else:
                LOG.warning(f"Skipping invalid email: {k} (${total})")

    return report_dict


def add_ce_missing_tag(email_summary, today):
    '''
    For each email given, query CE for resources missing a needed
    CostCenterOther tag and owned by the given email, and amend
    the email_summary to include the list of resources found.

    The function `get_cost_and_usage_with_resources` can only look back at most
    14 days, so we always look at the previous week.

    The resulting output schema:
    ```
    user1@sagebase.org:
        total: 100.0
        account_totals:
            111122223333: 10.0
            444455556666: 90.0
    user2@synapse.org:
        total: 20.0
        account_totals:
            111122223333: 20.0
        missing_other_tag:
            111122223333: [ i-0abcdefg ]
    ```
    '''

    _last_week = today - timedelta(weeks=1)
    last_week = {}
    last_week['Start'] = _last_week.strftime('%Y-%m-%d')
    last_week['End'] = today.strftime('%Y-%m-%d')

    LOG.debug(f'Last week: {last_week}')

    for email in email_summary:
        ce_info = get_ce_missing_tag_for_email(last_week, email)
        LOG.debug(f'Last week: {ce_info}')

        # parse ce_info and inject back into email_summary
        for i in ce_info:
            _total = i['Total']
            _groups = i['Groups']

            if 'UnblendedCost' in _total:  # only set if not groups found
                if float(_total['UnblendedCost']['Amount']) != 0:
                    LOG.error(f"Non-zero total: {_total}")
                else:
                    LOG.debug(f"No missing CostCenterOther tags for {email}")

            else:
                for group in _groups:
                    _amount = float(group['Metrics']['UnblendedCost']['Amount'])
                    # Keys preserve the order defined in the GroupBy parameter
                    _account = group['Keys'][0]
                    _resource = group['Keys'][1]

                    # not all resources show an ID in cost explorer
                    # don't report on resources without an ID
                    if _resource == 'NoResourceId':
                        continue

                    if 'missing_other_tag' not in email_summary[email]:
                        email_summary[email]['missing_other_tag'] = {}

                    if _account not in email_summary[email]['missing_other_tag']:
                        email_summary[email]['missing_other_tag'][_account] = []

                    email_summary[email]['missing_other_tag'][_account].append(_resource)

    return email_summary


def get_ce_missing_tag_for_email(period, email):
    '''
    Get cost category information for resources missing a CostCenterOther tag,
    filtered by owner email and grouped by account
    '''

    # Retrieve cost and usage metrics for specified account
    response = ce_client.get_cost_and_usage_with_resources(
        TimePeriod=period,
        Granularity='MONTHLY',
        Metrics=[
            'UnblendedCost',
        ],
        Filter={"And": [
            {'CostCategories': {
                'Key': email_category,
                'Values': [ email, ],
                'MatchOptions': [ 'EQUALS', ],
                }
            },{'Tags': {
                'Key': 'CostCenter',
                'Values': [ cost_center_other, ],
                'MatchOptions': [ 'EQUALS', ],
                }
            },{'Tags': {
                'Key': 'CostCenterOther',
                'MatchOptions': [ 'ABSENT', ],
                }
            }
        ]},
        GroupBy=[{
            'Type': 'DIMENSION',
            'Key': 'LINKED_ACCOUNT',
        },{
            'Type': 'DIMENSION',
            'Key': 'RESOURCE_ID',
        }],
    )

    # minimal rate limiting
    # sleep for 10ms after calling get_cost_and_usage_with_resources
    time.sleep(0.01)

    return response['ResultsByTime']


#--------------------------------------------------------------------------------------------------
# Compile HTML for E-mail Body

def create_and_send_emails(target_summary, compare_summary):
    '''
    Build an HTML email from a string template and give it to our SES client
    '''

    def _build_total_summary(target_total, previous_total, html=True):
        '''
        Build a summary paragraph with a user total, with percentage
        change from the previous month if applicable.
        '''

        summary = ('You are receiving this email because you have been '
                'tagged as a resource owner in AWS.')

        summary += (f' Your tagged resources total ${target_total:.2f} for the '
                'past month')

        if previous_total:
            pct_change = (target_total / previous_total) - 1
            summary += (f' ({pct_change:.2%} change from the month prior)')

        summary += '.'

        if html:
            summary = f'<p>{summary}</p>'

        return summary

    def _build_missing_table(account_map, html=True):
        '''
        Build an HTML table of resources in need of a CostCenterOther tag.
        '''

        table = ''
        description = ("The following resources have a 'CostCenter' tag "
                "value of 'Other / 000001' but do not have the required "
                "'CostCenterOther' tag. If you need assistance adding the "
                "required tag, please contact Sage IT.")

        if html:
            table = f'<p>{description}</p>'

            # begin table element
            table += "<table border=1 style='border-collapse: collapse;'>"

            # header row
            table += '<tr><th>Account</th><th>Resources</th></tr>'

            # add a row for each account
            for account in account_map:
                table += f'<tr><td>{account}</td><td>{account_map[account]}</td></tr>'

            # close table element
            table += '</table>'

        else:
            table = description + '\n'

            for account in account_map:
                table += f'Account: {account}, Resources: {account_map[account]}\n'

        return table

    _title = 'AWS Monthly Cost Report Summary'
    text_title = f'{_title}\n\n'
    html_title = f'<h2>{_title}</h2><br/>'

    docs_url = 'https://sagebionetworks.jira.com/wiki/spaces/IT/pages/2756935685/Using+AWS+Cost+Explorer'
    docs_title = 'Using AWS Cost Explorer'
    docs_prose = 'You can use AWS Cost Explorer to analyze those expenses'

    html_docs = f'<br/>{docs_prose}: <a href="{docs_url}">{docs_title}</a>'
    text_docs = f' {docs_prose}. See "{docs_title}" at: {docs_url}'

    for email, info in target_summary.items():
        LOG.debug(f'Processing email for {email} ({info})')

        missing = None
        if 'missing_other_tag' in info:
            missing = info['missing_other_tag']

        total = info['total']
        compare_total = None
        if email in compare_summary:
            compare_total = compare_summary[email]['total']

        # start with our title
        body_text = text_title
        body_html = html_title

        # add an intro summary
        body_text += _build_total_summary(total, compare_total, html=False)
        body_html += _build_total_summary(total, compare_total, html=True)

        # if any resources need CostCenterOther tags, list them
        if missing:
            body_text += _build_missing_table(missing, html=False)
            body_html += _build_missing_table(missing, html=True)

        # end with a link to the docs
        body_text += text_docs
        body_html += html_docs

        # send the email
        LOG.debug(body_text)
        LOG.debug(body_html)
        send_report_email(email, body_text, body_html)


#--------------------------------------------------------------------------------------------------
# Compile and send HTML E-mail

def send_report_email(recipient, body_text, body_html):

    sender = os.environ['SENDER']
    subject = "AWS Monthly Cost Report"

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
            ReturnPath=sender,
        )

        # minimal rate limiting
        # sleep for 10ms after calling send_email
        time.sleep(0.01)

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

    # get search periods
    now = datetime.now()
    target_month, compare_month = get_reporting_periods(now)

    # get target month data from ce
    target_info = get_ce_email_category(target_month)
    LOG.debug(f"Target month info: {target_info}")

    # get compare month data from ce
    compare_info = get_ce_email_category(compare_month)
    LOG.debug(f"Compare month info: {compare_info}")

    # TODO get account_id:account_name mapping from ce response

    # transform data into convenient format
    all_target_summary = get_summary_by_email(target_info)
    all_compare_summary = get_summary_by_email(compare_info)

    # filter out external users and miniscule totals
    sage_target_summary = filter_email_list(all_target_summary, sage_emails)
    sage_compare_summary = filter_email_list(all_compare_summary, sage_emails)

    # inject data about missing CostCenterOther tags
    # no need to do this for the compare data
    sage_target_summary = add_ce_missing_tag(sage_target_summary, now)

    # TODO: process account owner tags and amend summary

    # send user emails
    create_and_send_emails(sage_target_summary, sage_compare_summary)

    # TODO: also send cost center totals to PIs
