from __future__ import annotations

import sys

import click

from netbox_vsphere_sync.cli.commands.sync import sync_command


@click.group()
def cli() -> None:
    pass


cli.add_command(sync_command)


def main() -> None:
    sys.exit(cli())
