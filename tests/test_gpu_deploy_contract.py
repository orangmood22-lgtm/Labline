#!/usr/bin/env python3
"""Deployment contract tests for the single-user GPU container."""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GPU_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.gpu.yaml"
MULTI_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.yaml"
GPU_ENV_EXAMPLE = REPO_ROOT / "deploy" / ".env.gpu.example"
MULTI_ENV_EXAMPLE = REPO_ROOT / "deploy" / ".env.example"
GPU_DOCKERFILE = REPO_ROOT / "deploy" / "Dockerfile.gpu"
MULTI_DOCKERFILE = REPO_ROOT / "deploy" / "Dockerfile"
ENTRYPOINT = REPO_ROOT / "deploy" / "entrypoint.sh"


class GpuDeployContractTest(unittest.TestCase):
    def test_compose_mounts_host_framework_to_container_framework_path(self):
        content = GPU_COMPOSE.read_text()

        self.assertIn("FRAMEWORK_PATH", content)
        self.assertIn(":/aris/framework", content)
        self.assertIn("DEV_FRAMEWORK_PATH", content)
        self.assertIn(":/aris/aris-dev", content)
        self.assertIn("BUILD_HTTP_PROXY", content)
        self.assertIn("BUILD_HTTPS_PROXY", content)

    def test_env_example_uses_generic_host_paths(self):
        content = GPU_ENV_EXAMPLE.read_text()

        self.assertIn("USERNAME=researcher", content)
        self.assertIn("FRAMEWORK_PATH=", content)
        self.assertIn("DEV_FRAMEWORK_PATH=", content)
        self.assertIn("PROJECT_PATH=", content)
        self.assertIn("DATASETS_PATH=", content)
        self.assertIn("PRETRAINED_PATH=", content)
        self.assertIn("SSH_PATH=", content)
        self.assertIn("[你的framework位置]", content)
        self.assertIn("[你的项目工作区]", content)
        self.assertIn("[你的数据集目录]", content)
        self.assertNotIn("/data/", content)
        self.assertNotIn("USERNAME=orangmood", content)
        self.assertNotIn("/workspace", content)

    def test_gpu_compose_requires_explicit_host_paths(self):
        content = GPU_COMPOSE.read_text()

        self.assertIn("${FRAMEWORK_PATH:?set FRAMEWORK_PATH in .env}:/aris/framework", content)
        self.assertIn("${DEV_FRAMEWORK_PATH:?set DEV_FRAMEWORK_PATH in .env}:/aris/aris-dev", content)
        self.assertIn("${PROJECT_PATH:?set PROJECT_PATH in .env}:/aris/projects", content)
        self.assertIn("${DATASETS_PATH:?set DATASETS_PATH in .env}:/aris/shared/datasets:ro", content)
        self.assertIn("${PRETRAINED_PATH:?set PRETRAINED_PATH in .env}:/aris/shared/pretrained", content)
        self.assertIn("${SSH_PATH:?set SSH_PATH in .env}:/run/secrets/ssh:ro", content)
        self.assertNotIn(":-/data/", content)
        self.assertNotIn("/workspace", content)

    def test_multi_user_compose_uses_per_user_framework_and_project_paths(self):
        content = MULTI_COMPOSE.read_text()

        self.assertIn("${USER1_FRAMEWORK_PATH:?set USER1_FRAMEWORK_PATH in .env}:/aris/framework", content)
        self.assertIn("${USER1_PROJECTS_PATH:?set USER1_PROJECTS_PATH in .env}:/aris/projects", content)
        self.assertIn("${USER1_STATE_PATH:?set USER1_STATE_PATH in .env}:/aris/.aris", content)
        self.assertIn("${USER2_FRAMEWORK_PATH:?set USER2_FRAMEWORK_PATH in .env}:/aris/framework", content)
        self.assertIn("${USER2_PROJECTS_PATH:?set USER2_PROJECTS_PATH in .env}:/aris/projects", content)
        self.assertIn("${USER2_STATE_PATH:?set USER2_STATE_PATH in .env}:/aris/.aris", content)
        self.assertIn("ARIS_WORKSPACE=/aris", content)
        self.assertIn("${DATASETS_PATH:?set DATASETS_PATH in .env}:/aris/shared/datasets:ro", content)
        self.assertIn("${PRETRAINED_PATH:?set PRETRAINED_PATH in .env}:/aris/shared/pretrained", content)
        self.assertIn("${DOWNLOADS_PATH:?set DOWNLOADS_PATH in .env}:/aris/shared/downloads", content)
        self.assertNotIn("aris-framework:/aris/framework", content)
        self.assertNotIn("user1-projects:/aris/projects", content)

    def test_multi_user_env_example_declares_workspace_paths(self):
        content = MULTI_ENV_EXAMPLE.read_text()

        for item in [
            "ARIS_ROOT=[你的ARIS总目录]",
            "USER1_FRAMEWORK_PATH=[你的ARIS总目录]/users/zhangsan/framework",
            "USER1_PROJECTS_PATH=[你的ARIS总目录]/users/zhangsan/projects",
            "USER1_STATE_PATH=[你的ARIS总目录]/users/zhangsan/.aris",
            "USER2_FRAMEWORK_PATH=[你的ARIS总目录]/users/lisi/framework",
            "USER2_PROJECTS_PATH=[你的ARIS总目录]/users/lisi/projects",
            "USER2_STATE_PATH=[你的ARIS总目录]/users/lisi/.aris",
            "DATASETS_PATH=[你的ARIS总目录]/shared/datasets",
            "PRETRAINED_PATH=[你的ARIS总目录]/shared/pretrained",
            "DOWNLOADS_PATH=[你的ARIS总目录]/shared/downloads",
        ]:
            self.assertIn(item, content)

    def test_env_examples_include_runtime_proxy_git_proxy_and_feishu_vars(self):
        required = [
            "HTTP_PROXY=",
            "HTTPS_PROXY=",
            "NO_PROXY=",
            "http_proxy=",
            "https_proxy=",
            "no_proxy=",
            "GIT_HTTP_PROXY=",
            "GIT_HTTPS_PROXY=",
            "ARIS_AUTO_CHECK_UPDATE=1",
            "ARIS_UPDATE_CHECK_INTERVAL=1d",
            "ARIS_UPDATE_CHECK_TIMEOUT=10s",
            "FEISHU_APP_ID=",
            "FEISHU_APP_SECRET=",
            "FEISHU_USER_ID=",
            "FEISHU_RECEIVE_ID_TYPE=open_id",
            "FEISHU_ENABLE_WS=0",
            "BRIDGE_PORT=5000",
            "ARIS_PROJECT_ROOT=",
            "ARIS_FEISHU_CONTROL_ROOT=",
        ]
        for path in [GPU_ENV_EXAMPLE, MULTI_ENV_EXAMPLE]:
            content = path.read_text()
            with self.subTest(path=path.name):
                for item in required:
                    self.assertIn(item, content)

    def test_compose_files_pass_proxy_git_proxy_and_feishu_vars(self):
        required = [
            "HTTP_PROXY=${HTTP_PROXY:-}",
            "HTTPS_PROXY=${HTTPS_PROXY:-}",
            "NO_PROXY=${NO_PROXY:-}",
            "http_proxy=${http_proxy:-}",
            "https_proxy=${https_proxy:-}",
            "no_proxy=${no_proxy:-}",
            "GIT_HTTP_PROXY=${GIT_HTTP_PROXY:-}",
            "GIT_HTTPS_PROXY=${GIT_HTTPS_PROXY:-}",
            "ARIS_AUTO_CHECK_UPDATE=${ARIS_AUTO_CHECK_UPDATE:-1}",
            "ARIS_UPDATE_CHECK_INTERVAL=${ARIS_UPDATE_CHECK_INTERVAL:-1d}",
            "ARIS_UPDATE_CHECK_TIMEOUT=${ARIS_UPDATE_CHECK_TIMEOUT:-10s}",
            "FEISHU_APP_ID=${FEISHU_APP_ID:-}",
            "FEISHU_APP_SECRET=${FEISHU_APP_SECRET:-}",
            "FEISHU_USER_ID=${FEISHU_USER_ID:-}",
            "FEISHU_RECEIVE_ID_TYPE=${FEISHU_RECEIVE_ID_TYPE:-open_id}",
            "FEISHU_ENABLE_WS=${FEISHU_ENABLE_WS:-0}",
            "BRIDGE_PORT=${BRIDGE_PORT:-5000}",
            "ARIS_PROJECT_ROOT=${ARIS_PROJECT_ROOT:-/aris/framework}",
            "ARIS_FEISHU_CONTROL_ROOT=${ARIS_FEISHU_CONTROL_ROOT:-}",
        ]
        for path in [GPU_COMPOSE, MULTI_COMPOSE]:
            content = path.read_text()
            with self.subTest(path=path.name):
                for item in required:
                    self.assertIn(item, content)

    def test_entrypoint_persists_upper_lower_proxy_and_optional_git_proxy(self):
        content = ENTRYPOINT.read_text()

        self.assertIn('PROXY_HTTP="${HTTP_PROXY:-${http_proxy:-}}"', content)
        self.assertIn('PROXY_HTTPS="${HTTPS_PROXY:-${https_proxy:-$PROXY_HTTP}}"', content)
        self.assertIn('PROXY_NO="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost}}"', content)
        for name in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"]:
            self.assertIn(f'echo "{name}=', content)
        self.assertIn('git config --global http.proxy "$GIT_HTTP_PROXY"', content)
        self.assertIn('git config --global https.proxy "$GIT_HTTPS_PROXY"', content)

    def test_entrypoint_checks_framework_updates_without_auto_pull(self):
        content = ENTRYPOINT.read_text()

        self.assertIn("ARIS_AUTO_CHECK_UPDATE", content)
        self.assertIn("framework check-update", content)
        self.assertIn("ARIS_UPDATE_CHECK_INTERVAL", content)
        self.assertIn("--if-stale", content)
        self.assertIn("--notify", content)
        self.assertIn(".bashrc", content)
        self.assertNotIn("git pull --ff-only", content)

    def test_gpu_dockerfile_uses_distribution_python_without_ppa(self):
        content = GPU_DOCKERFILE.read_text()

        self.assertNotIn("deadsnakes", content)
        self.assertNotIn("add-apt-repository", content)
        self.assertIn("python3-venv", content)
        self.assertIn("python3-dev", content)
        self.assertIn("python3-distutils", content)
        self.assertIn("python3-pip", content)
        self.assertNotIn("get-pip.py", content)

    def test_container_images_preinstall_cc_switch_cli(self):
        for path in [GPU_DOCKERFILE, MULTI_DOCKERFILE]:
            content = path.read_text()
            with self.subTest(path=path.name):
                self.assertIn("cc-switch-cli", content)
                self.assertIn("cc-switch-cli-linux-x64-musl.tar.gz", content)
                self.assertIn("mv cc-switch /usr/local/bin/", content)

    def test_gpu_dockerfile_clears_base_image_proxy_before_apt(self):
        content = GPU_DOCKERFILE.read_text()
        first_apt = content.index("apt-get update")
        early_content = content[:first_apt]

        self.assertIn("BUILD_HTTP_PROXY", early_content)
        self.assertIn("BUILD_HTTPS_PROXY", early_content)
        self.assertIn('export http_proxy="${BUILD_HTTP_PROXY}"', early_content)
        self.assertIn("/etc/apt/apt.conf.d/*proxy*", early_content)
        self.assertIn("/etc/environment", early_content)
        self.assertGreaterEqual(content.count('export http_proxy="${BUILD_HTTP_PROXY}"'), 8)


if __name__ == "__main__":
    unittest.main()
