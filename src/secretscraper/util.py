"""Common utility functions."""

from collections import namedtuple
import re
from urllib.parse import urlparse

from dynaconf import LazySettings

from .entity import URL
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


def is_static_resource(path: str) -> bool:
    """Check whether a path is a static resource"""
    exts = ['.png', '.jpg', '.jpeg', '.gif', '.css', '.ico', ".dtd", '.svg']
    for ext in exts:
        if path.endswith(ext):
            return True
    return False


def to_host_port(netloc: str) -> tuple[str, str]:
    """Convert netloc to host and port"""
    r = netloc.split(":")
    if len(r) == 1:
        return r[0], ""
    if len(r) == 2:
        return r[0].strip(), r[1].strip()
    return '', ''


def sanitize_url(url: str) -> str:
    """Remove invalid characters in url
    Return emtpy string if url is invalid
    """
    url = url.replace(" ", "") \
        .replace("\\/", "/") \
        .replace("%3A", ":") \
        .replace("%2F", "/")
    # remove url that does not contain any word
    m = re.search("[a-zA-Z0-9]+", url)
    if m is None:
        return ""
    if url.strip().startswith("javascript"):
        return ""
    try:
        obj = urlparse(url)
        if obj.netloc.startswith("127.0.0.1") or obj.netloc.startswith("localhost"):
            return ""
    except:
        pass
    return url
