import io
import os
import zipfile
import urllib.request
from pathlib import Path
from utils import PROJECT_ROOT

def analyze_github_repo(owner: str, repo: str, branch: str = "main") -> dict:
    """
    Downloads a public GitHub repository zip archive into a local 'repos/' 
    folder within the workspace, allowing other tools to scan and read its files.
    """
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    
    # Create the repos directory if it doesn't exist.
    repos_dir = PROJECT_ROOT / "repos"
    repos_dir.mkdir(exist_ok=True)
    
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "FastMCP-Code-Analyzer"}
        )
        with urllib.request.urlopen(req) as response:
            zip_bytes = response.read()
            
        # Extract directly into the repos folder.
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
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