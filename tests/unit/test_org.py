from botocore.stub import Stubber

from email_totals import org


def test_account_owners(mock_org_accounts,
                        mock_org_account_no_tags,
                        mock_org_account_tags_user3,
                        mock_org_account_tags_user4,
                        mock_org_account_owners):
    with Stubber(org.org_client) as _stub:
        _stub.add_response('list_accounts', mock_org_accounts)

        # No owner tags for account1 or account2
        _stub.add_response('list_tags_for_resource', mock_org_account_no_tags)
        _stub.add_response('list_tags_for_resource', mock_org_account_no_tags)
        _stub.add_response('list_tags_for_resource', mock_org_account_tags_user3)
        _stub.add_response('list_tags_for_resource', mock_org_account_tags_user4)

        found_account_owners = org.get_account_owners()
        assert found_account_owners == mock_org_account_owners

        # assert that the client function was called the expected number of times
        _stub.assert_no_pending_responses()
