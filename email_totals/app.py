import logging
import os
from datetime import datetime

from email_totals import ce, org, synapse, ses

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
        target_month['End'] = f'{today.year}-{today.month:02}-01'

        compare_month['Start'] = f'{today.year}-{(today.month - 2):02}-01'
        compare_month['End'] = f'{today.year}-{(today.month - 1):02}-01'

    LOG.info(f"Target month: {target_month}")
    LOG.info(f"Compare month: {compare_month}")

    return target_month, compare_month


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

    def _build_dict(results_by_time, compare=None):
        """
        Build our simple data structure from the cost explorer results,
        optionally adding a percent change against compare data (if present).
        """
        resources = {}
        for result in results_by_time:
            for group in result['Groups']:
                amount = float(group['Metrics']['UnblendedCost']['Amount'])

                # Keys preserve the order defined in the GroupBy parameter from
                # the call to get_cost_and_usage().
                if len(group['Keys']) != 2:
                    LOG.error(f"Unexpected grouping: {group['Keys']}")
                    continue

                # The category key has the format "<category name>$<category value>"
                # so everything after the first '$' will be the email address
                # A special case of "<category name>$" is used for uncategorized costs
                email = group['Keys'][0].split('$', maxsplit=1)[1]

                account_id = group['Keys'][1]

                # Skip insignificant totals
                if amount < minimum:
                    LOG.info(f"Skipping total less than ${minimum} for "
                             f"{email}: {account_id} ${amount}")
                    continue

                # Add account resource total for resource owner
                if email not in resources:
                    resources[email] = {'resources': {}}
                resources[email]['resources'][account_id] = {'total': amount}

                # If we have a compare dict, calculate a percent change
                if compare and email in compare:
                    _compare = compare[email]['resources']
                    if account_id in _compare:
                        # Calculate percent change from compare month
                        pct = (amount / _compare[account_id]['total']) - 1
                        resources[email]['resources'][account_id]['change'] = pct

        return resources

    # First generate data to compare against
    compare_data = ce.get_ce_email_costs(compare_p)
    compare_dict = _build_dict(compare_data['ResultsByTime'])

    # Then generate data our target data, passing in compare data
    target_data = ce.get_ce_email_costs(target_p)
    target_dict = _build_dict(target_data['ResultsByTime'], compare_dict)

    return target_dict


def get_account_totals(target_p, compare_p, minimum):
    """
    Get account cost information from cost explorer for both time periods,
    and also account owner tags from organizations, then generate and return
    a tuple of two dictionaries.

    The first is a multi-level dictionary where the top-level key will be the
    email address of the account owner, the first-level subkey will be the
    literal string 'accounts', the second-level subkey will be the account ID,
    and the third-level subkeys will be the literal string 'total', and
    optionally 'change'; 'total' will map to a float representing the account
    total, and if 'change' is present it will map to a float representing
    percent change from the last month (1.0 is 100% growth).

    The second is a simple dictionary mapping account IDs to their names.

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

    ```
    111122223333: friendly-name
    222233334444: account-two
    ```
    """

    def _build_result_dict(results_by_time):
        """
        Transform the results from cost explorer into a dictionary of the form:
        ```
        111122223333: 100.0
        222233334444: 10
        ```
        """
        account_totals = {}
        for result in results_by_time:
            for group in result['Groups']:
                amount = float(group['Metrics']['UnblendedCost']['Amount'])

                # Keys preserve the order defined in the GroupBy parameter from
                # the call to get_cost_and_usage().
                if len(group['Keys']) != 1:
                    LOG.error(f"Unexpected grouping: {group['Keys']}")
                    continue

                # Add this account total to our output
                account_id = group['Keys'][0]
                if account_id not in account_totals:
                    account_totals[account_id] = amount
                else:
                    LOG.error(f"Duplicate account total found: {account_id}")

        return account_totals

    def _build_attr_dict(attributes):
        """
        Transform DimensionValueAttributes to a useful dict
        """
        attr_dict = {}

        for item in attributes:
            value = item['Value']
            description = item['Attributes']['description']
            attr_dict[value] = description

        return attr_dict

    output = {}

    compare_ce_data = ce.get_ce_account_costs(compare_p)
    compare_dict = _build_result_dict(compare_ce_data['ResultsByTime'])

    target_ce_data = ce.get_ce_account_costs(target_p)
    target_dict = _build_result_dict(target_ce_data['ResultsByTime'])

    account_names = _build_attr_dict(target_ce_data['DimensionValueAttributes'])
    account_owners = org.get_account_owners()

    # Build an accounts subkey for each account owner
    for owner in account_owners:
        account_dict = {'accounts': {}}

        for account in account_owners[owner]:
            if account not in target_dict:
                # Every account in our organization should be in the dict
                LOG.error(f"No current total for account: {account}")
                continue

            target_total = target_dict[account]

            # Skip insignificant totals
            if target_total < minimum:
                LOG.info(f"Skipping total less than ${minimum} for {owner}: "
                         f"{account} ${target_total}")
                continue

            account_dict['accounts'][account] = {'total': target_total}

            # If we have a compare dict, calculate percent change
            if account in compare_dict:
                compare_total = compare_dict[account]
                pct_change = (target_total / compare_total) - 1
                account_dict['accounts'][account]['change'] = pct_change

        output[owner] = account_dict

    return output, account_names


