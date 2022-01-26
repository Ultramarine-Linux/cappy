from construct import Optional
from platformdirs import importlib
import typer
import sys
import os
import libcappy.packages as packages
import libcappy.installer as installer

app = typer.Typer()
# Dynamically import the commands
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py' or module == '__main__.py':
        continue
    mod = importlib.import_module(f'libcappy.cli.{module[:-3]}')
    app.add_typer(mod.app, name=module[:-3])

@app.command()
def install(
    # package can be seperated by space
    package: str = typer.Argument(..., help='Package to install'),
):
    """Install a package"""
    pkg = packages.Packages()
    print(f'Installing {package}')
    #pkg.install([package])
    pkg.update()
@app.command()
def bootstrap(
    config: str = typer.Argument(..., help='Path to dnfstrap.yml'),
    postinst: bool = typer.Option(True, '--postinst', '-p', help='Run postinst script'),
):
    """
    Calls the libcappy installer to bootstrap the system.
    """
    inst = installer.Installer(config=config)
    typer.echo(f'Bootstrapping system with {config}...')
    inst.instRoot()
    if postinst:
        inst.postInstall()

if __name__ == "__main__":
    app()