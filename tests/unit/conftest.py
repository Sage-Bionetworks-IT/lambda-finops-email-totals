import pytest


@pytest.fixture()
def mock_app_resource_totals():
    response = {
        'user1@sagebase.org': {
            'resources': {
                '111122223333': {
                    'total': 10.1,
                }
            }
        },
        'user2@sagebase.org': {
            'resources': {
                '111122223333': {
                    'total': 20.2,
                    'change': 2.1,
                }
            }
        }
    }
    return response


@pytest.fixture()
def mock_app_account_totals():
    response = {
        'user1@sagebase.org': {
            'accounts': {
                '333344445555': {
                    'total': 100,
                    'change': -0.1,
                }
            }
        },
        'user2@sagebase.org': {
            'accounts': {
                '444455556666': {
                    'total': 222.2,
                    'change': 2.2,
                }
            }
        }
    }
    return response


@pytest.fixture()
def mock_app_missing_tags():
    response = {
        '111122223333': [
            'i-0abcdefg',
            'i-1hikjlmn',
        ]
    }
    return response


@pytest.fixture()
def mock_app_build_summary():
    response = {
        'user1@sagebase.org': {
            'resources': {
                '111122223333': {
                    'total': 10.1
                }
            },
            'accounts': {
                '333344445555': {
                    'total': 100,
                    'change': -0.1
                }
            },
            'missing_other_tag': {
                '111122223333': [
                    'i-0abcdefg',
                    'i-1hikjlmn'
                ]
            }
        },
        'user2@sagebase.org': {
            'resources': {
                '111122223333': {
                    'total': 20.2,
                    'change': 2.1
                }
            },
            'accounts': {
                '444455556666': {
                    'total': 222.2,
                    'change': 2.2
                }
            }
        }
    }
    return response


@pytest.fixture()
def mock_ses_response():
    response = { 'MessageId': 'testId' }
    return response
