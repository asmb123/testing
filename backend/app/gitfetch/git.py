from urllib.parse import urlparse
from uuid import uuid4

import requests
from fastapi import HTTPException
from github import Github
from github.GithubException import GithubException


def parse_github_repo(repo: str) -> tuple[str, str]:
    parsed = urlparse(repo)
    if parsed.scheme != "https" or parsed.netloc not in {"github.com", "www.github.com"}:
        raise HTTPException(status_code=400, detail="URL must be a valid https://github.com repository URL")

    path = parsed.path.strip("/").split("/")
    if len(path) != 2 or not path[0] or not path[1]:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub repository URL. Expected format: https://github.com/username/repository",
        )
    return path[0], path[1]


def fetch_github_repo(repo: str, github_token: str):
    user, repo_name = parse_github_repo(repo)
    
    api_url = f"https://api.github.com/repos/{user}/{repo_name}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {"exists": True}
        
        elif response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{user}/{repo_name}' not found. Please check the username and repository name."
            )
        
        elif response.status_code == 401:
            print("GitHub token authentication failed")
            raise HTTPException(
                status_code=500,
                detail="GitHub authentication failed. Please try again later."
            )
        
        elif response.status_code == 403:
            print("GitHub API rate limit exceeded or forbidden")
            raise HTTPException(
                status_code=429,
                detail="GitHub API rate limit exceeded. Please try again later."
            )
            
    
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to GitHub. Please check your internet connection."
        )
    
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )


def create_readme_pull_request(repo_url: str, github_token: str, readme: str) -> dict:
    print("[PR] start: validating repository URL", flush=True)
    owner, repo_name = parse_github_repo(repo_url)
    if not readme.strip():
        raise HTTPException(status_code=400, detail="README content cannot be empty")

    stage = "initializing GitHub client"
    github = Github(github_token)
    try:
        authenticated_user = github.get_user()
        print(f"[PR] authenticated GitHub user: {authenticated_user.login}", flush=True)
        print(f"[PR] repository lookup: {owner}/{repo_name}", flush=True)
        stage = "loading repository"
        repository = github.get_repo(f"{owner}/{repo_name}")
        permissions = repository.permissions
        print(
            "[PR] repository loaded: "
            f"default branch={repository.default_branch}; "
            f"push={getattr(permissions, 'push', None)}; "
            f"admin={getattr(permissions, 'admin', None)}",
            flush=True,
        )
        if permissions is not None and not permissions.push:
            raise HTTPException(
                status_code=403,
                detail="The GitHub token can read this repository but does not have permission to push branches.",
            )
        stage = "loading default branch ref"
        base_branch = repository.default_branch
        base_ref = repository.get_git_ref(f"heads/{base_branch}")
        branch_name = f"docpilot/readme-{uuid4().hex[:10]}"

        print(f"[PR] creating branch: {branch_name}", flush=True)
        stage = "creating branch"
        repository.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
        print("[PR] creating README blob", flush=True)
        stage = "creating README blob"
        blob = repository.create_git_blob(readme, "utf-8")
        print(
            f"[PR] README blob created: sha_type={type(blob.sha).__name__}; sha_length={len(blob.sha or '')}",
            flush=True,
        )
        print("[PR] creating git tree", flush=True)
        stage = "creating git tree"
        api_base = f"https://api.github.com/repos/{owner}/{repo_name}"
        api_headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        tree_response = requests.post(
            f"{api_base}/git/trees",
            headers=api_headers,
            json={
                "base_tree": base_ref.object.sha,
                "tree": [{"path": "README.md", "mode": "100644", "type": "blob", "sha": blob.sha}],
            },
            timeout=20,
        )
        if not tree_response.ok:
            print(f"[PR] git tree response: status={tree_response.status_code}; body={tree_response.text[:500]}", flush=True)
            tree_response.raise_for_status()
        tree_sha = tree_response.json()["sha"]
        print("[PR] creating commit", flush=True)
        stage = "creating commit"
        commit_response = requests.post(
            f"{api_base}/git/commits",
            headers=api_headers,
            json={
                "message": "docs: update README with DocPilot",
                "tree": tree_sha,
                "parents": [base_ref.object.sha],
            },
            timeout=20,
        )
        if not commit_response.ok:
            print(f"[PR] commit response: status={commit_response.status_code}; body={commit_response.text[:500]}", flush=True)
            commit_response.raise_for_status()
        commit_sha = commit_response.json()["sha"]
        print("[PR] updating branch ref", flush=True)
        stage = "updating branch ref"
        ref_response = requests.patch(
            f"{api_base}/git/refs/heads/{branch_name}",
            headers=api_headers,
            json={"sha": commit_sha},
            timeout=20,
        )
        if not ref_response.ok:
            print(f"[PR] ref response: status={ref_response.status_code}; body={ref_response.text[:500]}", flush=True)
            ref_response.raise_for_status()
        print("[PR] opening pull request", flush=True)
        stage = "opening pull request"
        pull_request = repository.create_pull(
            title="docs: update README",
            body="This pull request was generated by DocPilot.",
            head=branch_name,
            base=base_branch,
        )
        print(f"[PR] complete: {pull_request.html_url}", flush=True)
        return {"url": pull_request.html_url, "branch": branch_name}
    except GithubException as error:
        error_data = error.data if isinstance(error.data, dict) else {}
        print(
            f"[PR] failed at {stage}: GitHub status={error.status}; "
            f"message={error_data.get('message', str(error))}; "
            f"documentation={error_data.get('documentation_url', 'n/a')}",
            flush=True,
        )
        if error.status in {401, 403}:
            raise HTTPException(status_code=403, detail="GitHub denied permission to create this pull request") from error
        if error.status == 404:
            raise HTTPException(
                status_code=404,
                detail="GitHub returned 404 while creating the branch. The token likely lacks repository write permission, or the repository is empty.",
            ) from error
        raise HTTPException(status_code=502, detail="GitHub could not create the pull request") from error
    except Exception as error:
        print(f"[PR] failed at {stage}: {type(error).__name__}: {error}", flush=True)
        raise
    finally:
        github.close()
