"""Output the crawl result to file or terminal"""

import pathlib
import sys
import typing

import click

from .entity import URL, Secret, URLNode
from .util import Range, to_host_port


class Formatter:
    """Colorful output for terminal and non-colorful output for out-file"""

    def __init__(
        self,
        allowed_status: list[Range] = None,
    ) -> None:
        """

        :param allowed_status: filter response status. None for display all
        """
        self._allowed_status = allowed_status

    @property
    def allowed_status(self) -> list[Range]:
        return self._allowed_status

    @allowed_status.setter
    def allowed_status(self, allowed_status: list[Range]):
        self._allowed_status = allowed_status

    def format_colorful_status(self, status: str) -> str:
        try:
            status = int(status)
        except Exception:
            return status
        if 200 == status:
            return click.style(status, fg="green")
        elif 300 <= status < 400:
            return click.style(status, fg="yellow")
        elif 400 <= status < 500:
            return click.style(status, fg="magenta")
        else:
            return click.style(status, fg="red")

    def format_normal_result(self, content: str) -> str:
        return click.style(content, fg="bright_blue")

    def filter(self, url: URLNode) -> bool:
        """Determine whether a url should be displayed"""
        try:
            if int(url.response_status) == 404:  # filter 404 by default
                return False
        except ValueError:
            pass
        if self._allowed_status is None:
            return True
        for status_range in self._allowed_status:
            try:
                if status_range.start <= int(url.response_status) < status_range.end:
                    continue
                else:
                    return False
            except ValueError:
                return False  # default discard
        return True

    def output_found_domains(
        self, found_urls: typing.Iterable[URLNode], is_print: bool = False
    ) -> str:
        """Output the found domains"""
        if not is_print:
            urls = {str(url.url_object.netloc) for url in found_urls}
            found_urls_str = "\n".join(urls)
            result = f"\n{len(urls)} Domains:\n{found_urls_str}\n"
            return result
        else:
            urls = {str(url.url_object.netloc) for url in found_urls}
            found_urls_str = "\n".join(urls)
            result = f"\n{len(urls)} Domains:\n{found_urls_str}\n"
            click.echo(f"{len(urls)} Domains:")
            click.echo(self.format_normal_result(f"{found_urls_str}"))
            click.echo("")
            return result

    def output_url_hierarchy(
        self, url_dict: dict[URLNode, typing.Iterable[URLNode]], is_print: bool = False
    ) -> str:
        """Output the url hierarchy"""
        if not is_print:
            url_hierarchy = ""
            for base, urls in url_dict.items():
                url_set = {
                    f"{str(url.url)} [{str(url.response_status)}]"
                    for url in urls
                    if self.filter(url)
                }
                urls_str = "\n".join(url_set)
                url_hierarchy += f"\n{len(url_set)} URLs from {base.url} [{str(base.response_status)}] (depth:{base.depth}):\n{urls_str}\n"
            return url_hierarchy
        else:
            url_hierarchy = ""
            for base, urls in url_dict.items():
                url_set = {
                    self.format_normal_result(f"{str(url.url)}")
                    + " ["
                    + self.format_colorful_status(url.response_status)
                    + "]"
                    for url in urls
                    if self.filter(url)
                }
                urls_str = "\n".join(url_set)
                url_hierarchy += f"\n{len(url_set)} URLs from {base.url} [{str(base.response_status)}] (depth:{base.depth}):\n{urls_str}"
                click.echo(
                    f"\n{len(url_set)} URLs from {base.url} ["
                    + self.format_colorful_status(base.response_status)
                    + f"] (depth:{base.depth}):\n{urls_str}"
                )

            return url_hierarchy

    def output_url_per_domain(
        self, domains: set[str], url_dict: dict[URLNode, typing.Iterable[URLNode]], url_type: str = "URL"
    ) -> str:
        """Output the URLs for differenct domains"""
        url_hierarchy = ""
        domain_secrets: dict[str, list[URLNode]] = dict()
        for base, urls in url_dict.items():
            domain, _ = to_host_port(base.url_object.netloc)
            if domain not in domains:
                domain = "Other"
            if domain not in domain_secrets:
                domain_secrets[domain] = list()
            domain_secrets[domain].extend(list(urls))
        for domain, urls in domain_secrets.items():
            if urls is None or len(urls) == 0:
                continue
            url_set = {
                self.format_normal_result(f"{str(url.url)}")
                + " ["
                + self.format_colorful_status(url.response_status)
                + "]"
                for url in urls
                if self.filter(url)
            }
            urls_str = "\n".join(url_set)
            url_hierarchy += f"\n{len(url_set)} {url_type} from {domain}:\n{urls_str}\n"
        click.echo(url_hierarchy)

        return url_hierarchy

    def output_js(
        self, js_dict: dict[URLNode, typing.Iterable[URLNode]], is_print: bool = False
    ) -> str:
        """Output the url hierarchy"""
        if is_print:
            js_str = ""
            for base, urls in js_dict.items():
                url_set = {
                    f"{str(url.url)} [{str(url.response_status)}]"
                    for url in urls
                    if self.filter(url)
                }
                urls_str = "\n".join(url_set)
                js_str += f"\n{len(url_set)} JS from {base.url}:\n{urls_str}\n"
            return js_str
        else:
            js_str = ""
            for base, urls in js_dict.items():
                url_set = {
                    self.format_normal_result(f"{str(url.url)}")
                    + " ["
                    + self.format_colorful_status(url.response_status)
                    + "] "
                    for url in urls
                    if self.filter(url)
                }
                urls_str = "\n".join(url_set)
                js_str += f"\n{len(url_set)} JS from {base.url}:\n{urls_str}\n"
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
                url_secrets_str += f"\n{len(secret_set)} Secrets found in {url.url} [{self.format_colorful_status(str(url.response_status))}]:\n{secrets_str}\n"
        return url_secrets_str

    def output_local_scan_secrets(self, path_secrets: dict[pathlib.Path, typing.Iterable[Secret]]) -> str:
        """Display all secrets found in local file"""
        if len(path_secrets) == 0:
            click.echo("No secrets found.\n")
        result = ""
        for path, secrets in path_secrets.items():
            if secrets is not None and len(list(secrets)) > 0:
                secret_set = {
                    f"{str(secret.type)}: {str(secret.data)}" for secret in secrets
                }
                secrets_str = "\n".join(secret_set)
                s = click.style(f"\n{len(secret_set)} Secrets found in {str(path)}:", fg="cyan") + \
                    f"\n{secrets_str}\n"
                result += s
                click.echo(s)
        return result
