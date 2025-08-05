"""Configuration management commands."""
import click

from ..config import get_config, Config, dump_config_toml, dump_config_env


@click.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.option('--format', 'output_format', default='toml',
              type=click.Choice(['toml', 'env']),
              help='Output format (toml or env)')
def show(output_format):
    """Show current effective configuration."""
    current_config = get_config()

    if output_format == 'toml':
        click.echo(dump_config_toml(current_config))
    else:
        click.echo(dump_config_env(current_config))


@config.command()
@click.option('--format', 'output_format', default='toml',
              type=click.Choice(['toml', 'env']),
              help='Output format (toml or env)')
def defaults(output_format):
    """Show default configuration values."""
    default_config = Config()

    if output_format == 'toml':
        click.echo(dump_config_toml(default_config))
    else:
        click.echo(dump_config_env(default_config))
