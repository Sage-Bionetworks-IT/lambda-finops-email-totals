from email_totals import synapse


def test_team_sage(mocker, mock_syn_team, mock_syn_members, mock_team_sage):
    mock_syn_client = mocker.MagicMock(spec=synapse.syn_client)

    mock_syn_client.getTeam.return_value = mock_syn_team
    mock_syn_client.getTeamMembers.return_value = mock_syn_members

    synapse.syn_client = mock_syn_client

    found_team_sage = synapse.get_team_sage_members()
    assert found_team_sage == mock_team_sage
