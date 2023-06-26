import logging

import synapseclient as syn

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

synapse_email = '@synapse.org'
synapse_team_sage = '273957'

# Create a Synapse client
# The lambda homedir is not writeable, put the cache in /tmp
syn_client = syn.Synapse(cache_root_dir='/tmp/synapse')


def get_team_sage_members():
    """
    Get a list of Team Sage emails from Synapse
    """

    team_sage = []

    syn_team = syn_client.getTeam(synapse_team_sage)
    syn_members = syn_client.getTeamMembers(syn_team)
    for m in syn_members:
        email = m['member']['userName'] + synapse_email
        team_sage.append(email)

    LOG.info(f"Members of Team Sage: {team_sage}")

    return team_sage
