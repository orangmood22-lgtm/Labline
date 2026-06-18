from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = REPO_ROOT / "tools" / "install_labline_dev_skills.sh"
LANE_CLI = REPO_ROOT / "tools" / "lane"


def run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def write_skill(root: Path, name: str, body: str = "# skill\n") -> None:
    skill_dir = root / "to-developer" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def make_checkout(tmp_path: Path) -> Path:
    repo = tmp_path / "labline-dev"
    (repo / "tools").mkdir(parents=True)
    (repo / "templates").mkdir()
    shutil.copy2(SOURCE_SCRIPT, repo / "tools" / "install_labline_dev_skills.sh")
    (repo / "tools" / "install_labline_dev_skills.sh").chmod(0o755)

    write_skill(repo, "dev-alpha", "# alpha\n")
    write_skill(repo, "dev-beta", "# beta\n")
    write_skill(repo, "caveman", "# not-dev\n")

    claude_skills = repo / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "existing.txt").write_text("keep\n", encoding="utf-8")
    return repo


def test_dev_skill_installer_installs_only_dev_skills_and_keeps_claude(tmp_path: Path) -> None:
    repo = make_checkout(tmp_path)

    result = run(["bash", "tools/install_labline_dev_skills.sh", "--quiet"], cwd=repo)
    assert result.returncode == 0, result.stderr

    alpha_link = repo / ".agents" / "skills" / "dev-alpha"
    beta_link = repo / ".agents" / "skills" / "dev-beta"
    assert alpha_link.is_symlink()
    assert beta_link.is_symlink()
    assert alpha_link.resolve() == repo / "to-developer" / "skills" / "dev-alpha"
    assert beta_link.resolve() == repo / "to-developer" / "skills" / "dev-beta"
    assert not (repo / ".agents" / "skills" / "caveman").exists()

    manifest = repo / ".labline" / "installed-dev-skills.txt"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "dev-alpha" in manifest_text
    assert "dev-beta" in manifest_text
    assert "caveman" not in manifest_text

    assert (repo / ".claude" / "skills" / "existing.txt").read_text(encoding="utf-8") == "keep\n"
    assert not (repo / ".claude" / "skills" / "dev-alpha").exists()


def test_dev_skill_installer_dry_run_does_not_create_local_state(tmp_path: Path) -> None:
    repo = make_checkout(tmp_path)

    result = run(["bash", "tools/install_labline_dev_skills.sh", "--dry-run", "--quiet"], cwd=repo)
    assert result.returncode == 0, result.stderr

    assert not (repo / ".agents").exists()
    assert not (repo / ".labline").exists()
    assert not (repo / ".claude" / "skills" / "dev-alpha").exists()


def test_dev_skills_cli_wraps_installer(tmp_path: Path) -> None:
    repo = make_checkout(tmp_path)

    install = subprocess.run(
        [str(LANE_CLI), "dev", "skills", "install", "--labline-repo", str(repo), "--quiet"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr
    assert (repo / ".agents" / "skills" / "dev-alpha").is_symlink()
    assert (repo / ".labline" / "installed-dev-skills.txt").exists()

    doctor = subprocess.run(
        [str(LANE_CLI), "dev", "skills", "doctor", "--labline-repo", str(repo), "--quiet"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert doctor.returncode == 0, doctor.stderr

    detach = subprocess.run(
        [str(LANE_CLI), "dev", "skills", "detach", "--labline-repo", str(repo), "--quiet"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert detach.returncode == 0, detach.stderr
    assert not (repo / ".agents" / "skills" / "dev-alpha").exists()


def test_dev_skill_installer_reconciles_and_detaches(tmp_path: Path) -> None:
    repo = make_checkout(tmp_path)

    first = run(["bash", "tools/install_labline_dev_skills.sh", "--quiet"], cwd=repo)
    assert first.returncode == 0, first.stderr

    (repo / "to-developer" / "skills" / "dev-beta").rename(repo / "to-developer" / "skills" / "dev-gamma")

    second = run(["bash", "tools/install_labline_dev_skills.sh", "--quiet"], cwd=repo)
    assert second.returncode == 0, second.stderr

    assert not (repo / ".agents" / "skills" / "dev-beta").exists()
    assert (repo / ".agents" / "skills" / "dev-gamma").resolve() == repo / "to-developer" / "skills" / "dev-gamma"
    manifest_text = (repo / ".labline" / "installed-dev-skills.txt").read_text(encoding="utf-8")
    assert "dev-beta" not in manifest_text
    assert "dev-gamma" in manifest_text

    (repo / ".agents" / "skills" / "local-note.txt").write_text("keep\n", encoding="utf-8")
    detach = run(["bash", "tools/install_labline_dev_skills.sh", "--detach", "--quiet"], cwd=repo)
    assert detach.returncode == 0, detach.stderr

    assert not (repo / ".agents" / "skills" / "dev-alpha").exists()
    assert not (repo / ".agents" / "skills" / "dev-gamma").exists()
    assert (repo / ".agents" / "skills" / "local-note.txt").read_text(encoding="utf-8") == "keep\n"
    assert not (repo / ".labline" / "installed-dev-skills.txt").exists()
    assert (repo / ".claude" / "skills" / "existing.txt").exists()


def test_dev_skill_installer_doctor_reports_bad_links(tmp_path: Path) -> None:
    repo = make_checkout(tmp_path)

    install = run(["bash", "tools/install_labline_dev_skills.sh", "--quiet"], cwd=repo)
    assert install.returncode == 0, install.stderr

    dev_alpha = repo / ".agents" / "skills" / "dev-alpha"
    dev_alpha.unlink()
    dev_alpha.symlink_to(repo / "to-developer" / "skills" / "caveman")

    doctor = run(["bash", "tools/install_labline_dev_skills.sh", "--doctor", "--quiet"], cwd=repo, check=False)
    assert doctor.returncode != 0
    assert "wrong target" in doctor.stderr
