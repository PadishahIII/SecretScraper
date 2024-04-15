"""Output the crawl result to file or terminal"""

import typing

from .entity import URL, Secret, URLNode


class Formatter:
    """Colorful output for terminal and non-colorful output for out-file"""

    def __init__(self, out_file: typing.IO = None) -> None:
        self.out_file = out_file

    def output_found_domains(self, found_urls: typing.Iterable[URLNode]) -> str:
        """Output the found domains"""
        urls = {str(url.url_object.netloc) for url in found_urls}
        found_urls_str = "\n".join(urls)
        return f"{len(urls)} Domains:\n{found_urls_str}\n\n"

    def output_url_hierarchy(
        self, url_dict: dict[URLNode, typing.Iterable[URLNode]]
    ) -> str:
        """Output the url hierarchy"""
        url_hierarchy = ""
        for base, urls in url_dict.items():
            url_set = {str(url.url) for url in urls}
            urls_str = "\n".join(url_set)
            url_hierarchy += f"{len(url_set)} URLs from {base.url}(depth:{base.depth}):\n{urls_str}\n\n"
        return url_hierarchy

    def output_js(self, js_dict: dict[URLNode, typing.Iterable[URLNode]]) -> str:
        """Output the url hierarchy"""
        js_str = ""
        for base, urls in js_dict.items():
            url_set = {str(url.url) for url in urls}
            urls_str = "\n".join(url_set)
            js_str += f"{len(url_set)} JS from {base.url}:\n{urls_str}\n\n"
        return js_str

    def output_secrets(
        self, url_secrets: dict[URLNode, typing.Iterable[Secret]]
    ) -> str:
        """Output all secrets found
        :type secrets: dict[str, set[Secret]]
        :param secrets: dict keys indicate url and values indicate the secrets found from the url

        """
        url_secrets_str = ""
        if len(url_secrets.values()) == 0:
            return "No secrets found.\n"
        for url, secrets in url_secrets.items():
            if secrets is not None and len(list(secrets)) > 0:
                secret_set = {
                    f"{str(secret.type)}: {str(secret.data)}" for secret in secrets
                }
                secrets_str = "\n".join(secret_set)
                url_secrets_str += (
                    f"{len(secret_set)} Secrets found in {url.url}:\n{secrets_str}\n\n"
                )
        return url_secrets_str
