import subprocess
import requests
import typer
import json
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

app = typer.Typer(help="🚀 GitPut – Your friendly GitHub assistant!")
console = Console()

GLOBAL_CONFIG = os.path.join(os.path.expanduser("~"), ".gitput_config.json")
LOCAL_CONFIG = os.path.join(os.getcwd(), ".gitput_config.json")

def check_git_installed():
    """Check if Git is installed."""
    result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[red]❌ Git is not installed or not in PATH. Please download Git from https://git-scm.com/downloads.[/red]")
        raise typer.Exit()

def run_cmd(command: str):
    """Run terminal commands and print output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        if result.stdout.strip():
            console.print(f"[green]{result.stdout.strip()}[/green]")
    else:
        console.print(f"[red]❌ Error: {result.stderr.strip()}[/red]")

def save_credentials(username: str, email: str, token: str):
    """Save GitHub credentials to config file."""
    data = {"username": username, "email": email, "token": token}
    config_file = LOCAL_CONFIG if Confirm.ask("💼 Save credentials to this project only?", default=False) else GLOBAL_CONFIG
    with open(config_file, "w") as f:
        json.dump(data, f)
    console.print(f"[green]✅ Credentials saved to {config_file}[/green]\n")

def load_credentials():
    """Load saved credentials if available."""
    if os.path.exists(LOCAL_CONFIG):
        with open(LOCAL_CONFIG, "r") as f:
            return json.load(f)
    elif os.path.exists(GLOBAL_CONFIG):
        with open(GLOBAL_CONFIG, "r") as f:
            return json.load(f)
    return None

def validate_pat(token: str):
    """Check if the Personal Access Token is valid."""
    headers = {"Authorization": f"token {token}"}
    try:
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        response.raise_for_status()
        username = response.json()["login"]
        console.print(f"[green]✅ PAT is valid. Logged in as {username}[/green]")
        return username
    except requests.exceptions.Timeout:
        console.print("[red]⏳ GitHub API timed out. Please check your connection.[/red]")
        raise typer.Exit()
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]❌ GitHub error: {e.response.status_code} - {e.response.json().get('message')}[/red]")
        raise typer.Exit()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit()

def ask_credentials():
    """Prompt user for GitHub credentials and validate PAT."""
    while True:
        username = Prompt.ask("👤 Enter your GitHub username")
        email = Prompt.ask("📧 Enter your GitHub email")
        token = Prompt.ask("🔑 Enter your GitHub Personal Access Token", password=True)
        validated_username = validate_pat(token)
        if validated_username:
            username = validated_username
            save_credentials(username, email, token)
            return {"username": username, "email": email, "token": token}
        else:
            console.print("[yellow]⚠️ Let's try again.[/yellow]")

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

def safe_github_post(url, headers, data):
    """Post to GitHub API with error handling."""
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        console.print("[red]⏳ GitHub API timed out. Please check your connection.[/red]")
        raise typer.Exit()
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]❌ GitHub error: {e.response.status_code} - {e.response.json().get('message')}[/red]")
        raise typer.Exit()
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit()

def create_github_repo(username: str, token: str, repo_name: str, private: bool):
    """Create a new GitHub repository."""
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": private}
    response = safe_github_post("https://api.github.com/user/repos", headers, data)
    if response.status_code == 201:
        console.print(f"[green]🎉 Repo created: https://github.com/{username}/{repo_name}[/green]")
        add_remote(f"https://github.com/{username}/{repo_name}.git")

def warn_uncommitted_changes():
    """Warn if uncommitted changes are present."""
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        console.print("[yellow]⚠️ You have uncommitted changes.[/yellow]")
        if not Confirm.ask("Do you want to stage & commit them?", default=True):
            console.print("[red]🚨 Cannot proceed without committing changes.[/red]")
            raise typer.Exit()

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

    run_cmd(f"git remote add origin {repo_url}")
    console.print(f"[green]✅ Added new remote: {repo_url}[/green]")

def safe_commit():
    """Stage and commit changes."""
    warn_uncommitted_changes()
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
    check_git_installed()
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
    if os.path.exists(GLOBAL_CONFIG):
        os.remove(GLOBAL_CONFIG)
        console.print("[yellow]✅ Global credentials reset successfully.[/yellow]")
    elif os.path.exists(LOCAL_CONFIG):
        os.remove(LOCAL_CONFIG)
        console.print("[yellow]✅ Project credentials reset successfully.[/yellow]")
    else:
        console.print("[red]⚠️ No credentials to reset.[/red]")

@app.command()
def version():
    """Show GitPut version."""
    console.print("[bold cyan]GitPut v1.0.0[/bold cyan] 🚀")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🎉 Welcome to GitPut!"""
    check_git_installed()
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            Align.center(
                Text("🚀 GITPUT – YOUR FRIENDLY GITHUB ASSISTANT", style="bold bright_white on green", justify="center"),
                vertical="middle"
            ),
            title="GitPut",
            subtitle="Your friendly GitHub assistant",
            border_style="blue"
        ))

        console.print("👉 [cyan]Tip:[/cyan] Run [green]gitput start[/green] to create/connect and push code.")
        console.print("👉 [cyan]Other commands:[/cyan] [green]status[/green], [green]reset[/green], [green]version[/green]\n")
        if Confirm.ask("🚀 Do you want to start now?", default=True):
            start()


if __name__ == "__main__":
    app()
