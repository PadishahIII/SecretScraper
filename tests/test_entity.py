from urllib.parse import urlparse

import pytest

from secretscraper.entity import URLNode


def test_urlnode():
    base_node = URLNode(url="http://example.com", url_object=urlparse("http://example.com"), depth=0, parent=None)
    base_node_2 = URLNode(url="http://example.com/b", url_object=urlparse("http://example.com/b"), depth=0, parent=None)
    node1 = URLNode(url="http://example.com/xxx", url_object=urlparse("http://example.com/xxx"), depth=1,
                    parent=base_node)
    node1_copy_without_parent_and_depth = URLNode(url=node1.url,
                                                  url_object=node1.url_object, depth=2, parent=node1)
    node1_copy_without_parent = URLNode(url=node1.url,
                                        url_object=node1.url_object, depth=1, parent=base_node_2)
    node1_copy_without_url = URLNode(url=node1.url + "#..",
                                        url_object=node1.url_object, depth=1, parent=base_node)

    assert node1 == node1_copy_without_parent_and_depth
    assert node1 == node1_copy_without_parent
    assert node1 == node1_copy_without_url
    assert hash(node1) == hash(node1_copy_without_parent_and_depth)
    assert hash(node1) == hash(node1_copy_without_parent)
    assert hash(node1) == hash(node1_copy_without_url)
    with pytest.raises(ValueError):
        URLNode(url="http://example.com/2", url_object=urlparse("http://example.com/2"), depth=0,
                parent=base_node)
