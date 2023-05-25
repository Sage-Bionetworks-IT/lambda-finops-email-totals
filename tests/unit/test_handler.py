from email_totals import handler

import json
import os

import boto3
import pytest
from botocore.stub import Stubber


mock_ce_response = {
  'GroupDefinitions': [
    {'Type': 'COST_CATEGORY', 'Key': 'Owner Email'}
  ],
  'ResultsByTime': [
    {
      'TimePeriod': {'Start': '2023-03-01', 'End': '2023-04-01'},
       'Total': {},
      'Groups': [
          {
            'Keys': ['Owner Email$'],
            'Metrics': {
              'UnblendedCost': {
                'Amount': '48446.9515396549',
                'Unit': 'USD'
              }
            }
          },
          {'Keys': ['Owner Email$user1@synapse.org'], 'Metrics': {'UnblendedCost': {'Amount': '0.30000000264', 'Unit': 'USD'}}},
          {'Keys': ['Owner Email$user2@synapse.org'], 'Metrics': {'UnblendedCost': {'Amount': '3.000000264', 'Unit': 'USD'}}},
          {'Keys': ['Owner Email$user3@sagebase.org'], 'Metrics': {'UnblendedCost': {'Amount': '30.000000264', 'Unit': 'USD'}}},
        ],
        'Estimated': False
    }
  ],
  'DimensionValueAttributes': [],
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

expected_ce_costinfo = [
 {'Estimated': False,
  'Groups': [{'Keys': ['Owner Email$'],
              'Metrics': {'UnblendedCost': {'Amount': '48446.9515396549',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user1@synapse.org'],
              'Metrics': {'UnblendedCost': {'Amount': '0.30000000264',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user2@synapse.org'],
              'Metrics': {'UnblendedCost': {'Amount': '3.000000264',
                                            'Unit': 'USD'}}},
             {'Keys': ['Owner Email$user3@sagebase.org'],
              'Metrics': {'UnblendedCost': {'Amount': '30.000000264',
                                            'Unit': 'USD'}}}],
  'TimePeriod': {'End': '2023-04-01',
                 'Start': '2023-03-01'},
  'Total': {}},
]

expected_emails_all = {
  '': 48446.9515396549,
  'user1@synapse.org': 0.30000000264,
  'user2@synapse.org': 3.000000264,
  'user3@sagebase.org': 30.000000264,
}

expected_emails_filtered = {
  'user2@synapse.org': 3.000000264,
  'user3@sagebase.org': 30.000000264,
}

expected_emails_no_min = {
  'user1@synapse.org': 0.30000000264,
  'user2@synapse.org': 3.000000264,
  'user3@sagebase.org': 30.000000264,
}

mock_approved_emails = 'user3@sagebase.org,user4@synapse.org'

expected_emails_restricted = {
  'user3@sagebase.org': 30.000000264,
}

mock_restricted_compare = {
  'user3@sagebase.org': 20.000000264,
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


def test_get_team_sage(mocker):
    mock_syn_client = mocker.MagicMock(spec=handler.syn_client)

    mock_syn_client.getTeam.return_value = mock_syn_team
    mock_syn_client.getTeamMembers.return_value = mock_syn_members

    handler.syn_client = mock_syn_client

    found_sage_emails = handler.get_team_sage_emails()
    assert found_sage_emails == expected_sage_emails


def test_get_ce_costinfo(mocker):
    with Stubber(handler.ce_client) as _stub:
        _stub.add_response('get_cost_and_usage', mock_ce_response)

        found_ce_costinfo = handler.get_ce_costinfo(handler.target_month)
        assert found_ce_costinfo == expected_ce_costinfo


def test_get_email_totals(mocker):
    found_emails_all = handler.get_email_totals(expected_ce_costinfo)
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
    }
    mocker.patch.dict(os.environ, env_vars)

    found_emails = handler.filter_email_list(expected_emails_all, expected_sage_emails)
    assert found_emails == expected_emails


def test_create_email(mocker):
    mocker.patch('email_totals.handler.send_report_email', autospec=True)

    handler.create_and_send_emails(expected_emails_restricted, mock_restricted_compare)


def test_send_email(mocker):
    recipient = 'user1@sagebase.org'
    email_html = 'test body'

    with Stubber(handler.ses_client) as _stub:
        _stub.add_response('send_email', mock_ses_response)

        env_vars = {
            'SENDER': 'test@example.com',
        }
        mocker.patch.dict(os.environ, env_vars)

        handler.send_report_email(recipient, email_html)

        # assert that no exception is raised
