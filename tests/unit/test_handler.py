from email_totals import handler

import json
import os
from datetime import datetime

import boto3
import pytest
from botocore.stub import Stubber


# fixtures for datetime processing around year boundaries

# in december we target nov of this year
# and compare with oct of this year
test_now_dec = '2020-12-02'

expected_target_dec = {
  'Start': '2020-11-01',
  'End': '2020-12-01',
}

expected_compare_dec = {
  'Start': '2020-10-01',
  'End': '2020-11-01',
}

# in january we target dec of last year
# and compare with nov of last year
test_now_jan = '2020-01-02'

expected_target_jan = {
  'Start': '2019-12-01',
  'End': '2020-01-01',
}

expected_compare_jan = {
  'Start': '2019-11-01',
  'End': '2019-12-01',
}

# in february we target jan of this year
# and compare with dec of last year
test_now_feb = '2020-02-02'

expected_target_feb = {
  'Start': '2020-01-01',
  'End': '2020-02-01',
}

expected_compare_feb = {
  'Start': '2019-12-01',
  'End': '2020-01-01',
}

mock_ce_email_category = {
  'GroupDefinitions': [
    {'Type': 'COST_CATEGORY', 'Key': 'Owner Email'},
    {'Type': 'DIMNESION', 'Key': 'LINKED_ACCOUNT'},
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {'Start': '2023-03-01', 'End': '2023-04-01'},
      'Total': {},
      'Groups': [
        {
          'Keys': [
            'Owner Email$',
            '111122223333',
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '48446.9515396549',
              'Unit': 'USD'
            }
          }
        },
        {
          'Keys': ['Owner Email$user1@synapse.org', '111122223333'],
          'Metrics': {'UnblendedCost': {'Amount': '0.30000000264', 'Unit': 'USD'}}
        },{
          'Keys': ['Owner Email$user2@synapse.org', '111122223333'],
          'Metrics': {'UnblendedCost': {'Amount': '3.000000264', 'Unit': 'USD'}}
        },{
          'Keys': ['Owner Email$user3@sagebase.org', '111122223333'],
          'Metrics': {'UnblendedCost': {'Amount': '30.000000264', 'Unit': 'USD'}}
        },
      ],
      'Estimated': False
    }
  ],
  'DimensionValueAttributes': [
    {
      'Value': '111122223333',
      'Attributes': {
        'description': 'test-account-name'
      }
    },
  ],
  'ResponseMetadata': {
    'RequestId': '15f5cdde-0ea0-420f-867a-b862afeca967',
    'HTTPStatusCode': 200,
    'HTTPHeaders': {
      'date': 'Wed, 31 May 2023 20:57:36 GMT',
      'content-type': 'application/x-amz-json-1.1',
      'content-length': '14561',
      'connection': 'keep-alive',
      'x-amzn-requestid': '15f5cdde-0ea0-420f-867a-b862afeca967',
      'cache-control': 'no-cache'
    },
    'RetryAttempts': 0
  }
}

mock_ce_missing_tag = {
  'GroupDefinitions': [
    {'Type': 'DIMNESION', 'Key': 'LINKED_ACCOUNT'},
    {'Type': 'DIMNESION', 'Key': 'RESOURCE_ID'},
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {
        'Start': '2023-06-01T00:00:00Z',
        'End': '2023-07-01T00:00:00Z'
      },
      'Total': {},
      'Groups': [
        {
          'Keys': [
            '111122223333',
            'NoResourceId'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '10.1791666761',
              'Unit': 'USD'
            }
          }
        },
        {
          'Keys': [
            '111122223333',
            'i-0abcdefg'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '11.1791666761',
              'Unit': 'USD'
            }
          }
        }
      ],
      'Estimated': True
    }
  ],
  'DimensionValueAttributes': [
    {
      'Value': '111122223333',
      'Attributes': {
        'description': 'test-account-name'
      }
    },
  ],
  'ResponseMetadata': {
    'RequestId': '15f5cdde-0ea0-420f-867a-b862afeca967',
    'HTTPStatusCode': 200,
    'HTTPHeaders': {
      'date': 'Wed, 31 May 2023 20:57:36 GMT',
      'content-type': 'application/x-amz-json-1.1',
      'content-length': '14561',
      'connection': 'keep-alive',
      'x-amzn-requestid': '15f5cdde-0ea0-420f-867a-b862afeca967',
      'cache-control': 'no-cache'
    },
    'RetryAttempts': 0
  }
}

