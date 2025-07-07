import subprocess
import requests
import click
import json
import os
from colorama import Fore, Style

# Global config file path (saved in user home directory)
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".gitput_config.json")

def run_cmd(command):
    """Run terminal commands and print output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(Fore.GREEN + result.stdout + Style.RESET_ALL)
    else:
        print(Fore.RED + "❌ Error: " + result.stderr + Style.RESET_ALL)

def save_credentials(username, email, token):
    """Save GitHub credentials to global config file."""
    data = {"username": username, "email": email, "token": token}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)
    click.echo(Fore.GREEN + "✅ Credentials saved for future sessions.\n" + Style.RESET_ALL)

def load_credentials():
    """Load GitHub credentials from config if exists."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def ask_and_save_credentials():
    """Prompt user for GitHub credentials and save them."""
    username = click.prompt("👤 Enter your GitHub username")
    email = click.prompt("📧 Enter your GitHub email")
    token = click.prompt("🔑 Enter your GitHub Personal Access Token")
    save_credentials(username, email, token)
    return {"username": username, "email": email, "token": token}

def get_credentials():
    """Get saved credentials or ask for new ones."""
    creds = load_credentials()
    if creds:
        click.echo(Fore.GREEN + f"✅ Using saved GitHub account: {creds['username']}\n" + Style.RESET_ALL)
        if click.confirm("🔄 Do you want to switch GitHub account?", default=False):
            creds = ask_and_save_credentials()
    else:
        click.echo(Fore.YELLOW + "🆕 No saved credentials found.\n" + Style.RESET_ALL)
        creds = ask_and_save_credentials()
    return creds

@click.group()
def cli():
    """GitPut – Your Git assistant."""
    click.echo(Fore.CYAN + "👋 Welcome to GitPut – your Git assistant!\n" + Style.RESET_ALL)

@cli.command()
def reset():
    """Reset saved GitHub credentials."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        click.echo(Fore.YELLOW + "🔄 Credentials reset successfully." + Style.RESET_ALL)
    else:
        click.echo(Fore.RED + "⚠️ No saved credentials to reset." + Style.RESET_ALL)

@cli.command()
def status():
    """Show current saved GitHub account."""
    creds = load_credentials()
    if creds:
        click.echo(Fore.GREEN + f"👤 Saved GitHub account: {creds['username']}\n📧 Email: {creds['email']}" + Style.RESET_ALL)
    else:
        click.echo(Fore.RED + "⚠️ No credentials saved." + Style.RESET_ALL)

@cli.command()
def start():
    """Start GitPut workflow (create/connect repo and push code)."""
    creds = get_credentials()
    subprocess.run(f'git config --global user.name "{creds["username"]}"', shell=True)
    subprocess.run(f'git config --global user.email "{creds["email"]}"', shell=True)

    choice = click.prompt(
        "What do you want to do?\n1️⃣ Create NEW Repo\n2️⃣ Connect EXISTING Repo\nEnter 1 or 2", 
        type=int
    )

    if choice == 1:
        repo_name = click.prompt("📂 Enter new repo name")
        private = click.confirm("🔒 Should the repo be private?")
        create_github_repo(creds["username"], creds["token"], repo_name, private)
    else:
        repo_url = click.prompt("🌐 Enter your existing repo URL")
        add_remote(repo_url)

    if click.confirm("✅ Do you want to stage all files?", default=True):
        run_cmd("git add .")
    commit_msg = click.prompt("📝 Enter your commit message")
    safe_commit(commit_msg)

    if click.confirm("🚀 Do you want to push to GitHub now?", default=True):
        run_cmd("git branch -M main")
        run_cmd("git push -u origin main")
        click.echo(Fore.CYAN + "🎉 Success! Your code was pushed to GitHub.\n" + Style.RESET_ALL)

def create_github_repo(username, token, repo_name, private):
    """Create a new GitHub repository."""
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": private}
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if response.status_code == 201:
        click.echo(Fore.GREEN + f"🎉 Repo created successfully: https://github.com/{username}/{repo_name}" + Style.RESET_ALL)
        add_remote(f"https://github.com/{username}/{repo_name}.git")
    else:
        click.echo(Fore.RED + "❌ Failed to create repo: " + str(response.json()) + Style.RESET_ALL)

def add_remote(repo_url):
    """Add GitHub remote and handle existing remote."""
    result = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        click.echo(Fore.YELLOW + "📂 Not a git repository. Initializing..." + Style.RESET_ALL)
        run_cmd("git init")
    
    result = subprocess.run("git remote", shell=True, capture_output=True, text=True)
    if "origin" in result.stdout:
        if click.confirm("⚠️ Remote 'origin' exists. Remove it?", default=True):
            run_cmd("git remote remove origin")
            click.echo(Fore.YELLOW + "✅ Removed old remote." + Style.RESET_ALL)
    run_cmd(f"git remote add origin {repo_url}")
    click.echo(Fore.GREEN + f"✅ Added remote: {repo_url}" + Style.RESET_ALL)

def safe_commit(message):
    """Commit changes safely."""
    run_cmd(f'git commit -m "{message}"')

if __name__ == "__main__":
    cli()
