# DECODE_Cloud_IntegrationTests
Integration tests for [DECODE OpenCloud](https://github.com/ries-lab/DECODE_Cloud_Documentation).

## Run the DECODE OpenCloud stack locally
**Requirements**
 * Docker and docker-compose installed.
 * Repositories locally cloned (and checked out to the branch to run)
   * [User-facing API](https://github.com/ries-lab/DECODE_Cloud_UserAPI);
   * [Worker-facing API](https://github.com/ries-lab/DECODE_Cloud_WorkerAPI);
   * [Frontend](https://github.com/ries-lab/DECODE_Cloud_UserFrontend);
   * [Job fetcher](https://github.com/ries-lab/DECODE_Cloud_JobFetcher).
 * AWS Cognito
   * User pool with public client;
   * Worker user in the user pool (i.e., member of a "workers" group);
   * To run the integration tests: user in the user pool (i.e., member of a "users" group). Note that this could be the same as the worker user.

**How to start**
 * Copy `.env.example` to `.env` and fill it out accordingly.
 * Run `docker compose up` (or `docker compose up -d` to have it run in the background and `docker compose down` to stop it).

**Notes**
 * It can happen that environment variables are not updated between successive runs.
   To avoid this, open a new terminal if you change the environment variables in `docker-compose.yaml`.
 * The frontend will be available only on `http://localhost:8080`, not on `http://127.0.0.1:8080`, because of CORS settings.

## Run the integration tests

**Execution modes**:
 * Locally
   * `poetry install`
   * `cp .env.example .env` and fill out `.env` appropriately
   * `poetry run pytest tests/ <options>`
 * Github
   * Trigger the `Run tests` action

**Execution environments**:
 * Local (`--local`): locally deployed services using `docker-compose.yaml`
 * Dev (`--dev`): services deployed on AWS dev stack
 * Prod (`--prod`): services deployed on AWS prod stack
The Dev and Prod environment require the [AWS Infrastructure](https://github.com/ries-lab/DECODE_AWS_Infrastructure) to be deployed.

**Worker configuration**:  
Use `--cloud` to run the test jobs on cloud (AWS) workers.
This is not possible with locally deployed services.

Use `--gpu` to run the test jobs with a GPU.
This is not possible with locally deployed services.

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
 * Deletes the ran job.
 * Deletes the input/output files of the job.

## Cleanup
Run `poetry run docker-cleanup` to clean-up the space taken up by docker for these tests.