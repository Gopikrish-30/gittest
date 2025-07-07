import subprocess
import requests
import click
import json
import os
from colorama import Fore, Style

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".gitput_config.json")

def run_cmd(command):
    """Run terminal commands and print output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(Fore.GREEN + result.stdout.strip() + Style.RESET_ALL)
    else:
        print(Fore.RED + "❌ Error: " + result.stderr.strip() + Style.RESET_ALL)

def save_credentials(username, email, token):
    """Save GitHub credentials to global config file."""
    data = {"username": username, "email": email, "token": token}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)
    click.echo(Fore.GREEN + "✅ Credentials saved for future sessions.\n" + Style.RESET_ALL)

def load_credentials():
    """Load GitHub credentials if config exists."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def ask_credentials():
    """Prompt user for GitHub credentials and save them."""
    username = click.prompt("👤 Enter your GitHub username")
    email = click.prompt("📧 Enter your GitHub email")
    token = click.prompt("🔑 Enter your GitHub Personal Access Token")
    save_credentials(username, email, token)
    return {"username": username, "email": email, "token": token}

def use_or_switch_account():
    """Load or switch GitHub credentials."""
    creds = load_credentials()
    if creds:
        click.echo(Fore.GREEN + f"✅ Using saved GitHub account: {creds['username']}\n" + Style.RESET_ALL)
        if click.confirm("🔄 Do you want to switch to a different account?", default=False):
            creds = ask_credentials()
    else:
        click.echo(Fore.YELLOW + "🆕 No saved credentials found.\n" + Style.RESET_ALL)
        creds = ask_credentials()
    subprocess.run(f'git config --global user.name "{creds["username"]}"', shell=True)
    subprocess.run(f'git config --global user.email "{creds["email"]}"', shell=True)
    return creds

def create_github_repo(username, token, repo_name, private):
    """Create a new GitHub repository."""
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": private}
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    if response.status_code == 201:
        click.echo(Fore.GREEN + f"🎉 Repo created: https://github.com/{username}/{repo_name}" + Style.RESET_ALL)
        add_remote(f"https://github.com/{username}/{repo_name}.git")
    else:
        click.echo(Fore.RED + "❌ Failed to create repo: " + str(response.json()) + Style.RESET_ALL)

def add_remote(repo_url):
    """Add GitHub remote and handle existing remote."""
    # Check if we're inside a git repo
    result = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        click.echo(Fore.YELLOW + "📂 No git repo found. Initializing..." + Style.RESET_ALL)
        run_cmd("git init")

    # Check for existing remote
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    remotes = result.stdout.strip()

    if "origin" in remotes:
        # Show existing origin URL
        origin_urls = [
            line.split() for line in remotes.split("\n") if line.startswith("origin")
        ]
        click.echo(Fore.YELLOW + "🔗 Existing remote 'origin':" + Style.RESET_ALL)
        for url in origin_urls:
            click.echo(Fore.CYAN + f"• {url[1]} ({url[2]})" + Style.RESET_ALL)

        if click.confirm("⚠️ Remote 'origin' exists. Do you want to remove it?", default=True):
            run_cmd("git remote remove origin")
            click.echo(Fore.YELLOW + "✅ Removed old remote 'origin'." + Style.RESET_ALL)
        else:
            click.echo(Fore.GREEN + "✅ Keeping existing remote 'origin'." + Style.RESET_ALL)
            return  # Exit without adding new remote

    # Add new remote
    run_cmd(f"git remote add origin {repo_url}")
    click.echo(Fore.GREEN + f"✅ Added new remote: {repo_url}" + Style.RESET_ALL)


def safe_commit():
    """Stage and commit changes."""
    run_cmd("git add .")
    commit_msg = click.prompt("📝 Enter commit message", default="Initial commit")
    run_cmd(f'git commit -m "{commit_msg}"')

def push_to_github():
    """Push code to GitHub."""
    run_cmd("git branch -M main")
    run_cmd("git push -u origin main")
    click.echo(Fore.CYAN + "🚀 Code pushed successfully!\n" + Style.RESET_ALL)

@click.command()
def gitput():
    """Main assistant UI."""
    click.echo(Fore.CYAN + "👋 Welcome to GitPut – your friendly Git assistant!\n" + Style.RESET_ALL)

    while True:
        choice = click.prompt(
            "👉 What do you want to do?\n"
            "1️⃣ Start pushing code\n"
            "2️⃣ View saved GitHub account\n"
            "3️⃣ Switch GitHub account\n"
            "4️⃣ Reset credentials\n"
            "5️⃣ Exit\n"
            "Enter 1-5",
            type=int
        )

        if choice == 1:
            creds = use_or_switch_account()
            if click.confirm("📂 Do you want to create a new GitHub repo?", default=True):
                repo_name = click.prompt("📁 Enter new repo name")
                private = click.confirm("🔒 Should the repo be private?")
                create_github_repo(creds["username"], creds["token"], repo_name, private)
            else:
                repo_url = click.prompt("🌐 Enter existing GitHub repo URL")
                add_remote(repo_url)
            safe_commit()
            if click.confirm("🚀 Push code to GitHub now?", default=True):
                push_to_github()
        elif choice == 2:
            creds = load_credentials()
            if creds:
                click.echo(Fore.GREEN + f"👤 GitHub: {creds['username']}\n📧 Email: {creds['email']}\n" + Style.RESET_ALL)
            else:
                click.echo(Fore.RED + "⚠️ No credentials saved.\n" + Style.RESET_ALL)
        elif choice == 3:
            ask_credentials()
        elif choice == 4:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                click.echo(Fore.YELLOW + "🔄 Credentials reset.\n" + Style.RESET_ALL)
            else:
                click.echo(Fore.RED + "⚠️ No credentials to reset.\n" + Style.RESET_ALL)
        elif choice == 5:
            click.echo(Fore.CYAN + "👋 Goodbye! Happy coding! ✨\n" + Style.RESET_ALL)
            break
        else:
            click.echo(Fore.RED + "❌ Invalid choice. Try again.\n" + Style.RESET_ALL)

if __name__ == "__main__":
    gitput()
