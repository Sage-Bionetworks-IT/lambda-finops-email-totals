import os

import pytest


# This needs to be set when the ses module is loaded,
# but its value is not used when running tests
os.environ['AWS_DEFAULT_REGION'] = 'test-region'
from email_totals import ses


# Constants used by fixtures

ce_period = {
    'Start': '2023-01-01',
    'End': '2023-02-01'
}

user1 = 'user1' + ses.synapse_email
user2 = 'user2' + ses.synapse_email
user3 = 'user3' + ses.sagebio_email
user4 = 'user4' + ses.sagebase_email
uncategorized = ''

account1_id = '111122223333'
account2_id = '222233334444'
account3_id = '333344445555'
account4_id = '444455556666'

account1_name = 'mock-account-shared'
account2_name = 'mock-account-ignored'
account3_name = 'mock-account-user3'
account4_name = 'mock-account-user4'

account1_user1_total1 = 30.0
account1_user1_total2 = 20.0
account1_user1_change = 0.5

account1_user2_total = 32.10
account1_user2_missing = ['i-0abcdefg', 'i-1hijklmnop']

account1_unowned_total = 999
account1_total = 9999

account2_total = 0.01

account3_user3_total1 = 100.0
account3_user3_total2 = 100
account3_user3_change = 0
account3_user3_missing_ce = ['i-0hijklmnop', 'NoResourceId']
account3_user3_missing_app = ['i-0hijklmnop']

account4_user4_total = 10


# App fixtures

@pytest.fixture()
def mock_app_resource_dict():
    response = {
        user1: {
            'resources': {
                account1_id: {
                    'total': account1_user1_total1,
                    'change': account1_user1_change,
                }
            }
        },
        user2: {
            'resources': {
                account1_id: {
                    'total': account1_user2_total,
                }
            }
        },
        user4: {
            'resources': {
                account4_id: {
                    'total': account4_user4_total,
                }
            }
        },
        uncategorized: {
            'resources': {
                account1_id: {
                    'total': account1_unowned_total,
                    'change': 0.0,
                },
                account3_id: {
                    'total': account3_user3_total1,
                    'change': account3_user3_change,
                }
            }
        }
    }
    return response


@pytest.fixture()
def mock_app_account_dict():
    response = {
        user3: {
            'accounts': {
                account3_id: {
                    'total': account3_user3_total1,
                    'change': account3_user3_change,
                }
            }
        },
        user4: {
            'accounts': {
                account4_id: {
                    'total': account4_user4_total,
                },
            }
        }
    }
    return response


@pytest.fixture()
def mock_app_account_names():
    response = {
        account1_id: account1_name,
        account2_id: account2_name,
        account3_id: account3_name,
        account4_id: account4_name,
    }
    return response


@pytest.fixture()
def mock_app_missing_tags_user2():
    response = {
        account1_id: account1_user2_missing
    }
    return response


@pytest.fixture()
def mock_app_missing_tags_user3():
    response = {
        account3_id: account3_user3_missing_app
    }
    return response


@pytest.fixture()
def mock_app_unowned():
    response = {
        account1_id: {
            'total': account1_unowned_total,
            'change': 0.0
        }
    }
    return response


@pytest.fixture()
def mock_app_per_user():
    response = {
        user1: {
            'resources': {
                account1_id: {
                    'total': account1_user1_total1,
                    'change': account1_user1_change
                }
            },
        },
        user2: {
            'resources': {
                account1_id: {'total': account1_user2_total}
            },
            'missing_other_tag': {
                account1_id: account1_user2_missing
            }
        },
        user3: {
            'accounts': {
                account3_id: {'total': account3_user3_total1,
                              'change': account3_user3_change}
            },
            'missing_other_tag': {
                account3_id: account3_user3_missing_app
            }
        },
        user4: {
            'resources': {
                account4_id: {'total': account4_user4_total}
            },
            'accounts': {
                account4_id: {'total': account4_user4_total}
            },

        }
    }
    return response


@pytest.fixture()
def mock_app_build_summary(mock_app_account_names,
                           mock_app_per_user,
                           mock_app_unowned):
    response = {
        'account_names': mock_app_account_names,
        'per_user_summary': mock_app_per_user,
        'unowned': mock_app_unowned
    }
    return response


# CE fixtures

