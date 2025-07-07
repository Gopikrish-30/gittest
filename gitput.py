import subprocess
import requests
import typer
import json
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

app = typer.Typer(help="🚀 GitPut – Your friendly GitHub assistant!")
console = Console()

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".gitput_config.json")

def run_cmd(command: str):
    """Run terminal commands and print output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"[green]{result.stdout.strip()}[/green]")
    else:
        console.print(f"[red]❌ Error: {result.stderr.strip()}[/red]")

def save_credentials(username: str, email: str, token: str):
    """Save GitHub credentials to config file."""
    data = {"username": username, "email": email, "token": token}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)
    console.print("[green]✅ Credentials saved for future sessions.[/green]\n")

def load_credentials():
    """Load saved credentials if available."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def ask_credentials():
    """Prompt user for GitHub credentials and save them."""
    username = Prompt.ask("👤 Enter your GitHub username")
    email = Prompt.ask("📧 Enter your GitHub email")
    token = Prompt.ask("🔑 Enter your GitHub Personal Access Token", password=True)
    save_credentials(username, email, token)
    return {"username": username, "email": email, "token": token}

def use_or_switch_account():
    """Load saved credentials or switch to a new account."""
    creds = load_credentials()
    if creds:
        console.print(f"[green]✅ Using saved account: {creds['username']} ({creds['email']})[/green]")
        if Confirm.ask("🔄 Do you want to switch to a different account?", default=False):
            creds = ask_credentials()
    else:
        console.print("[yellow]🆕 No saved credentials found.[/yellow]")
        creds = ask_credentials()
    subprocess.run(f'git config --global user.name "{creds["username"]}"', shell=True)
    subprocess.run(f'git config --global user.email "{creds["email"]}"', shell=True)
    return creds

def create_github_repo(username: str, token: str, repo_name: str, private: bool):
    """Create a new GitHub repository."""
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": private}
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if response.status_code == 201:
        console.print(f"[green]🎉 Repo created: https://github.com/{username}/{repo_name}[/green]")
        add_remote(f"https://github.com/{username}/{repo_name}.git")
    else:
        console.print(f"[red]❌ Failed to create repo: {response.json()}[/red]")

def add_remote(repo_url: str):
    """Add or replace remote origin."""
    result = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[yellow]📂 No git repo found. Initializing...[/yellow]")
        run_cmd("git init")

    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    remotes = result.stdout.strip()

    if "origin" in remotes:
        console.print("[yellow]🔗 Existing remote 'origin':[/yellow]")
        for line in remotes.split("\n"):
            if line.startswith("origin"):
                console.print(f"[cyan]• {line}[/cyan]")
        if Confirm.ask("⚠️ Remote 'origin' exists. Do you want to remove it?", default=True):
            run_cmd("git remote remove origin")
            console.print("[yellow]✅ Removed old remote 'origin'.[/yellow]")
        else:
            console.print("[green]✅ Keeping existing remote 'origin'.[/green]")
            return

    run_cmd(f"git remote add origin {repo_url}")
    console.print(f"[green]✅ Added new remote: {repo_url}[/green]")

def safe_commit():
    """Stage and commit changes."""
    run_cmd("git add .")
    commit_msg = Prompt.ask("📝 Enter commit message", default="Initial commit")
    run_cmd(f'git commit -m "{commit_msg}"')

def push_to_github():
    """Push committed changes to GitHub."""
    run_cmd("git branch -M main")
    run_cmd("git push -u origin main")
    console.print("[cyan]🚀 Code pushed successfully![/cyan]\n")

@app.command()
def start():
    """✨ Start workflow: Create/Connect repo and push code."""
    creds = use_or_switch_account()

    if Confirm.ask("📂 Do you want to create a new GitHub repo?", default=True):
        repo_name = Prompt.ask("📁 Enter new repo name")
        private = Confirm.ask("🔒 Should the repo be private?", default=False)
        create_github_repo(creds["username"], creds["token"], repo_name, private)
    else:
        repo_url = Prompt.ask("🌐 Enter existing GitHub repo URL")
        add_remote(repo_url)

    safe_commit()
    if Confirm.ask("🚀 Push code to GitHub now?", default=True):
        push_to_github()

@app.command()
def status():
    """📄 View saved GitHub account."""
    creds = load_credentials()
    if creds:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("👤 Username", creds["username"])
        table.add_row("📧 Email", creds["email"])
        console.print(table)
    else:
        console.print("[red]⚠️ No credentials saved.[/red]")

@app.command()
def reset():
    """🔄 Reset saved GitHub credentials."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        console.print("[yellow]✅ Credentials reset successfully.[/yellow]")
    else:
        console.print("[red]⚠️ No credentials to reset.[/red]")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🎉 Welcome to GitPut!"""
    if ctx.invoked_subcommand is None:
        console.print("[bold magenta]🎉 Welcome to GitPut – your friendly GitHub assistant![/bold magenta]\n")
        console.print("👉 [cyan]Tip:[/cyan] Run [green]gitput start[/green] to create/connect and push code.")
        console.print("👉 [cyan]Other commands:[/cyan] [green]status[/green], [green]reset[/green]\n")
        # Automatically call start if desired
        if Confirm.ask("🚀 Do you want to start now?", default=True):
            start()

if __name__ == "__main__":
    app()
