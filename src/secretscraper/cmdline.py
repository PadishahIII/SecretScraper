"""Command line"""

import click
from click import Context

from secretscraper import __version__
from secretscraper.config import settings
from secretscraper.log import init_log


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "-V", "--version", is_flag=True, help="Show version and exit."
)  # If it's true, it will override `settings.VERBOSE`
@click.option("-v", "--verbose", is_flag=True, help="Show more info.")
@click.option(
    "--debug", is_flag=True, help="Enable debug."
)  # If it's true, it will override `settings.DEBUG`
def main(ctx: Context, version: str, verbose: bool, debug: bool):
    """Main commands"""
    if version:
        click.echo(__version__)
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    else:
        if verbose:
            settings.set("VERBOSE", True)
        if debug:
            settings.set("DEBUG", True)


@main.command()
def run():
    """Run command"""
    init_log()
    click.echo("run......")
