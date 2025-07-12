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
from rich.progress import Progress

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
        raise typer.Exit()

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
        console.print("[cyan]👤 Let's get your GitHub details![/cyan]")
        username = Prompt.ask("What's your GitHub username?")
        email = Prompt.ask("What's your GitHub email?")
        token = Prompt.ask("What's your GitHub Personal Access Token?", password=True)
        validated_username = validate_pat(token)
        if validated_username:
            username = validated_username
            save_credentials(username, email, token)
            return {"username": username, "email": email, "token": token}
        console.print("[yellow]⚠️ Let's try again.[/yellow]")

def use_or_switch_account():
    """Load saved credentials or switch to a new account."""
    creds = load_credentials()
    if creds:
        console.print(f"[green]✅ Found saved account: {creds['username']} ({creds['email']})[/green]")
        if Confirm.ask("🔄 Want to use a different account?", default=False):
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
    with Progress() as progress:
        task = progress.add_task("[cyan]Creating repository...", total=100)
        response = safe_github_post("https://api.github.com/user/repos", headers, data)
        progress.update(task, advance=100)
    if response.status_code == 201:
        console.print(f"[green]🎉 Repo created: https://github.com/{username}/{repo_name}[/green]")
        return f"https://github.com/{username}/{repo_name}.git"
    raise typer.Exit()

def check_repo_status():
    """Check the current repository status and return relevant actions."""
    actions = []
    result = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        actions.append("init")
        return actions

    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        actions.append("add_remote")

    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        actions.append("commit")

    result = subprocess.run("git log --remotes --pretty=oneline", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        actions.append("push")
    return actions

def add_remote(repo_url: str):
    """Add or replace remote origin."""
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    remotes = result.stdout.strip()
    if "origin" in remotes:
        console.print("[yellow]🔗 Existing remote 'origin' found.[/yellow]")
        if Confirm.ask("⚠️ Want to replace it?", default=True):
            run_cmd("git remote remove origin")
            console.print("[yellow]✅ Removed old remote 'origin'.[/yellow]")
    run_cmd(f"git remote add origin {repo_url}")
    console.print(f"[green]✅ Added new remote: {repo_url}[/green]")

def safe_commit():
    """Stage and commit changes."""
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        console.print("[green]✅ No changes to commit.[/green]")
        return
    console.print("[yellow]⚠️ Found uncommitted changes.[/yellow]")
    if Confirm.ask("Do you want to stage & commit them?", default=True):
        run_cmd("git add .")
        default_msg = f"Update {os.path.basename(os.getcwd())}"
        commit_msg = Prompt.ask("📝 Enter commit message", default=default_msg)
        run_cmd(f'git commit -m "{commit_msg}"')
        console.print("[green]✅ Changes committed![/green]")

def push_to_github():
    """Push committed changes to GitHub."""
    with Progress() as progress:
        task = progress.add_task("[cyan]Pushing to GitHub...", total=100)
        run_cmd("git branch -M main")
        run_cmd("git push -u origin main")
        progress.update(task, advance=100)
    console.print("[cyan]🚀 Code pushed successfully![/cyan]\n")

def conversational_workflow():
    """Main conversational workflow for GitPut."""
    check_git_installed()
    console.print(Panel(
        Align.center(
            Text("🚀 GITPUT – YOUR FRIENDLY GITHUB ASSISTANT", style="bold bright_white on green", justify="center"),
            vertical="middle"
        ),
        title="GitPut",
        subtitle="Your friendly GitHub assistant",
        border_style="blue"
    ))
    console.print("[cyan]👋 Hi! I'm GitPut, here to help with your GitHub project. Let's get started![/cyan]\n")

    creds = use_or_switch_account()
    while True:
        actions = check_repo_status()
        options = []
        if "init" in actions:
            options.append("Initialize a new Git repository")
        if "add_remote" in actions:
            options.append("Connect to a GitHub repository")
        if "commit" in actions:
            options.append("Commit changes")
        if "push" in actions:
            options.append("Push changes to GitHub")
        options.append("Check account status")
        options.append("Reset credentials")
        options.append("Exit")

        console.print("[cyan]❓ What would you like to do?[/cyan]")
        for i, option in enumerate(options, 1):
            console.print(f"[green]{i}. {option}[/green]")
        choice = Prompt.ask("Enter the number of your choice", choices=[str(i) for i in range(1, len(options) + 1)])

        if options[int(choice) - 1] == "Initialize a new Git repository":
            run_cmd("git init")
            console.print("[green]✅ Initialized a new Git repository![/green]")
        
        elif options[int(choice) - 1] == "Connect to a GitHub repository":
            if Confirm.ask("📂 Want to create a new GitHub repo?", default=True):
                default_name = os.path.basename(os.getcwd())
                repo_name = Prompt.ask("📁 Enter new repo name", default=default_name)
                private = Confirm.ask("🔒 Should the repo be private?", default=False)
                repo_url = create_github_repo(creds["username"], creds["token"], repo_name, private)
                add_remote(repo_url)
            else:
                repo_url = Prompt.ask("🌐 Enter existing GitHub repo URL")
                add_remote(repo_url)
        
        elif options[int(choice) - 1] == "Commit changes":
            safe_commit()
        
        elif options[int(choice) - 1] == "Push changes to GitHub":
            push_to_github()
        
        elif options[int(choice) - 1] == "Check account status":
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
        
        elif options[int(choice) - 1] == "Reset credentials":
            if os.path.exists(GLOBAL_CONFIG):
                os.remove(GLOBAL_CONFIG)
                console.print("[yellow]✅ Global credentials reset successfully.[/yellow]")
            elif os.path.exists(LOCAL_CONFIG):
                os.remove(LOCAL_CONFIG)
                console.print("[yellow]✅ Project credentials reset successfully.[/yellow]")
            else:
                console.print("[red]⚠️ No credentials to reset.[/red]")
        
        elif options[int(choice) - 1] == "Exit":
            console.print("[cyan]👋 Thanks for using GitPut! Bye![/cyan]")
            break

        if not Confirm.ask("❓ Want to do something else?", default=True):
            console.print("[cyan]👋 Thanks for using GitPut! Bye![/cyan]")
            break

@app.callback(invoke_without_command=True)
def main():
    """Run the conversational workflow."""
    conversational_workflow()

if __name__ == "__main__":
    app()