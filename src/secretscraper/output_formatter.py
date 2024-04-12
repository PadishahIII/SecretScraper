"""Output the crawl result to file or terminal"""
import typing

from .entity import URL, Secret, URLNode


class Formatter:
    """Colorful output for terminal and non-colorful output for out-file"""

    def __init__(self, out_file: typing.IO = None) -> None:
        self.out_file = out_file

    def output_found_domains(self, found_urls: typing.Iterable[URLNode]) -> str:
        """Output the found domains"""
        found_urls_str = "\n".join(str(url) for url in found_urls)
        return found_urls_str

    def output_url_hierarchy(self, url_dict: dict[URLNode, typing.Iterable[URLNode]]) -> str:
        """Output the url hierarchy"""
        url_hierarchy = ""
        for base, urls in url_dict.items():
            urls_str = "\n\t".join(str(url.url) for url in urls)
            url_hierarchy += f"{base}:\n\t{urls_str}\n"
        return url_hierarchy

    def output_secrets(self, url_secrets: dict[URLNode, typing.Iterable[Secret]]) -> str:
        """Output all secrets found
        :type secrets: dict[str, set[Secret]]
        :param secrets: dict keys indicate url and values indicate the secrets found from the url

        """
        url_secrets = ""
        for url, secrets in url_secrets:
            secrets_str = "\n\t".join(str(secret) for secret in secrets)
            url_secrets += f"{url.url}:\n\t{secrets_str}\n"
        return url_secrets
