import logging

import boto3


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

ce_client = boto3.client('ce')


def get_ce_email_costs(period):
    """
    Get cost information grouped by owner email then account
    (i.e. email totals for each account)
    """

    # TODO: call ce_client.get_cost_and_usage() and return response
    return {}


def get_ce_account_costs(period):
    """
    Get cost information grouped by account (i.e. account totals)
    """

    # TODO: call ce_client.get_cost_and_usage() and return response
    return {}


def get_ce_missing_tag_for_email(period, email):
    """
    Get cost category information for a given owner email and grouped by account,
    filtered for resources tagged with CostCenter=Other but no CostCenterOther tag.
    """

    # TODO: call ce_client.get_cost_and_usage_with_resources() and return response
    return {}
