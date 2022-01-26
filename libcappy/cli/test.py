import typer
import os
app = typer.Typer()

@app.command()
def test():
    print("test")