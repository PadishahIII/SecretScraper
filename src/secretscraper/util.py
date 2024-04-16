"""Common utility functions."""

from collections import namedtuple

from dynaconf import LazySettings

from .exception import SecretScraperException

Range = namedtuple("Range", ["start", "end"])


def read_rules_from_setting(settings: LazySettings) -> dict[str, str]:
    """Read rules from settings

    :param settings: Dynaconf settings
    :return dict[str, str]: key for rule name and value for regex literal
    """
    rules_dict = dict()
    try:
        rules = settings.RULES
        for rule in rules:
            name = rule.get("name")
            regex = rule.get("regex")
            loaded = rule.get("loaded")
            if loaded is True:
                rules_dict[name] = regex
    except Exception as e:
        raise SecretScraperException(
            f"Exception occur when reading rules from setting: {e}"
        ) from e
    return rules_dict
