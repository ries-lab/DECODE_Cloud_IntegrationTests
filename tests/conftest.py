import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--local",
        action="store_true",
        help="Run tests against a locally deployed environment."
        "Takes care of deploying the environment with docker-compose up -d.",
    )
    parser.addoption(
        "--dev",
        action="store_true",
        help="Run tests against the dev environment",
    )
    parser.addoption(
        "--prod",
        action="store_true",
        help="Run tests against the prod environment",
    )

    parser.addoption(
        "--gpu",
        action="store_true",
        help="Run applications on GPU",
    )
    parser.addoption(
        "--cloud",
        action="store_true",
        help="Run applications on a cloud worker",
    )
