from pathlib import Path

import docker
import yaml


def _get_client() -> docker.DockerClient:
    return docker.from_env()


def cleanup() -> None:
    """
    Removes all Docker images for these tests, prune dangling images.
    Deletes all containers for these tests.
    """
    client = _get_client()
    docker_compose_cfg = yaml.safe_load(
        open(Path(__file__).parent.parent / "docker-compose.yaml")
    )
    services = docker_compose_cfg.get("services", {})
    for _, service_cfg in services.items():
        image_name = service_cfg.get("image")
        if image_name:
            for image in client.images.list(name=image_name):
                client.images.remove(image.id, force=True)
    client.images.prune(filters={"dangling": True})
