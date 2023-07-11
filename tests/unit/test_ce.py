from botocore.stub import Stubber

from email_totals import ce


def test_ce_accounts(mocker, mock_ce_period, mock_ce_account_usage):
    with Stubber(ce.ce_client) as _stub:
        _stub.add_response('get_cost_and_usage', mock_ce_account_usage)

        ce.get_ce_account_costs(mock_ce_period)

        # assert that the client function was called
        _stub.assert_no_pending_responses()


def test_ce_emails(mocker, mock_ce_period, mock_ce_email_usage):
    with Stubber(ce.ce_client) as _stub:
        _stub.add_response('get_cost_and_usage', mock_ce_email_usage)

        ce.get_ce_email_costs(mock_ce_period)

        # assert that the client function was called
        _stub.assert_no_pending_responses()


def test_ce_missing_tags(mocker, mock_ce_missing_tag_resources):
    with Stubber(ce.ce_client) as _stub:
        _stub.add_response('get_cost_and_usage_with_resources', mock_ce_missing_tag_resources)

        ce.get_ce_missing_tag_for_email('email')

        # assert that the client function was called
        _stub.assert_no_pending_responses()
