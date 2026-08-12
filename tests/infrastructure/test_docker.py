import yaml
import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent


def test_dockerfile_exists():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile missing"


def test_dockerignore_exists():
    dockerignore = PROJECT_ROOT / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore missing"


def test_dockerignore_excludes_node_modules():
    dockerignore = PROJECT_ROOT / ".dockerignore"
    content = dockerignore.read_text() if dockerignore.exists() else ""
    assert "node_modules" in content, ".dockerignore must exclude node_modules"


def test_dockerignore_excludes_venv():
    dockerignore = PROJECT_ROOT / ".dockerignore"
    content = dockerignore.read_text() if dockerignore.exists() else ""
    assert ".venv" in content or "/.venv" in content, ".dockerignore must exclude .venv"


def test_dockercompose_exists():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml missing"


def test_dockercompose_has_eval_service():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    assert content is not None
    assert "services" in content
    assert "promptfoo-eval" in content["services"], "promptfoo-eval service missing"


def test_dockercompose_has_view_service():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    assert content is not None
    assert "services" in content
    assert "promptfoo-view" in content["services"], "promptfoo-view service missing"


def test_dockercompose_view_exposes_port_15500():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    view = content["services"]["promptfoo-view"]
    ports = view.get("ports", [])
    port_values = [str(p) for p in ports]
    assert any("15500" in p for p in port_values), "promptfoo-view must expose port 15500"


def test_dockercompose_mounts_data_app_data():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    for service in content["services"].values():
        volumes = service.get("volumes", [])
        for v in volumes:
            v_str = str(v)
            if "./data:" in v_str or "data/app_data" in v_str:
                return
    pytest.fail("data/app_data volume mount not found in any service")


def test_run_insight_eval_script_exists():
    script = PROJECT_ROOT / "scripts" / "run_insight_eval.sh"
    assert script.exists(), "scripts/run_insight_eval.sh missing"


def test_run_insight_eval_script_is_executable():
    script = PROJECT_ROOT / "scripts" / "run_insight_eval.sh"
    if not script.exists():
        pytest.skip("scripts/run_insight_eval.sh not found")
    import os
    assert os.access(script, os.X_OK), "scripts/run_insight_eval.sh is not executable"


def test_dockerfile_has_promptfoo():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile not found")
    content = dockerfile.read_text()
    assert "promptfoo" in content, "Dockerfile must install promptfoo"


def test_dockerfile_has_python():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile not found")
    content = dockerfile.read_text()
    assert "python" in content.lower(), "Dockerfile must include Python"


def test_dockerfile_copies_deps_before_source():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile not found")
    content = dockerfile.read_text()
    lines = content.split("\n")
    copy_lines = [i for i, line in enumerate(lines) if line.strip().startswith("COPY")]
    if len(copy_lines) >= 2:
        first_copy = lines[copy_lines[0]]
        second_copy = lines[copy_lines[1]]
        deps_files = ["package.json", "requirements.txt", "pyproject.toml"]
        is_deps_first = any(f in first_copy for f in deps_files)
        assert is_deps_first, (
            "Deps files (package.json/requirements.txt) must be copied before source code. "
            f"First COPY: {first_copy.strip()}"
        )


def test_eval_script_invokes_promptfoo_eval():
    script = PROJECT_ROOT / "scripts" / "eval.sh"
    if not script.exists():
        pytest.skip("scripts/eval.sh not found")
    content = script.read_text()
    assert "promptfoo eval" in content, "eval.sh must invoke 'promptfoo eval'"


def test_dockercompose_eval_has_no_command():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    eval_service = content["services"]["promptfoo-eval"]
    assert "command" not in eval_service, (
        "promptfoo-eval must not have a command so the wrapper can supply one"
    )


def test_dockerfile_creates_data_app_data_dir():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    if not dockerfile.exists():
        pytest.skip("Dockerfile not found")
    content = dockerfile.read_text()
    assert "data/app_data" in content, (
        "Dockerfile must create or reference data/app_data directory"
    )


def test_dockercompose_mounts_promptfoo_store():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    for svc_name in ("promptfoo-eval", "promptfoo-view"):
        svc = content["services"].get(svc_name, {})
        volumes = [str(v) for v in svc.get("volumes", [])]
        assert any("promptfoo_store:/root/.promptfoo" in v for v in volumes), (
            f"{svc_name} must mount ./data/promptfoo_store:/root/.promptfoo"
        )


def test_dockercompose_app_service_uses_named_volume():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    
    assert "app" in content["services"], "app service missing in docker-compose.yml"
    app_service = content["services"]["app"]
    volumes = app_service.get("volumes", [])
    
    has_named_volume = False
    for v in volumes:
        v_str = str(v)
        if v_str.endswith(":/app/data"):
            assert not v_str.startswith("./") and not v_str.startswith("/"), (
                f"app service mounts a host directory to /app/data: {v_str}. It must use a named volume."
            )
            assert v_str.startswith("tinybi-data:"), f"Expected named volume tinybi-data, got {v_str}"
            has_named_volume = True
            
    assert has_named_volume, "app service must mount to /app/data using a named volume"


def test_dockercompose_has_tinybi_data_volume_declared():
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    content = yaml.safe_load(compose_file.read_text())
    
    assert "volumes" in content, "volumes section missing in docker-compose.yml"
    assert "tinybi-data" in content["volumes"], "tinybi-data named volume not declared"


def test_dockerfile_app_copies_data_directory():
    dockerfile = PROJECT_ROOT / "Dockerfile.app"
    if not dockerfile.exists():
        pytest.skip("Dockerfile.app not found")
    content = dockerfile.read_text()
    
    assert "COPY data/" in content or "COPY ./data" in content, (
        "Dockerfile.app must copy the data/ folder to seed the container"
    )

