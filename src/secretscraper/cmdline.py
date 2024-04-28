"""Command line"""

import functools
import logging
import pathlib

import click
from click import Context
from dynaconf.base import Settings

from secretscraper import __version__
from secretscraper.config import settings
from secretscraper.exception import FacadeException
from secretscraper.facade import CrawlerFacade, FileScannerFacade
from secretscraper.handler import HyperscanRegexHandler
from secretscraper.log import init_log

facade_settings = settings  # for unit test
facade_obj = None


# @click.group(invoke_without_command=True)
# @click.pass_context
@click.command()
@click.option(
    "-V", "--version", is_flag=True, help="Show version and exit."
)  # If it's true, it will override `settings.VERBOSE`
# @click.option("-v", "--verbose", is_flag=True, help="Show more info.")
@click.option(
    "--debug", is_flag=True, help="Enable debug."
)  # If it's true, it will override `settings.DEBUG`
@click.option("-a", "--ua", help="Set User-Agent", type=click.STRING)
@click.option("-c", "--cookie", help="Set cookie", type=click.STRING)
@click.option(
    "-d",
    "--allow-domains",
    help="Domain white list, wildcard(*) is supported, separated by commas, e.g. *.example.com, example*",
    type=click.STRING,
)
@click.option(
    "-D",
    "--disallow-domains",
    help="Domain black list, wildcard(*) is supported, separated by commas, e.g. *.example.com, example*",
    type=click.STRING,
)
@click.option(
    "-f",
    "--url-file",
    help="Target urls file, separated by line break",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "-i",
    "--config",
    help="Set config file, defaults to settings.yml",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "-m",
    "--mode",
    help="Set crawl mode, 1(normal) for max_depth=1, 2(thorough) for max_depth=2, default 1",
    type=click.Choice(["1", "2"]),
)
@click.option(
    "--max-page", help="Max page number to crawl, default 100000", type=click.INT
)
@click.option("--max-depth", help="Max depth to crawl, default 1", type=click.INT)
@click.option(
    "-o",
    "--outfile",
    help="Output result to specified file",
    type=click.Path(
        exists=False, file_okay=True, dir_okay=False, path_type=pathlib.Path
    ),
)
@click.option(
    "-s",
    "--status",
    help="Filter response status to display, seperated by commas, e.g. 200,300-400",
    type=click.STRING,
)
@click.option(
    "-x",
    "--proxy",
    help="Set proxy, e.g. http://127.0.0.1:8080, http://127.0.0.1:7890",
    type=click.STRING,
)
@click.option("-H", "--hide-regex", help="Hide regex search result", is_flag=True)
@click.option("-F", "--follow-redirects", help="Follow redirects", is_flag=True)
@click.option("-u", "--url", help="Target url", type=click.STRING)
@click.option("-l", "--local", help="Local file or directory, scan local file/directory recursively ",
              type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path))
def main(**options):
    """Main commands"""
    if options["version"]:
        click.echo(__version__)
        exit(1)
    if options["debug"]:
        settings.DEBUG = True
        settings.LOGLEVEL = "debug"
    if options["config"] is not None:
        if not options["config"].exists():
            click.echo(f"Error: config file not exists: {str(options['config'])}")
            return
        settings.load_file(path=str(options["config"]))
    options_dict = dict()
    for key, value in options.items():
        if value is not None:
            options_dict[key] = value
    # settings.update(options_dict)
    try:
        global facade_settings, facade_obj
        print_func = functools.partial(click.echo, color=True)
        init_log()
        if options['local'] is not None:
            facade = FileScannerFacade(settings, options_dict, print_func)
        else:
            facade = CrawlerFacade(settings, options_dict, print_func=print_func)
        facade_obj = facade
        facade_settings = facade.settings
    except FacadeException as e:
        click.echo(f"Error: {e}")
        exit(1)
    else:
        facade.start()
