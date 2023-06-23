import logging
import os

import boto3
from botocore.exceptions import ClientError

# Create organizations client for getting account tags
org_client = boto3.client('organizations')


def get_account_owners():
    """
    Get account owner tags from organizations client and return a mapping
    of owners to accounts:
    ```
    owner1@exapmle.com:
        - 111122223333
        - 222233334444
    owner2@example.com:
        - 333344445555
    ```
    """

    # TODO: call org_client.list_accounts() and build the response dict
    # For now return some dummy data
    output = {
        'user@example.com': ['111122223333', ]
    }
    return output