def mock_ce_account_usage(account_totals):
    groups = []

    for account in account_totals:
        group = {
            'Keys': [account, ],
            'Metrics': {
                'UnblendedCost': {
                    'Amount': account_totals[account]
                }
            }
        }
        groups.append(group)

    response = {
        'GroupDefinitions': [
            {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'},
        ],
        'ResultsByTime': [
            {
                'TimePeriod': ce_period,
                'Total': {},
                'Groups': groups,
                'Estimated': True
            }
        ],
        'DimensionValueAttributes': [
            {
                'Value': account1_id,
                'Attributes': {
                    'description': account1_name
                }
            },
            {
                'Value': account2_id,
                'Attributes': {'description': account2_name}
            },
            {
                'Value': account3_id,
                'Attributes': {'description': account3_name}
            },
            {
                'Value': account4_id,
                'Attributes': {'description': account4_name}
            },

        ],
    }
    return response


@pytest.fixture()
def mock_ce_account_target_data():
    account_totals = {
        account1_id: str(account1_total),
        account2_id: str(account2_total),
        account3_id: str(account3_user3_total1),
        account4_id: str(account4_user4_total),
    }
    return mock_ce_account_usage(account_totals)


@pytest.fixture()
def mock_ce_account_compare_data():
    account_totals = {
        account1_id: str(account1_total),
        account2_id: str(account2_total),
        account3_id: str(account3_user3_total2),
    }
    return mock_ce_account_usage(account_totals)


def mock_ce_email_usage(user_totals):
    groups = []

    for user, account_id, amount in user_totals:
        group = {
            'Keys': [
                f"Owner Email${user}",
                account_id
            ],
            'Metrics': {
                'UnblendedCost': {
                    'Amount': amount
                }
            }
        }
        groups.append(group)

    response = {
        'GroupDefinitions': [
            {'Type': 'COST_CATEGORY', 'Key': 'Owner Email'},
            {'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'},
        ],
        'ResultsByTime': [
            {
                'TimePeriod': ce_period,
                'Total': {},
                'Groups': groups,
                'Estimated': False
            }
        ],
    }
    return response


@pytest.fixture()
def mock_ce_email_target_data():
    target_totals = {
        (user1, account1_id, str(account1_user1_total1)),
        (user2, account1_id, str(account1_user2_total - 5)),
        (user2.upper(), account1_id, "5.0"),
        (user4, account4_id, str(account4_user4_total)),
        (uncategorized, account1_id, str(account1_unowned_total)),
        (uncategorized, account3_id, str(account3_user3_total1)),

    }
    return mock_ce_email_usage(target_totals)


@pytest.fixture()
def mock_ce_email_compare_data():
    compare_totals = {
        (user1, account1_id, str(account1_user1_total2)),
        (uncategorized, account1_id, str(account1_unowned_total)),
        (uncategorized, account3_id, str(account3_user3_total2)),
    }
    return mock_ce_email_usage(compare_totals)


def mock_ce_missing_tag_response(account_id, user_missing):
    groups = []

    for r in user_missing:
        group = {
            'Keys': [account_id, r],
            'Metrics': {}
        }
        groups.append(group)

    response = {
        'ResultsByTime': [
            {
                'TimePeriod': ce_period,
                'Total': {},
                'Groups': groups,
            }
        ]
    }
    return response


@pytest.fixture()
def mock_ce_missing_tags_user2():
    return mock_ce_missing_tag_response(account1_id,
                                        account1_user2_missing)


@pytest.fixture()
def mock_ce_missing_tags_user3():
    return mock_ce_missing_tag_response(account3_id,
                                        account3_user3_missing_ce)


@pytest.fixture()
def mock_ce_period():
    return ce_period


# Organizations fixtures

@pytest.fixture()
def mock_org_accounts():
    response = {
        'Accounts': [
            {
                'Id': account1_id,
                'Name': account1_name,
            }, {
                'Id': account2_id,
                'Name': account2_name,
            }, {
                'Id': account3_id,
                'Name': account3_name,
            }, {
                'Id': account4_id,
                'Name': account4_name,
            }
        ]
    }
    return response


@pytest.fixture()
def mock_org_account_owners():
    response = {
        user3: [account3_id, ],
        user4: [account4_id, ]
    }
    return response


@pytest.fixture()
def mock_org_account_no_tags():
    response = {
        'Tags': []
    }
    return response


@pytest.fixture()
def mock_org_account_tags_user3():
    response = {
        'Tags': [
            {
                'Key': 'AccountOwner',
                'Value': user3,
            }
        ]
    }
    return response


@pytest.fixture()
def mock_org_account_tags_user4():
    response = {
        'Tags': [
            {
                'Key': 'AccountOwner',
                'Value': user4,
            }
        ]
    }
    return response


# SES fixtures

@pytest.fixture()
def mock_ses_response():
    response = {'MessageId': 'testId'}
    return response


# Synapse fixtures

@pytest.fixture()
def mock_syn_team():
    response = {
        'name': 'test team',
        'id': '123',
    }
    return response


@pytest.fixture()
def mock_syn_members():
    response = [
        {
            'teamId': '123',
            'member': {
                'ownerId': '456',
                'userName': 'user1',
            }
        }, {
            'teamId': '123',
            'member': {
                'ownerId': '789',
                'userName': 'user2',
            }
        }

    ]
    return response


@pytest.fixture()
def mock_team_sage():
    response = [
        user1,
        user2,
    ]

    return response


# User fixtures

def mock_user(name):
    return name


@pytest.fixture()
def mock_user1():
    return mock_user(user1)


@pytest.fixture()
def mock_user2():
    return mock_user(user2)


@pytest.fixture()
def mock_user3():
    return mock_user(user3)


@pytest.fixture()
def mock_user4():
    return mock_user(user4)
