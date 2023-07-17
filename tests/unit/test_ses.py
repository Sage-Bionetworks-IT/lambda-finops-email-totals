import os

import pytest
from botocore.stub import Stubber

from email_totals import ses


def test_send_email(mocker,
                    mock_ses_response):
    recipient = 'user@synapse.org'
    text_body = 'test'
    html_body = '<html>test</html>'
    period = 'Test Month'

    env_vars = {
        'SENDER': 'test@example.com',
    }
    mocker.patch.dict(os.environ, env_vars)

    with Stubber(ses.ses_client) as _stub:
        _stub.add_response('send_email', mock_ses_response)

        ses.send_report_email(recipient, html_body, text_body, period)

        # assert that the client function was called
        _stub.assert_no_pending_responses()


def test_email_body(mock_app_account_names,
                    mock_app_build_summary,
                    mock_user1,
                    mock_user2,
                    mock_user3,
                    mock_user4):
    # assert no exceptions are raised
    html, text = ses.build_email_body(mock_app_build_summary[mock_user1],
                                      mock_app_account_names)
    print(html)
    print(text)

    html, text = ses.build_email_body(mock_app_build_summary[mock_user2],
                                      mock_app_account_names)
    print(html)
    print(text)

    html, text = ses.build_email_body(mock_app_build_summary[mock_user3],
                                      mock_app_account_names)
    print(html)
    print(text)

    html, text = ses.build_email_body(mock_app_build_summary[mock_user4],
                                      mock_app_account_names)
    print(html)
    print(text)


@pytest.mark.parametrize(
    "mock_env_restrict,mock_env_approved,mock_env_skiplist,mock_email,result",
    [
        ("False", [], [], 'test@example.com', False),  # invalid domain
        ("False", [], [], 'user1' + ses.synapse_email, True),  # member of Team Sage
        ("False", [], [], 'external' + ses.synapse_email, False),  # not a member of Team Sage
        ("False", [], [], 'user' + ses.sagebase_email, True),  # internal Sage domain
        ("False", [], [], 'user' + ses.sagebio_email, True),  # internal Sage domain
        ("False", [], ['user' + ses.sagebio_email], 'user' + ses.sagebio_email, False),  # user in skip list
        ("True", ['user' + ses.sagebio_email], [], 'user' + ses.sagebio_email, True),  # user in approved list
        ("True", [], [], 'user' + ses.sagebio_email, False),  # user not in approved list
    ]
)
def test_valid_recipient(mocker,
                         mock_env_approved,
                         mock_env_restrict,
                         mock_env_skiplist,
                         mock_team_sage,
                         mock_email,
                         result):
    env_vars = {
        'RESTRICT': mock_env_restrict,
        'APPROVED': ','.join(mock_env_approved),
        'SKIPLIST': ','.join(mock_env_skiplist),
    }
    mocker.patch.dict(os.environ, env_vars)

    found = ses.valid_recipient(mock_email, mock_team_sage)
    assert found == result
