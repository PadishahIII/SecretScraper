from secretscraper.util import read_rules_from_setting

from . import settings


def test_read_rules_from_setting():
    d = read_rules_from_setting(settings)
    assert len(d) > 0
