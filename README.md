# DECODE_Cloud_IntegrationTests
Integration tests for [DECODE OpenCloud](https://github.com/ries-lab/DECODE_Cloud_Documentation).

**Requirements**:
 * Deployed backend (e.g. through [AWS infrastructure](https://github.com/ries-lab/DECODE_AWS_Infrastructure))
   * [User-facing](https://github.com/ries-lab/DECODE_Cloud_UserAPI) and [worker-facing]((https://github.com/ries-lab/DECODE_Cloud_WorkerAPI)) APIs
   * Worker pulling and working on jobs (e.g. cloud worker [on AWS](https://github.com/ries-lab/DECODE_AWS_Infrastructure), or [local worker](https://github.com/ries-lab/DECODE_Cloud_JobFetcher))
   * Application `decode` with version `v0_10_1` and entrypoint `train` (see [DECODE_AWS_Infrastructure](https://github.com/ries-lab/DECODE_AWS_Infrastructure))
 * [Optional] Linked frontend ([frontend](https://github.com/ries-lab/DECODE_Cloud_UserFrontend))
 * A user in the Cognito user pool used by the APIs
The resources are either already deployed (`--dev` or `--prod`), or deployed locally automatically (`--local`).

**Execution modes**:
 * Locally (requires docker-compose): `poetry install`; `cp .env.example .env` and fill out appropriately; `poetry run pytest tests/ <options>`
 * Using the Github `Run tests` action

**Execution environments**:
 * Local (`--local`): locally deployed services using `docker-compose.yaml`
 * Dev (`--dev`): services deployed on AWS dev stack
 * Prod (`--prod`): services deployed on AWS prod stack

**Worker configuration**:  
Use `--cloud` to run the test jobs on cloud (AWS) workers.

**Test flow**:
 * [Gets ID token to authenticate.]
 * Checks that the files to upload do not exist.
 * Uploads configuration and data (2-step: get pre-signed url, post to pre-signed url).
 * Gets the list of files, checks that the uploaded files are there.
 * Starts a job, tests that it is `queued`.
 * Waits at most 10 minutes for the status to be changed to `pulled`.
 * Waits at most 10 minutes for the status to be changed to `preprocessing`.
 * Waits at most 10 minutes for the status to be changed to `running`.
 * Waits at most 30 minutes for the status to be changed to `postprocessing`.
 * Waits at most 10 minutes for the status to be changed to `finished`.
 * Downloads the output `param_run_in.yaml` (2-step pre-signed url, get from pre-signed url), checks that a `.pt` file is present in the output.
 * Tries deleting the ran job (as a side-effect, cleaning up the test).
