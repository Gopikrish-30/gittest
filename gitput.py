import subprocess
import requests
import click
from colorama import Fore, Style
from getpass import getpass

def run_cmd(command):
    """Run terminal commands."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(Fore.GREEN + result.stdout + Style.RESET_ALL)
    else:
        print(Fore.RED + "❌ Error: " + result.stderr + Style.RESET_ALL)

@click.command()
def gitput():
    click.echo(Fore.CYAN + "👋 Welcome to GitPut – your Git assistant!\n" + Style.RESET_ALL)
    
    choice = click.prompt("What do you want to do?\n1️⃣ Create NEW Repo\n2️⃣ Connect EXISTING Repo\nEnter 1 or 2", type=int)

    username = click.prompt("👤 Enter your GitHub username")
    email = click.prompt("📧 Enter your GitHub email")
    subprocess.run(f'git config --global user.name "{username}"', shell=True)
    subprocess.run(f'git config --global user.email "{email}"', shell=True)

    if choice == 1:
        token = click.prompt("🔑 Enter your GitHub Personal Access Token")
        repo_name = click.prompt("📂 Enter new repo name")
        private = click.confirm("🔒 Should the repo be private?")
        create_github_repo(username, token, repo_name, private)
    else:
        repo_url = click.prompt("🌐 Enter your existing repo URL")
        add_remote(repo_url)
    
    if click.confirm("✅ Do you want to stage all files?"):
        run_cmd("git add .")
    commit_msg = click.prompt("📝 Enter your commit message")
    run_cmd(f'git commit -m "{commit_msg}"')

    if click.confirm("🚀 Do you want to push to GitHub now?"):
        run_cmd("git push -u origin main")

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
    # Check if we are in a git repo
    result = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        click.echo(Fore.YELLOW + "📂 Not a git repository. Initializing..." + Style.RESET_ALL)
        run_cmd("git init")  # Initialize git repo
    
    # Check for existing remote
    result = subprocess.run("git remote", shell=True, capture_output=True, text=True)
    if "origin" in result.stdout:
        if click.confirm("⚠️ Remote 'origin' exists. Remove it?"):
            run_cmd("git remote remove origin")
            click.echo(Fore.YELLOW + "✅ Removed old remote." + Style.RESET_ALL)
    run_cmd(f"git remote add origin {repo_url}")
    click.echo(Fore.GREEN + f"✅ Added remote: {repo_url}" + Style.RESET_ALL)

if __name__ == "__main__":
    gitput()
