import hashlib
from pathlib import PurePosixPath
from urllib.parse import urlparse

from github import Github
from fastapi import HTTPException

from app.core.redis_cache import get_cache, set_cache

MAX_README_CANDIDATE_PATHS = 120
IGNORED_DIRECTORIES = {
    ".git", ".idea", ".next", ".nuxt", ".venv",
    ".vscode", "__pycache__", "build", "coverage", "dist", "node_modules",
    "out", "target", "test", "tests", "vendor", "venv",
}
IMPORTANT_FILENAMES = {
    "README.md", "README.rst", "README.txt",
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
    "go.mod", "Cargo.toml", "pom.xml", "composer.json",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
    ".env.example", ".env.sample", "env.example", "Makefile",
    "Jenkinsfile", ".gitlab-ci.yml",
}
ENTRYPOINT_FILENAMES = {
    "main.py", "app.py", "server.py",
    "index.js", "main.js", "server.js", "index.ts", "main.ts",
}


def readme_candidate_paths(paths: list[str]) -> list[str]:
    """Return a bounded, high-signal set of paths for README analysis.
       Lock files, source trees, tests, build output, and binary assets add many
       tokens without normally improving a README.
    """
    candidates: list[tuple[int, str]] = []

    for path in paths:
        file_path = PurePosixPath(path)
        parts = file_path.parts
        filename = file_path.name
        parent_directories = set(parts[:-1])

        if parent_directories & IGNORED_DIRECTORIES or path.startswith(".github/ISSUE_TEMPLATE/"):
            continue
        if filename in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "Gemfile.lock", "go.sum"}:
            continue

        depth = len(parts) - 1
        if filename in IMPORTANT_FILENAMES:
            candidates.append((0 if depth == 0 else 1, path))
        elif filename in ENTRYPOINT_FILENAMES and depth <= 2:
            candidates.append((2, path))
        elif path.startswith(".github/workflows/") and filename in {"main.yml", "main.yaml", "ci.yml", "ci.yaml", "deploy.yml", "deploy.yaml"}:
            candidates.append((3, path))

    candidates.sort(key=lambda item: (item[0], item[1].lower()))
    return [path for _, path in candidates[:MAX_README_CANDIDATE_PATHS]]

def file_system(repo_url: str, github_token: str):
    token_id = hashlib.sha256(github_token.encode()).hexdigest()[:16]
    key = f"repourl:v2:{token_id}:{repo_url}"
    cache_data = get_cache(key)
    if cache_data:
        print("returning the data from caches")
        return cache_data

    path = urlparse(repo_url).path.strip("/").split("/")
    user = path[0]
    repo_name = path[1]
    full_repo_name = f"{user}/{repo_name}"

    github = Github(github_token)
    repo = github.get_repo(full_repo_name)

    if repo.private:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PRIVATE_REPOSITORY_NOT_ALLOWED",
                "message": "Private repositories cannot be accessed.",
            },
        )

    tree = repo.get_git_tree(repo.default_branch, recursive=True)
    all_paths = [item.path for item in tree.tree if item.type == "blob"]
    metadata = {
        "repo": repo.full_name,
        "files": [
            {"path": path, "name": path.rsplit("/", 1)[-1]}
            for path in readme_candidate_paths(all_paths)
        ],
    }

    if tree.truncated:
        raise ValueError("Repository is too large to list completely.")

    set_cache(key, metadata)
    return metadata
