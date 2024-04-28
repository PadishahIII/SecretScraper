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
    help="Set proxy, e.g. http://127.0.0.1:8080, socks5://127.0.0.1:7890",
    type=click.STRING,
)
@click.option("-H", "--hide-regex", help="Hide regex search result", is_flag=True)
@click.option("-F", "--follow-redirects", help="Follow redirects", is_flag=True,
              type=click.BOOL)
@click.option("-u", "--url", help="Target url", type=click.STRING)
@click.option("--detail", help="Show detailed result", is_flag=True)
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
    else:
        file = pathlib.Path() / "settings.yml"
        generate_configuration(file)
        settings.load_file(path=str(file.absolute()))
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


def generate_configuration(file: pathlib.Path):
    """Generate settings.yml in current directory."""
    if file.exists():
        # click.echo(f"Fail to generate configuration: settings.yml already exists")
        return
    click.echo(f"Generating default configuration: {file.name}")
    file.write_text(
        r"""verbose: false
debug: false
loglevel: warning
logpath: log

proxy: "" # http://127.0.0.1:7890
max_depth: 1 # 0 for no limit
max_page_num: 1000 # 0 for no limit
timeout: 5
follow_redirects: false
workers_num: 1000
headers:
  Accept: "*/*"
  Cookie: ""
  User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0

urlFind:
  - '["''‘“`]\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100}?)\s{0,6}["''‘“`]'
  - =\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})
  - '["''‘“`]\s{0,6}([#,.]{0,2}/[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100}?)\s{0,6}["''‘“`]'
  - '"([-a-zA-Z0-9()@:%_\+.~#?&//={}]+?[/]{1}[-a-zA-Z0-9()@:%_\+.~#?&//={}]+?)"'
  - href\s{0,6}=\s{0,6}["'‘“`]{0,1}\s{0,6}([-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})|action\s{0,6}=\s{0,6}["'‘“`]{0,1}\s{0,6}([-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})
jsFind:
    - (https{0,1}:[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)
    - '["''‘“`]\s{0,6}(/{0,1}[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)'
    - =\s{0,6}[",',’,”]{0,1}\s{0,6}(/{0,1}[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)

rules:
  - name: Swagger
    regex: \b[\w/]+?((swagger-ui.html)|(\"swagger\":)|(Swagger UI)|(swaggerUi)|(swaggerVersion))\b
    loaded: true
  - name: ID Card
    regex: \b((\d{8}(0\d|10|11|12)([0-2]\d|30|31)\d{3}\$)|(\d{6}(18|19|20)\d{2}(0[1-9]|10|11|12)([0-2]\d|30|31)\d{3}(\d|X|x)))\b
    loaded: true
  - name: Phone
    regex: \b((?:(?:\+|00)86)?1(?:(?:3[\d])|(?:4[5-79])|(?:5[0-35-9])|(?:6[5-7])|(?:7[0-8])|(?:8[\d])|(?:9[189]))\d{8})\b
    loaded: true
  - name: JS Map
    regex: \b([\w/]+?\.js\.map)
    loaded: true
  - name: URL as a Value
    regex: (\b\w+?=(https?)(://|%3a%2f%2f))
    loaded: true
  - name: Email
    regex: \b(([a-z0-9][_|\.])*[a-z0-9]+@([a-z0-9][-|_|\.])*[a-z0-9]+\.([a-z]{2,}))\b
    loaded: true
  - name: Internal IP
    regex: '[^0-9]((127\.0\.0\.1)|(10\.\d{1,3}\.\d{1,3}\.\d{1,3})|(172\.((1[6-9])|(2\d)|(3[01]))\.\d{1,3}\.\d{1,3})|(192\.168\.\d{1,3}\.\d{1,3}))'
    loaded: true
  - name: Cloud Key
    regex: \b((accesskeyid)|(accesskeysecret)|\b(LTAI[a-z0-9]{12,20}))\b
    loaded: true
  - name: Shiro
    regex: (=deleteMe|rememberMe=)
    loaded: true
  - name: Suspicious API Key
    regex: "[\"'][0-9a-zA-Z]{32}['\"]"
    loaded: true
"""
    )

if __name__ == "__main__":
    main()
