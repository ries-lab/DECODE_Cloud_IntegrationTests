# DECODE_Cloud_IntegrationTests
Integration tests for DECODE OpenCloud.

**Requires**:
 * Deployed backed (typically through `DECODE_AWS_Infrastructure`)
   * User-facing and worker-facing APIs
   * Worker pulling and working on jobs (e.g. cloud worker if deploying the whole infrastructure)
   * Application `decode` with version `v0_10_1` and entrypoint `train` (see `DECODE_AWS_Infrastructure`, build locally and push with `python -m scripts push_local_dockerimage decode:v0_10_1`)
 * Configuration (environment variables in `.env`)
   * `API_URL`
   * `ID_TOKEN` to login, or `EMAIL` and `PASSWORD` if the user-facing API exposes endpoint `POST /token`
   * `DEVICE="cpu"` if the worker does not have a GPU
   * `ENVIRONMENT="cloud"` if testing with a cloud worker, else `"local"`

**Test flow**:
 * [Gets ID token to authenticate]
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