def get_missing_other_tags(owner):
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

    missing_data = ce.get_ce_missing_tag_for_email(owner)

    for result in missing_data['ResultsByTime']:
        for group in result['Groups']:
            # Keys preserve the order defined in the GroupBy parameter from
            # the call to get_cost_and_usage().
            if len(group['Keys']) != 2:
                LOG.error(f"Unexpected grouping: {group['Keys']}")
                continue

            account_id = group['Keys'][0]
            resource = group['Keys'][1]

            # Create initial list if needed
            if account_id not in output:
                output[account_id] = []

            # Add this resource to the account
            output[account_id].append(resource)
    return output


def build_summary(target_period, compare_period, team_sage):
    """
    Build a convenient data structure representing the recipients and the data
    we want to include in each email.

    The 'resources' subkey will have per-account resource totals for the owner,
    and percent change from the previous month if applicable.

    The 'missing_other_tag' subkey will list owner resources that are missing a
    required 'CostCenterOther' tag.

    Since IT-2369 is blocked, the owner category does not include accounts
    tagged with an account owner. As a workaround, we add an 'accounts' subkey
    with account totals for owned accounts, and build an additional email
    section from it. If IT-2369 is ever implemented, then the owned accounts
    would be included in the 'resources' subkey and the 'accounts' subkey can
    be removed.

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

    data = {}
    min_value = float(os.environ['MINIMUM'])

    # Generate 'resources' subkeys and merge them in
    resources = get_resource_totals(target_period, compare_period, min_value)
    for owner in resources:
        if owner not in data:
            data[owner] = {}
        data[owner]['resources'] = resources[owner]['resources']
    LOG.debug(data)

    # Generate 'accounts' subkeys and merge them in
    accounts_dict, account_names = get_account_totals(target_period,
                                                      compare_period,
                                                      min_value)
    LOG.debug(accounts_dict)
    LOG.debug(account_names)

    for owner in accounts_dict:
        if owner not in data:
            data[owner] = {}
        data[owner]['accounts'] = accounts_dict[owner]['accounts']
    LOG.debug(data)

    # Filter valid recipients and amend missing tag info
    filtered = {}
    for recipient in data:
        if ses.valid_recipient(recipient, team_sage):
            filtered[recipient] = data[recipient]

            # Amend summary with missing CostCenterOther tags
            # Do this after filtering to minimize CE calls
            missing_tags = get_missing_other_tags(recipient)
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
    team_sage = synapse.get_team_sage_members()

    # Build email summary
    email_summary = build_summary(target_month, compare_month, team_sage)

    # Create and send email reports from summary
    for email in email_summary:
        html, text = ses.build_email_body(email_summary[email])
        ses.send_report_email(email, html, text)
