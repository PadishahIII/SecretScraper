"""Test"""

from pathlib import Path

from secretscraper.config import settings


def merge_test_settings():
    """
    合并测试配置
    :return:
    """
    test_config_path = Path(__file__).parent
    settings.load_file(test_config_path / "settings.yml")
    settings.load_file(test_config_path / "settings.local.yml")


merge_test_settings()