mock_ce_missing_tag_multi = {
  'GroupDefinitions': [
    {'Type': 'DIMNESION', 'Key': 'LINKED_ACCOUNT'},
    {'Type': 'DIMNESION', 'Key': 'RESOURCE_ID'},
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {
        'Start': '2023-06-01T00:00:00Z',
        'End': '2023-07-01T00:00:00Z'
      },
      'Total': {},
      'Groups': [
        {
          'Keys': [
            '111122223333',
            'NoResourceId'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '10.1791666761',
              'Unit': 'USD'
            }
          }
        },
        {
          'Keys': [
            '111122223333',
            'i-0abcdefg'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '11.1791666761',
              'Unit': 'USD'
            }
          }
        },
        {
          'Keys': [
            '111122223333',
            'i-0hijklmnop'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '11.1791666761',
              'Unit': 'USD'
            }
          }
        },
        {
          'Keys': [
            '222233334444',
            'i-1hijklmnop'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '11.1791666761',
              'Unit': 'USD'
            }
          }
        }
      ],
      'Estimated': True
    }
  ],
  'DimensionValueAttributes': [
    {
      'Value': '111122223333',
      'Attributes': {
        'description': 'test-account-name'
      }
    },
  ],
  'ResponseMetadata': {
    'RequestId': '15f5cdde-0ea0-420f-867a-b862afeca967',
    'HTTPStatusCode': 200,
    'HTTPHeaders': {
      'date': 'Wed, 31 May 2023 20:57:36 GMT',
      'content-type': 'application/x-amz-json-1.1',
      'content-length': '14561',
      'connection': 'keep-alive',
      'x-amzn-requestid': '15f5cdde-0ea0-420f-867a-b862afeca967',
      'cache-control': 'no-cache'
    },
    'RetryAttempts': 0
  }
}

mock_ce_missing_tag_no_id = {
  'GroupDefinitions': [
    {'Type': 'DIMNESION', 'Key': 'LINKED_ACCOUNT'},
    {'Type': 'DIMNESION', 'Key': 'RESOURCE_ID'},
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {
        'Start': '2023-06-01T00:00:00Z',
        'End': '2023-07-01T00:00:00Z'
      },
      'Total': {},
      'Groups': [
        {
          'Keys': [
            '111122223333',
            'NoResourceId'
          ],
          'Metrics': {
            'UnblendedCost': {
              'Amount': '1.1791666761',
              'Unit': 'USD'
            }
          }
        }
      ],
      'Estimated': True
    }
  ],
  'DimensionValueAttributes': [
    {
      'Value': '111122223333',
      'Attributes': {
        'description': 'test-account-name'
      }
    },
  ],
  'ResponseMetadata': {
    'RequestId': '15f5cdde-0ea0-420f-867a-b862afeca967',
    'HTTPStatusCode': 200,
    'HTTPHeaders': {
      'date': 'Wed, 31 May 2023 20:57:36 GMT',
      'content-type': 'application/x-amz-json-1.1',
      'content-length': '14561',
      'connection': 'keep-alive',
      'x-amzn-requestid': '15f5cdde-0ea0-420f-867a-b862afeca967',
      'cache-control': 'no-cache'
    },
    'RetryAttempts': 0
  }
}

