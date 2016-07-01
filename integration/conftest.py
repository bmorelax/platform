import pytest
import requests


DEVICE_USER = "user"
DEVICE_PASSWORD = "password"


def pytest_addoption(parser):
    parser.addoption("--email", action="store")
    parser.addoption("--password", action="store")
    parser.addoption("--domain", action="store")
    parser.addoption("--app-archive-path", action="store")

@pytest.fixture(scope="session")
def auth(request):
    config = request.config
    return config.getoption("--email"), \
           config.getoption("--password"), \
           config.getoption("--domain"), \
           config.getoption("--app-archive-path")



@pytest.fixture(scope="function")
def public_web_session():

    retry = 0
    retries = 5
    while retry < retries:
        try:
            session = requests.session()
            session.post('http://localhost/rest/login', data={'name': DEVICE_USER, 'password': DEVICE_PASSWORD})
            assert session.get('http://localhost/rest/user', allow_redirects=False).status_code == 200
            return session
        except Exception, e:
            retry += 1
            print(e.message)
            print('retry {0} of {1}'.format(retry, retries)
    

