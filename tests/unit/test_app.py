from email_totals import app

import os

import pytest


def test_build_summary(mocker,
                       mock_app_resource_totals,
                       mock_app_account_totals,
                       mock_app_missing_tags,
                       mock_app_build_summary):

    def _missing_tags_side_effect():
        yield mock_app_missing_tags

        while True:
            yield {}


    env_vars = {
            'MINIMUM': '1.1',
    }
    mocker.patch.dict(os.environ, env_vars)

    mocker.patch('email_totals.app.get_resource_totals', return_value=mock_app_resource_totals)
    mocker.patch('email_totals.app.get_account_totals', return_value=mock_app_account_totals)

    mocker.patch('email_totals.app.get_missing_other_tags', side_effect=_missing_tags_side_effect())

    mocker.patch('email_totals.ses.valid_recipient', return_value=True)

    ret = app.build_summary(None, None, [])
    assert ret == mock_app_build_summary
