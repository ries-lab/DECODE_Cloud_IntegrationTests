import datetime
import os
import pytest
import requests
import time
import yaml
from pathlib import Path

from decode.utils.example_helper import load_gateway, load_example_package
from decode.utils.param_io import load_params, save_params

from conftest import API_URL, DEVICE, ENVIRONMENT, ID_TOKEN


@pytest.fixture(scope="module")
def example_training_files(tmpdir_factory):
    """Downloads example training files."""
    gateway = load_gateway()
    package = gateway["examples"]["colab_train_experimental_rc"]
    zip_folder = load_example_package(
        path=(
            Path(tmpdir_factory.mktemp("ex_files_train")) / package["name"]
        ).with_suffix(".zip"),
        url=package["url"],
        hash=package["hash"],
    )
    return zip_folder


@pytest.fixture(scope="module")
def params_path(example_training_files):
    params_path = str(example_training_files / "param_run_in.yaml")
    # Change training parameters
    param = load_params(params_path)
    param.HyperParameter.epochs = 1  # shorten training
    param.HyperParameter.pseudo_ds_size = 200  # shorten training
    param.Simulation.test_size = 64  # shorten training
    param.Hardware.device = DEVICE  # train on right device
    param.Hardware.device_simulation = DEVICE
    save_params(params_path, param)
    return params_path


@pytest.fixture(scope="module")
def calib_path(example_training_files):
    return str(example_training_files / "spline_calibration_3dcal.mat")


@pytest.fixture(scope="module")
def headers():
    return {"Authorization": f"Bearer {ID_TOKEN}"}


@pytest.fixture(scope="module")
def experiment_unique_id():
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


@pytest.fixture(scope="module")
def job_name(experiment_unique_id):
    return f"integration_test_job_{experiment_unique_id}"


@pytest.fixture(scope="module")
def job_id(experiment_unique_id, job_name, headers):
    params = {
        "job_name": job_name,
        "environment": ENVIRONMENT,
        "priority": 0,
        "application": {
            "application": "decode",
            "version": "v0_10_1",
            "entrypoint": "train",
        },
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
    resp = requests.post(f"{API_URL}/jobs", json=params, headers=headers)
    resp.raise_for_status()
    return resp.json()["id"]


def upload_file(base_path, file_path, headers):
    resp = requests.post(
        f"{API_URL}/files/{base_path}/url",
        headers=headers,
    )
    resp.raise_for_status()
    resp = requests.request(
        **resp.json(),
        files={"file": (os.path.split(file_path)[-1], open(file_path, "rb"))},
    )
    resp.raise_for_status()


def download_file(base_path, headers):
    resp = requests.get(
        f"{API_URL}/files/{base_path}/url",
        headers=headers,
    )
    resp.raise_for_status()
    resp = requests.request(**resp.json())
    resp.raise_for_status()
    return resp.content


def get_status(job_id, headers):
    resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()["status"]


def check_status_change(job_id, status, headers, sleep_time=30, timeout=10 * 60):
    t_start = datetime.datetime.utcnow()
    while datetime.datetime.utcnow() - t_start < datetime.timedelta(seconds=timeout):
        if get_status(job_id, headers) == status:
            return
        time.sleep(sleep_time)
    raise TimeoutError(f"Status did not change to {status}.")


@pytest.mark.order1
def test_upload(params_path, calib_path, headers, experiment_unique_id):
    # files not already there
    resp = requests.get(
        f"{API_URL}/files/config/{experiment_unique_id}", headers=headers
    )
    assert resp.status_code == 404
    resp = requests.get(f"{API_URL}/files/data/{experiment_unique_id}", headers=headers)
    assert resp.status_code == 404
    # upload params
    upload_file(f"config/{experiment_unique_id}/", params_path, headers)
    # upload calib
    upload_file(f"data/{experiment_unique_id}/", calib_path, headers)


@pytest.mark.order2
def test_list_files(headers, experiment_unique_id):
    resp = requests.get(
        f"{API_URL}/files/",
        params={"recursive": True},
        headers=headers,
    )
    resp.raise_for_status()
    paths = [f["path"] for f in resp.json()]
    assert f"config/{experiment_unique_id}/param_run_in.yaml" in paths
    assert f"data/{experiment_unique_id}/spline_calibration_3dcal.mat" in paths


@pytest.mark.order3
def test_start_job(job_id, headers):
    assert get_status(job_id, headers) == "queued"


@pytest.mark.order4
def test_job_preprocessing(job_id, headers):
    check_status_change(job_id, "preprocessing", headers, sleep_time=5, timeout=10 * 60)


@pytest.mark.order5
def test_job_running(job_id, headers):
    check_status_change(job_id, "running", headers, sleep_time=5, timeout=10 * 60)


@pytest.mark.order6
def test_job_postprocessing(job_id, headers):
    check_status_change(
        job_id, "postprocessing", headers, sleep_time=5, timeout=30 * 60
    )


@pytest.mark.order7
def test_job_finished(job_id, headers):
    check_status_change(job_id, "finished", headers, sleep_time=5, timeout=10 * 60)


@pytest.mark.order8
def test_download(job_name, headers, params_path):
    resp = requests.get(
        f"{API_URL}/files/artifact/{job_name}/",
        params={"recursive": True},
        headers=headers,
    )
    resp.raise_for_status()
    paths = [f["path"] for f in resp.json()]
    path = [p for p in paths if "param_run_in.yaml" in p][0]
    content = download_file(path, headers)
    assert (
        yaml.safe_load(content)["Camera"]["baseline"]
        == yaml.safe_load(open(params_path))["Camera"]["baseline"]
    )
    model_paths = [p for p in paths if os.path.splitext(p)[-1] == ".pt"]
    assert len(model_paths) >= 1


@pytest.mark.order9
def test_cancel_job(job_id, headers):
    resp = requests.delete(f"{API_URL}/jobs/{job_id}", headers=headers)
    resp.raise_for_status()
