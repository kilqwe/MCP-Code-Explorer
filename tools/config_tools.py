import sys
import time
import json
from utils import resolve_safe_path

MANIFEST_FRAMEWORK_SIGNALS = {
    "package.json": {
        "next": "Next.js", "react": "React", "vue": "Vue",
        "express": "Express", "@angular/core": "Angular",
    },
    "requirements.txt": {
        "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
    },
    "pyproject.toml": {
        "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
    },
}

CONFIG_FILE_CANDIDATES = [
    ".env.example", ".env", "docker-compose.yml", "pytest.ini",
    "tsconfig.json", ".eslintrc.json", ".eslintrc.js", ".prettierrc",
    "vite.config.js", "vite.config.ts", "next.config.js", "next.config.ts",
    "tailwind.config.js",
]

BUILD_CI_CANDIDATES = ["Makefile", "Dockerfile", ".gitlab-ci.yml"]


def _read_text_safe(path):
    raw = path.read_bytes()
    # Detect UTF-16 by BOM (Byte Order Mark)
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        try:
            return raw.decode("utf-16")
        except Exception:
            pass
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("utf-8", errors="replace")

def get_project_config(relative_dir: str = ".") -> dict:
    """Deterministically detects a project's framework, dependencies, config files,
    and build/CI setup by reading manifests and known config filenames — no LLM."""
    start_time = time.perf_counter()
    target_dir = resolve_safe_path(relative_dir)  # raises on invalid path, per convention

    frameworks = set()
    dependencies = {}

    pkg_json_path = target_dir / "package.json"
    if pkg_json_path.exists():
        try:
            pkg_data = json.loads(_read_text_safe(pkg_json_path))
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            dependencies["npm"] = list(deps.keys())
            for signal, fw_name in MANIFEST_FRAMEWORK_SIGNALS["package.json"].items():
                if signal in deps:
                    frameworks.add(fw_name)
        except Exception:
            pass

    req_path = target_dir / "requirements.txt"
    if req_path.exists():
        content = _read_text_safe(req_path).lower()
        pkgs = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        dependencies["pip"] = pkgs
        for signal, fw_name in MANIFEST_FRAMEWORK_SIGNALS["requirements.txt"].items():
            if signal in content:
                frameworks.add(fw_name)

    pyproject_path = target_dir / "pyproject.toml"
    if pyproject_path.exists():
        content = _read_text_safe(pyproject_path).lower()
        for signal, fw_name in MANIFEST_FRAMEWORK_SIGNALS["pyproject.toml"].items():
            if signal in content:
                frameworks.add(fw_name)

    if (target_dir / "manage.py").exists():
        frameworks.add("Django")
    if (target_dir / "next.config.js").exists() or (target_dir / "next.config.ts").exists():
        frameworks.add("Next.js")

    config_files_found = [f for f in CONFIG_FILE_CANDIDATES if (target_dir / f).exists()]

    build_ci_found = [f for f in BUILD_CI_CANDIDATES if (target_dir / f).exists()]
    workflows_dir = target_dir / ".github" / "workflows"
    if workflows_dir.exists():
        build_ci_found.extend(f".github/workflows/{f.name}" for f in workflows_dir.glob("*.yml"))

    env_vars_expected = []
    env_example_path = target_dir / ".env.example"
    if env_example_path.exists():
        for line in _read_text_safe(env_example_path).splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                env_vars_expected.append(line.split("=")[0].strip())

    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Project config analysis completed in {elapsed:.4f} seconds.", file=sys.stderr)

    return {
        "frameworks": sorted(frameworks),
        "dependencies": dependencies,
        "config_files": config_files_found,
        "build_ci": build_ci_found,
        "env_vars_expected": env_vars_expected,
    }