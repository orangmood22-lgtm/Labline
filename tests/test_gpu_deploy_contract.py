#!/usr/bin/env python3
"""Deployment contract tests for the single-user GPU container."""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GPU_COMPOSE = REPO_ROOT / "deploy" / "docker-compose.gpu.yaml"
GPU_ENV_EXAMPLE = REPO_ROOT / "deploy" / ".env.gpu.example"
GPU_DOCKERFILE = REPO_ROOT / "deploy" / "Dockerfile.gpu"


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
        self.assertIn("FRAMEWORK_PATH=/data/aris/aris-framework", content)
        self.assertIn("DEV_FRAMEWORK_PATH=/data/aris/aris-dev", content)
        self.assertIn("PROJECT_PATH=/data/aris/projects", content)
        self.assertIn("DATASETS_PATH=/data/datasets", content)
        self.assertNotIn("USERNAME=orangmood", content)
        self.assertNotIn("/workspace", content)

    def test_gpu_dockerfile_uses_distribution_python_without_ppa(self):
        content = GPU_DOCKERFILE.read_text()

        self.assertNotIn("deadsnakes", content)
        self.assertNotIn("add-apt-repository", content)
        self.assertIn("python3-venv", content)
        self.assertIn("python3-dev", content)
        self.assertIn("python3-distutils", content)
        self.assertIn("python3-pip", content)
        self.assertNotIn("get-pip.py", content)

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