mock_ce_missing_tag_none = {
  'GroupDefinitions': [
    {'Type': 'DIMNESION', 'Key': 'LINKED_ACCOUNT'},
    {'Type': 'DIMNESION', 'Key': 'RESOURCE_ID'},
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {
        'Start': '2023-06-01T00:00:00Z',
        'End': '2023-07-01T00:00:00Z'
      },
      'Total': {
        'UnblendedCost': {
          'Amount': '0'
        }
      },
      'Groups': [],
      'Estimated': True
    }
  ],
  'DimensionValueAttributes': [
    {
      'Value': '111122223333',
      'Attributes': {
        'description': 'test-account-name'
      }
    },
  ],
  'ResponseMetadata': {
    'RequestId': '15f5cdde-0ea0-420f-867a-b862afeca967',
    'HTTPStatusCode': 200,
    'HTTPHeaders': {
      'date': 'Wed, 31 May 2023 20:57:36 GMT',
      'content-type': 'application/x-amz-json-1.1',
      'content-length': '14561',
      'connection': 'keep-alive',
      'x-amzn-requestid': '15f5cdde-0ea0-420f-867a-b862afeca967',
      'cache-control': 'no-cache'
    },
    'RetryAttempts': 0
  }
}

expected_ce_email_category = [
 {'Estimated': False,
  'Groups': [{'Keys': ['Owner Email$', '111122223333'],
              'Metrics': {'UnblendedCost': {'Amount': '48446.9515396549',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user1@synapse.org', '111122223333'],
              'Metrics': {'UnblendedCost': {'Amount': '0.30000000264',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user2@synapse.org', '111122223333'],
              'Metrics': {'UnblendedCost': {'Amount': '3.000000264',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user3@sagebase.org', '111122223333'],
              'Metrics': {'UnblendedCost': {'Amount': '30.000000264',
                                            'Unit': 'USD'}}}],
  'TimePeriod': {'End': '2023-04-01',
                 'Start': '2023-03-01'},
  'Total': {}},
]

expected_emails_all = {
  '': {
    'total': 48446.9515396549,
    'account_totals': {'111122223333': 48446.9515396549},
  },
  'user1@synapse.org': {
    'total': 0.30000000264,
    'account_totals': {'111122223333': 0.30000000264},
  },
  'user2@synapse.org': {
    'total': 3.000000264,
    'account_totals': {'111122223333': 3.000000264},
  },
  'user3@sagebase.org': {
    'total': 30.000000264,
    'account_totals': {'111122223333': 30.000000264},
  }
}

expected_emails_filtered = {
  'user2@synapse.org': {
    'total': 3.000000264,
    'account_totals': {'111122223333': 3.000000264},
  },
  'user3@sagebase.org': {
    'total': 30.000000264,
    'account_totals': {'111122223333': 30.000000264},
  }
}

expected_emails_no_min = {
  'user1@synapse.org': {
    'total': 0.30000000264,
    'account_totals': {'111122223333': 0.30000000264},
  },
  'user2@synapse.org': {
    'total': 3.000000264,
    'account_totals': {'111122223333': 3.000000264},
  },
  'user3@sagebase.org': {
    'total': 30.000000264,
    'account_totals': {'111122223333': 30.000000264},
  }
}

expected_summary_filtered = {
  'user2@synapse.org': {
    'total': 3.000000264,
    'account_totals': {
      '111122223333': 3.000000264
    },
    'missing_other_tag': {
      '111122223333': ['i-0abcdefg'],
    }
  },
  'user3@sagebase.org': {
    'total': 30.000000264,
    'account_totals': {'111122223333': 30.000000264},
    'missing_other_tag': {
      '111122223333': ['i-0abcdefg', 'i-0hijklmnop'],
      '222233334444': ['i-1hijklmnop'],
    }
  }
}

mock_approved_emails = 'user3@sagebase.org,user4@synapse.org'

expected_emails_restricted = {
  'user3@sagebase.org': {
    'total': 30.000000264,
    'account_totals': {'111122223333': 30.000000264},
  }
}

mock_restricted_compare = {
  'user3@sagebase.org': {
    'total': 20.000000264,
    'account_totals': {'111122223333': 20.000000264},
  }
}

mock_syn_team = 'team'
mock_syn_members = [
    {'member': {'userName': 'user1'}},
    {'member': {'userName': 'user2'}},
]

expected_sage_emails = [
    'user1@synapse.org',
    'user2@synapse.org',
]

mock_ses_response = { 'MessageId': 'testId' }


@pytest.mark.parametrize(
        "test_now,expected_target_period,expected_compare_period",
        [
            (test_now_dec, expected_target_dec, expected_compare_dec),
            (test_now_jan, expected_target_jan, expected_compare_jan),
            (test_now_feb, expected_target_feb, expected_compare_feb),
        ]
    )
def test_get_periods(test_now, expected_target_period, expected_compare_period):
    test_dt = datetime.fromisoformat(test_now)
    found_target, found_compare = handler.get_reporting_periods(test_dt)
    assert found_target == expected_target_period
    assert found_compare == expected_compare_period


def test_get_team_sage(mocker):
    mock_syn_client = mocker.MagicMock(spec=handler.syn_client)

    mock_syn_client.getTeam.return_value = mock_syn_team
    mock_syn_client.getTeamMembers.return_value = mock_syn_members

    handler.syn_client = mock_syn_client

    found_sage_emails = handler.get_team_sage_emails()
    assert found_sage_emails == expected_sage_emails


def test_get_ce_email_category(mocker):
    with Stubber(handler.ce_client) as _stub:
        _stub.add_response('get_cost_and_usage', mock_ce_email_category)

        found_ce_costinfo = handler.get_ce_email_category(expected_target_dec)
        assert found_ce_costinfo == expected_ce_email_category


def test_get_email_summary(mocker):
    found_emails_all = handler.get_summary_by_email(expected_ce_email_category)
    assert found_emails_all == expected_emails_all


@pytest.mark.parametrize(
        "minimum,restrict,expected_emails",
        [
            ('1.0', 'True', expected_emails_restricted),
            ('1.0', 'False', expected_emails_filtered),
            ('0.0', 'False', expected_emails_no_min),
        ]
    )
def test_filter_sage_emails(mocker, minimum, restrict, expected_emails):
    env_vars = {
        'MINIMUM': minimum,
        'RESTRICT': restrict,
        'APPROVED': mock_approved_emails,
        'SKIPLIST': '',
    }
    mocker.patch.dict(os.environ, env_vars)

    found_emails = handler.filter_email_list(expected_emails_all, expected_sage_emails)
    assert found_emails == expected_emails


def test_add_missing_tag(mocker):
    # return these values,
    # we expect the function to be called twice
    side_effects = [
        mock_ce_missing_tag['ResultsByTime'],
        mock_ce_missing_tag_multi['ResultsByTime'],
    ]

    mocker.patch('email_totals.handler.get_ce_missing_tag_for_email',
                 side_effect=side_effects)

    now = datetime.now()

    found_summary = handler.add_ce_missing_tag(expected_emails_filtered, now)
    assert found_summary == expected_summary_filtered


def test_create_email(mocker):
    mocker.patch('email_totals.handler.send_report_email', autospec=True)

    handler.create_and_send_emails(expected_emails_restricted, mock_restricted_compare)


def test_send_email(mocker):
    recipient = 'user1@sagebase.org'
    text_body = 'test body'
    html_body = '<html>test body</html>'

    with Stubber(handler.ses_client) as _stub:
        _stub.add_response('send_email', mock_ses_response)

        env_vars = {
            'SENDER': 'test@example.com',
        }
        mocker.patch.dict(os.environ, env_vars)

        handler.send_report_email(recipient, text_body, html_body)

        # assert that no exception is raised
