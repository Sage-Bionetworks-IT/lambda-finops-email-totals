from botocore.stub import Stubber

from email_totals import org


def test_account_owners(mocker,
                        mock_org_accounts,
                        mock_org_account_tags,
                        mock_org_account_no_tags):
    with Stubber(org.org_client) as _stub:
        _stub.add_response('list_accounts', mock_org_accounts)

        _stub.add_response('list_tags_for_resource', mock_org_account_no_tags)
        _stub.add_response('list_tags_for_resource', mock_org_account_tags)

        org.get_account_owners()

        # assert that the client function was called
        _stub.assert_no_pending_responses()
