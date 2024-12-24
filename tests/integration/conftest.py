import dataclasses
import os
import time
from typing import Any, Generator, cast

import boto3
import dotenv
import pytest
import requests
from python_on_whales import docker


@dataclasses.dataclass
class Environment:
    name: str
    userfacing_api_url: str
    workerfacing_api_url: str


@pytest.fixture(scope="session", autouse=True)
def environment(pytestconfig: pytest.Config) -> Generator[Environment, Any, None]:
    local = pytestconfig.getoption("local")
    dev = pytestconfig.getoption("dev")
    prod = pytestconfig.getoption("prod")

    if not any([local, dev, prod]):
        raise ValueError("You must specify one of --local, --dev, or --prod")
    if sum([local, dev, prod]) > 1:
        raise ValueError("You can only specify one of --local, --dev, or --prod")

    if local:
        docker.compose.up(detach=True)
        time.sleep(30)  # leave some time for the services to start
        yield Environment(
            name="local",
            userfacing_api_url="http://localhost:8000",
            workerfacing_api_url="http://localhost:8001",
        )
        docker.compose.down()
    elif dev:
        yield Environment(
            name="dev",
            userfacing_api_url="https://dev.api.decode.arthur-jaques.de",
            workerfacing_api_url="https://dev.wapi.decode.arthur-jaques.de",
        )
    elif prod:
        yield Environment(
            name="prod",
            userfacing_api_url="https://prod.api.decode.arthur-jaques.de",
            workerfacing_api_url="https://prod.wapi.decode.arthur-jaques.de",
        )
    else:
        raise RuntimeError("Python is broken ;)")


@pytest.fixture(scope="session")
def use_gpu(pytestconfig: pytest.Config) -> bool:
    gpu = cast(bool, pytestconfig.getoption("gpu"))
    if gpu:
        raise NotImplementedError("GPU tests are not implemented yet")
    return gpu


@pytest.fixture(scope="session")
def use_cloud(pytestconfig: pytest.Config, environment: Environment) -> bool:
    ret = cast(bool, pytestconfig.getoption("cloud"))
    if ret and environment.name == "local":
        raise ValueError("Cannot use --cloud with --local")
    return ret


@pytest.fixture(scope="session")
def id_token(environment: Environment) -> str:
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    prefix = "" if environment.name == "local" else "TEST_"
    email = os.environ[f"{prefix}EMAIL"]
    pwd = os.environ[f"{prefix}PASSWORD"]

    resp = requests.get(f"{environment.userfacing_api_url}/access_info")
    resp.raise_for_status()
    access_info = resp.json()["cognito"]
    cognito_client = boto3.client("cognito-idp", region_name=access_info["region"])
    id_token = cognito_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": pwd},
        ClientId=access_info["client_id"],
    )["AuthenticationResult"]["IdToken"]
    return cast(str, id_token)
