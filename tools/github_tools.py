import io
import os
import re
import zipfile
import urllib.request
from pathlib import Path
from utils import PROJECT_ROOT

# Bounds on untrusted third-party archives.
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024       # 100 MB compressed
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024   # 500 MB expanded
MAX_MEMBERS = 20_000

# GitHub owner/repo charset; a branch may additionally contain '/'.
SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

def analyze_github_repo(owner: str, repo: str, branch: str = "main") -> dict:
    """
    Downloads a public GitHub repository zip archive into a local 'repos/'
    folder within the workspace, allowing other tools to scan and read its files.
    """
    # Validate before interpolating into the URL, so a crafted owner/repo/branch
    # cannot redirect the request to an unrelated path on github.com.
    if not SEGMENT_RE.match(owner) or not SEGMENT_RE.match(repo):
        return {"error": "Invalid owner or repo name."}
    if not BRANCH_RE.match(branch) or ".." in branch:
        return {"error": "Invalid branch name."}

    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    # Create the repos directory if it doesn't exist.
    repos_dir = (PROJECT_ROOT / "repos").resolve()
    repos_dir.mkdir(exist_ok=True)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FastMCP-Code-Analyzer"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            # Read one byte past the cap so an oversized body is detectable.
            zip_bytes = response.read(MAX_DOWNLOAD_BYTES + 1)

        if len(zip_bytes) > MAX_DOWNLOAD_BYTES:
            return {"error": f"Archive exceeds the {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB download limit."}

        # Extract directly into the repos folder.
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            infos = z.infolist()

            if len(infos) > MAX_MEMBERS:
                return {"error": f"Archive contains more than {MAX_MEMBERS} entries."}

            # Declared uncompressed sizes. A crafted archive can under-report these,
            # so this bounds naive zip bombs rather than adversarial ones; the
            # download cap above is the real backstop.
            if sum(i.file_size for i in infos) > MAX_UNCOMPRESSED_BYTES:
                return {"error": f"Archive expands to more than {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB."}

            # Assert containment explicitly. CPython's extractall already strips
            # '..', leading separators and drive letters, but stating the property
            # here means the guarantee does not rest on that implementation detail,
            # and a hostile archive is refused outright instead of silently rewritten.
            for info in infos:
                destination = (repos_dir / info.filename).resolve()
                if not destination.is_relative_to(repos_dir):
                    return {"error": f"Refused archive: entry '{info.filename}' resolves outside 'repos/'."}

            z.extractall(repos_dir)
            
        extracted_folder_name = f"{repo}-{branch}"
        relative_sandbox_path = f"repos/{extracted_folder_name}"
        
        return {
            "status": "success",
            "repo": f"{owner}/{repo}",
            "branch": branch,
            "local_path": relative_sandbox_path,
            "instructions": f"Repository extracted. You can now use scan_directory('{relative_sandbox_path}') to explore it."
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch repository '{owner}/{repo}': {str(e)}"}