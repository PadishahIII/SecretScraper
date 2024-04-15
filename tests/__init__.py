"""Test"""

import functools
import time
from pathlib import Path

from secretscraper.config import settings
from secretscraper.log import init_log


def merge_test_settings():
    """
    合并测试配置
    :return:
    """
    test_config_path = Path(__file__).parent
    settings.load_file(test_config_path / "settings.yml")
    settings.load_file(test_config_path / "settings.local.yml")


merge_test_settings()


def duration(func):
    """Print execution time"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        before = time.time()
        ret = func(*args, **kwargs)
        after = time.time()
        print(f"\n{func.__name__} finished in {after - before} seconds")
        return ret

    return wrapper


init_log()
