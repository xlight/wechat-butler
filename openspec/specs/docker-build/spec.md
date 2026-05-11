## Purpose

Docker image build infrastructure for WeChat Butler, producing a minimized production-ready container image.

## Requirements

### Requirement: Multi-stage Dockerfile build
The system SHALL provide a Dockerfile using multi-stage build (builder + runtime) based on `python:3.11-slim` to produce a minimized production image.

#### Scenario: Build produces valid image
- **WHEN** `docker build -t wechat-butler .` is executed
- **THEN** a Docker image is produced with the application installed and ready to run

#### Scenario: Builder stage installs dependencies
- **WHEN** the builder stage runs
- **THEN** `pip install` is executed with the project's dependencies from `pyproject.toml` / `requirements.txt`

#### Scenario: Runtime stage excludes build tools
- **WHEN** the runtime stage completes
- **THEN** the image SHALL NOT contain setuptools, wheel, or other build-only dependencies

### Requirement: Non-root user execution
The system SHALL create and run the container as a non-root user `butler` (UID 1000).

#### Scenario: Container runs as non-root
- **WHEN** the container starts
- **THEN** the process SHALL be running as user `butler` (UID 1000), not root

#### Scenario: Application files owned by butler user
- **WHEN** the image is built
- **THEN** all application files under `/app` SHALL be owned by the `butler` user

### Requirement: Built-in health check
The system SHALL include a Docker HEALTHCHECK directive that probes the `/health` endpoint.

#### Scenario: Healthy container passes check
- **WHEN** the application is running normally
- **THEN** `docker inspect` SHALL report the container health status as `healthy`

#### Scenario: Unhealthy container fails check
- **WHEN** the application is not responding on the configured port
- **THEN** the health check SHALL fail and Docker SHALL report status as `unhealthy`

### Requirement: Dockerignore file
The system SHALL include a `.dockerignore` file that excludes non-essential files from the build context.

#### Scenario: Build context excludes irrelevant files
- **WHEN** `docker build` is executed
- **THEN** files matching `.git`, `__pycache__`, `.env`, `*.pyc`, `.venv`, `openspec`, `docs`, `.sisyphus` SHALL NOT be included in the build context
