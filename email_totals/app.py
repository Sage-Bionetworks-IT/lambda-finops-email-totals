from email_totals import ce, org, ses

import logging
import os
from datetime import datetime


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def report_periods(today):
    """
    Calculate the time periods for cost explorer.

    This lambda will run at the beginning of the month, looking at the
    previous month and comparing change to the month before that.

    The Start date is inclusive, and the End date is exclusive
    """
    target_month = {}
    compare_month = {}

    # TODO: calculate these values from today

    LOG.info(f"Target month: {target_month}")
    LOG.info(f"Compare month: {compare_month}")

    return target_month, compare_month


def get_team_sage_emails():
    """
    Get a list of Team Sage emails from Synapse
    """

    team_sage = []

    # TODO: interact with Synapse to get the members of Team Sage.
    # For now return an empty list, which will treat all synapse users as external

    return team_sage


def get_resource_totals(target_p, compare_p, minimum):
    """
    Get email cost information from cost explorer for both time periods
    and generate a multi-level dictionary. The top-level key will be the
    email address of the resource owner, the first-level subkey will be the
    literal string 'resources', the second-level subkey will be the account ID,
    and the third-level subkeys will be the literal strings 'total', and
    optionally 'change'; 'total' will map to a float representing the user's
    resource total for this account, and if 'change' is present it will map to a
    float representing percent change from the last month (1.0 is 100% growth).

    Example:
    ```
    email1@example.com:
        resources:
            111122223333:
                total: 10.0
                change: -0.1
    email2@example.com:
        resources:
            222233334444:
                total: 2.1
    ```
    """

    output = {}

    # TODO: call ce.get_ce_email_costs() for each period and build a dict.

    return output


def get_account_totals(target_p, compare_p, minimum):
    """
    Get account cost information from cost explorer for both time periods,
    and also account owner tags from organizations, then generate and return
    a multi-level dictionary. The top-level key will be the email address of
    the account owner, the first-level subkey will be the literal string
    'accounts', the second-level subkey will be the account ID, and the third-
    level subkeys will be the literal string 'total', and optionally 'change';
    'total' will map to a float representing the account total, and if 'change'
    is present it will map to a float representing percent change from the last
    month (1.0 is 100% growth).

    Example:
    ```
    email1@example.com:
        accounts:
            111122223333:
                total: 100.0
                change: 0.5
    email2@example.com:
        accounts:
            222233334444:
                total: 10
    ```
    """

    output = {}

    # TODO: call ce.get_ce_account_costs() and org.get_account_owners()
    # and build our output dict.

    return output

def get_missing_other_tags(period, owner):
    """
    Query cost explorer for resource usage by the given resource owner,
    filtering for resources missing a required CostCenterOther tag,
    and grouped by account id, then generate a dictionary mapping an
    account ID to a list of resource IDs.

    Example:
    ```
    111122223333:
      - i-0abcdefg
      - i-1hijkmln
    ```
    """

    output = {}

    # TODO: call ce.get_ce_missing_tag_for_email() and build an output dict

    return output


def build_summary(target_period, compare_period, team_sage):
    """
    Build a convenient data structure representing the data we want to
    include in each email.

    The resource and account totals are separate subkeys because our
    owner cost category in cost explorer doesn't include account-based rules.

    Example output
    ```
    user1@example.com:
        resources:
            111122223333:
                total: 10.0
                change: 1.2
            222233334444:
                total: 0.1
                change: 0.0
        missing_other_tag:
            111122223333:
              - i-0abcdefg
        accounts:
            333344445555:
                total: 20.0
                change: -2.1
    user2@example.com:
        ...
    ```
    """

    summary = {}
    min_value = float(os.environ['MINIMUM'])

    # Generate 'resources' subkeys and merge them in
    resources = get_resource_totals(target_period, compare_period, min_value)
    for owner in resources:
        if owner not in summary:
            summary[owner] = {}
        summary[owner]['resources'] = resources[owner]['resources']

    LOG.debug(summary)

    # Generate 'accounts' subkeys and merge them in
    accounts = get_account_totals(target_period, compare_period, min_value)
    for owner in accounts:
        if owner not in summary:
            summary[owner] = {}
        summary[owner]['accounts'] = accounts[owner]['accounts']

    LOG.debug(summary)

    # Filter valid recipients and amend missing tag info
    filtered = {}
    for recipient in summary:
        if ses.valid_recipient(recipient, team_sage):
            filtered[recipient] = summary[recipient]

            # Amend summary with missing CostCenterOther tags
            # Do this after filtering to minimize CE calls
            missing_tags = get_missing_other_tags(target_period, recipient)
            if missing_tags:
                filtered[recipient]['missing_other_tag'] = missing_tags

    LOG.debug(filtered)
    return filtered


def lambda_handler(event, context):
    """
    Entry point

    Send monthly email reports to users with (1) tagged resource totals for the month,
    (2) tagged account totals for the month, and (3) resources missing a required
    CostCenterOther tag. Include month-over-month changes for both resource and
    account totals.
    """

    # Calculate the reporting periods for this run
    now = datetime.now()
    target_month, compare_month = report_periods(now)

    # Get Team Sage from Synapse
    team_sage = get_team_sage_emails()

    # Build email summary
    email_summary = build_summary(target_month, compare_month, team_sage)

    # Create and send email reports from summary
    for email in email_summary:
        html, text = ses.build_email_body(email_summary[email])
        ses.send_report_email(email, html, text)
