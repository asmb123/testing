from typing_extensions import List, Dict, TypedDict

from app.gitfetch.readfile import read_file

MAX_FILES_FOR_README = 12
MAX_CHARS_PER_FILE = 20_000
MAX_TOTAL_CHARS = 80_000


class dat_response(TypedDict):
    raw_data: List[Dict[str,str]]


def _truncate(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    suffix = "\n\n[Content truncated to keep README generation focused.]"
    if limit <= len(suffix):
        return content[:limit]
    return f"{content[:limit - len(suffix)]}{suffix}"


def storingdata(data, github_token: str) -> dat_response:
    """Fetch bounded file content selected by the repository analyzer.

    A failed GitHub read is skipped instead of returning an invalid response
    shape.  This lets README generation continue with the other useful files.
    """
    repo = data["repo"]
    selected_paths = list(dict.fromkeys(data.get("readme_imp", [])))
    raw_content: List[Dict[str, str]] = []
    total_chars = 0

    for path in selected_paths[:MAX_FILES_FOR_README]:
        content = read_file(repo, path, github_token)
        if not content:
            print(f"Skipping unreadable README candidate: {path}")
            continue

        remaining_chars = MAX_TOTAL_CHARS - total_chars
        if remaining_chars <= 0:
            break

        content = _truncate(content, min(MAX_CHARS_PER_FILE, remaining_chars))
        raw_content.append({"path": path, "content": content})
        total_chars += len(content)

    return {"raw_data": raw_content}
