from secretscraper.util import read_rules_from_setting, start_local_test_http_server
import requests
from signal import pthread_kill, SIGKILL

from . import settings


def test_read_rules_from_setting():
    d = read_rules_from_setting(settings)
    assert len(d) > 0


def test_start_local_test_http_server():
    thread, httpd = start_local_test_http_server("127.0.0.1", 8888)
    res = requests.get(f"http://127.0.0.1:8888/index.html")
    try:
        assert res.status_code == 200
    except AssertionError as e:
        raise e
    finally:
        httpd.shutdown()
        print(1)
