import typer
import os
import libcappy.installer as installer
app = typer.Typer()

@app.command()
def fstab(
    config: str = typer.Argument(..., help='Path to dnfstrap.yml'),
):
    """
    Calls the libcappy installer to bootstrap the system.
    """
    inst = installer.Installer(config=config)
    fs = inst.cfgparse.fstab()
    inst.fstab(fs)