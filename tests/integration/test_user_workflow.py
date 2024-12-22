import abc
import dataclasses
import datetime
import os
import time
from io import BytesIO
from typing import Literal
from urllib.request import urlopen
from zipfile import ZipFile

import pytest
import requests
import yaml

from conftest import Environment


@dataclasses.dataclass
class ApplicationSpecs:
    application: str
    version: str
    entrypoint: str


@dataclasses.dataclass
class ApplicationFile:
    type: Literal["config", "data", "artifact", "output", "log"]
    path: str


class _TestApplicationWorkflow(abc.ABC):
    @pytest.fixture(scope="class")
    @abc.abstractmethod
    def application(self) -> ApplicationSpecs:
        raise NotImplementedError()

    @pytest.fixture(scope="class")
    @abc.abstractmethod
    def input_files(self) -> list[ApplicationFile]:
        raise NotImplementedError()

    @pytest.fixture(scope="class")
    def headers(self, id_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {id_token}"}

    @pytest.fixture(scope="class")
    def experiment_unique_id(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

    @pytest.fixture(scope="class")
    def job_name(self, experiment_unique_id: str) -> str:
        return f"integration_test_job_{experiment_unique_id}"

    @pytest.fixture(scope="class")
    def job_id(
        self,
        use_cloud: bool,
        environment: Environment,
        application: ApplicationSpecs,
        experiment_unique_id: str,
        job_name: str,
        headers: dict[str, str],
    ) -> str:
        params = {
            "job_name": job_name,
            "environment": "cloud" if use_cloud else "local",
            "priority": 0,
            "application": dataclasses.asdict(application),
            "attributes": {
                "files_down": {
                    "config_id": experiment_unique_id,
                    "data_ids": [experiment_unique_id],
                    "artifact_ids": [],
                },
                "env_vars": {},
            },
            "hardware": {
                "cpu_cores": None,
                "memory": None,
                "gpu_model": None,
                "gpu_archi": None,
                "gpu_mem": None,
            },
        }
        resp = requests.post(
            f"{environment.userfacing_api_url}/jobs", json=params, headers=headers
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_file(
        self, api_url: str, base_path: str, file_path: str, headers: dict[str, str]
    ) -> None:
        resp = requests.post(
            f"{api_url}/files/{base_path}/url",
            headers=headers,
        )
        resp.raise_for_status()
        resp = requests.request(
            **resp.json(),
            files={"file": (os.path.split(file_path)[-1], open(file_path, "rb"))},
        )
        resp.raise_for_status()

    def download_file(
        self, api_url: str, base_path: str, headers: dict[str, str]
    ) -> bytes:
        resp = requests.get(
            f"{api_url}/files/{base_path}/url",
            headers=headers,
        )
        resp.raise_for_status()
        resp = requests.request(**resp.json())
        resp.raise_for_status()
        return resp.content

    def get_status(self, api_url: str, job_id: str, headers: dict[str, str]):
        resp = requests.get(f"{api_url}/jobs/{job_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()["status"]

    def check_status_change(
        self,
        api_url: str,
        job_id: str,
        status: str,
        headers: dict[str, str],
        sleep_time: int = 30,
        timeout: int = 10 * 60,
    ) -> None:
        t_start = datetime.datetime.now(datetime.timezone.utc)
        while datetime.datetime.now(
            datetime.timezone.utc
        ) - t_start < datetime.timedelta(seconds=timeout):
            if self.get_status(api_url, job_id, headers) == status:
                return
            time.sleep(sleep_time)
        raise TimeoutError(f"Status did not change to {status}.")

    @pytest.mark.order1
    def test_upload(
        self,
        environment: Environment,
        input_files: list[ApplicationFile],
        headers: dict[str, str],
        experiment_unique_id: str,
    ) -> None:
        # files not already there
        resp = requests.get(
            f"{environment.userfacing_api_url}/files/config/{experiment_unique_id}",
            headers=headers,
        )
        assert resp.status_code == 404
        resp = requests.get(
            f"{environment.userfacing_api_url}/files/data/{experiment_unique_id}",
            headers=headers,
        )
        assert resp.status_code == 404
        resp = requests.get(
            f"{environment.userfacing_api_url}/files/artifact/{experiment_unique_id}",
            headers=headers,
        )
        assert resp.status_code == 404
        # upload
        for file in input_files:
            self.upload_file(
                environment.userfacing_api_url,
                f"{file.type}/{experiment_unique_id}/",
                file.path,
                headers,
            )

    @pytest.mark.order2
    def test_list_files(
        self,
        environment: Environment,
        input_files: list[ApplicationFile],
        headers: dict[str, str],
        experiment_unique_id: str,
    ) -> None:
        resp = requests.get(
            f"{environment.userfacing_api_url}/files/",
            params={"recursive": True},
            headers=headers,
        )
        resp.raise_for_status()
        paths = [f["path"] for f in resp.json()]
        for file in input_files:
            assert f"{file.type}/{experiment_unique_id}/{file.path}" in paths

    @pytest.mark.order3
    def test_start_job(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        assert (
            self.get_status(environment.userfacing_api_url, job_id, headers) == "queued"
        )

    @pytest.mark.order4
    def test_job_preprocessing(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        self.check_status_change(
            environment.userfacing_api_url,
            job_id,
            "preprocessing",
            headers,
            sleep_time=5,
            timeout=10 * 60,
        )

    @pytest.mark.order5
    def test_job_running(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        self.check_status_change(
            environment.userfacing_api_url,
            job_id,
            "running",
            headers,
            sleep_time=5,
            timeout=10 * 60,
        )

    @pytest.mark.order6
    def test_job_postprocessing(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        self.check_status_change(
            environment.userfacing_api_url,
            job_id,
            "postprocessing",
            headers,
            sleep_time=5,
            timeout=30 * 60,
        )

    @pytest.mark.order7
    def test_job_finished(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        self.check_status_change(
            environment.userfacing_api_url,
            job_id,
            "finished",
            headers,
            sleep_time=5,
            timeout=10 * 60,
        )

    @pytest.mark.order8
    @abc.abstractmethod
    def test_download(
        self,
        environment: Environment,
        job_name: str,
        headers: dict[str, str],
        input_files: list[ApplicationFile],
    ) -> None:
        raise NotImplementedError()

    @pytest.mark.order9
    def test_cancel_job(
        self, environment: Environment, job_id: str, headers: dict[str, str]
    ) -> None:
        resp = requests.delete(
            f"{environment.userfacing_api_url}/jobs/{job_id}", headers=headers
        )
        resp.raise_for_status()


class TestDecodeStableWorkflow(_TestApplicationWorkflow):
    @pytest.fixture(scope="class")
    def application(self) -> ApplicationSpecs:
        return ApplicationSpecs(
            application="decode",
            version="v_0_10_1",
            entrypoint="train",
        )

    @pytest.fixture(scope="class")
    def input_files(
        self, use_gpu: bool, tmp_path_factory: pytest.TempPathFactory
    ) -> list[ApplicationFile]:
        zip_url = "https://oc.embl.de/index.php/s/Abn8nSMlOqvKeHC/download"
        tmpdir = tmp_path_factory.mktemp("decode_stable")
        with urlopen(zip_url) as zipresp:
            with ZipFile(BytesIO(zipresp.read())) as zfile:
                zfile.extractall(tmpdir)
        base_dir = tmpdir / "decode_cloud_train_experimental"

        calib_path = base_dir / "spline_calibration_3dcal.mat"

        params_path = base_dir / "param_run_in.yaml"
        with open(params_path, "r") as f:
            params = yaml.safe_load(f)
            # shorten training
            params["HyperParameter"]["epochs"] = 1
            params["HyperParameter"]["pseudo_ds_size"] = 200
            params["Simulation"]["test_size"] = 64
            # train on right device
            device = "cuda" if use_gpu else "cpu"
            params["Hardware"]["device"] = device
            params["Hardware"]["device_simulation"] = device
        with open(params_path, "w") as f:
            yaml.dump(params, f)

        return [
            ApplicationFile(type="config", path=params_path),
            ApplicationFile(type="data", path=calib_path),
        ]

    @pytest.mark.order8
    def test_download(
        self,
        environment: Environment,
        job_name: str,
        headers: dict[str, str],
        input_files: list[ApplicationFile],
    ) -> None:
        resp = requests.get(
            f"{environment.userfacing_api_url}/files/artifact/{job_name}/",
            params={"recursive": True},
            headers=headers,
        )
        resp.raise_for_status()
        paths = [f["path"] for f in resp.json()]
        path = [p for p in paths if "param_run_in.yaml" in p][0]
        content = self.download_file(environment.userfacing_api_url, path, headers)
        assert (
            yaml.safe_load(content)["Camera"]["baseline"]
            == yaml.safe_load(open(input_files[0].path))["Camera"]["baseline"]
        )
        model_paths = [p for p in paths if os.path.splitext(p)[-1] == ".pt"]
        assert len(model_paths) >= 1
