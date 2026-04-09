from secretscraper.util import read_rules_from_setting, start_local_test_http_server
import requests

from . import settings


def test_read_rules_from_setting():
    d = read_rules_from_setting(settings)
    assert len(d) > 0


def test_start_local_test_http_server():
    thread, httpd = start_local_test_http_server("127.0.0.1", 8888)
    res = requests.get("http://127.0.0.1:8888/index.html", timeout=5)
    try:
        assert res.status_code == 200
    except AssertionError as e:
        raise e
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None:
            thread.join(timeout=1)
        # print(1)
