# AgriBusiness OS AI Architecture

This document describes the implemented application flow in the current codebase.
It is based on:

- `main.py`
- `static/app.js`
- `templates/*.html`
- `src/pipelines/*.py`

## 1. System Overview

```mermaid
flowchart TB
    subgraph UI["Browser UI"]
        IDX["Planner `/`"]
        VID["Videos `/videos`"]
        STP["Startups `/startups`"]
        POL["Schemes `/policies`"]
    end

    subgraph API["Flask App (`main.py`)"]
        PLAN["POST `/api/plan`"]
        STREAM["GET `/api/plan/{job_id}/stream`"]
        TRACE["GET `/api/trace/{job_id}`"]
        FUP["POST `/api/followup`"]
        HEALTH["GET `/health`"]
        SAVEV["POST `/library/videos/save`"]
        SAVES["POST `/library/startups/save`"]
        SEARCHPOL["POST `/policies`"]
    end

    subgraph STATE["In-Memory State"]
        JOBS["`JOBS`"]
        QUEUES["`JOB_QUEUES`"]
        TRACEBUF["per-job trace events"]
    end

    subgraph FILES["File-backed Libraries"]
        VLIB["`database/video_library_urls.txt`"]
        SLIB["`database/startup_reference_library.txt`"]
    end

    subgraph AI["AI Pipelines"]
        AGRI["Agribusiness pipeline"]
        FOLLOW["Follow-up pipeline"]
        POLICY["Government policy pipeline"]
    end

    IDX --> PLAN
    IDX --> STREAM
    IDX --> TRACE
    IDX --> FUP
    VID --> SAVEV
    STP --> SAVES
    POL --> SEARCHPOL

    PLAN --> JOBS
    PLAN --> QUEUES
    STREAM --> QUEUES
    TRACE --> JOBS
    FUP --> JOBS

    SAVEV --> VLIB
    SAVES --> SLIB
    VID --> VLIB
    STP --> SLIB

    PLAN --> AGRI
    FUP --> FOLLOW
    SEARCHPOL --> POLICY

    JOBS --> TRACEBUF
```

## 2. Planner Flow

The planner starts in `static/app.js` when the user submits farm input from `/`.

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant F as Flask
    participant T as Background Thread
    participant P as Agribusiness Pipeline
    participant Q as Queue

    U->>B: Enter farm details
    B->>F: POST `/api/plan` {message, language}
    F->>F: Validate request
    F->>F: Create `job_id`
    F->>F: Initialize `JOBS[job_id]`
    F->>F: Initialize `JOB_QUEUES[job_id]`
    F->>T: Start `_run_job_background(...)`
    F-->>B: `{job_id, trace_url}`

    B->>F: GET `/api/plan/{job_id}/stream`
    F->>Q: Read progress events

    T->>P: `run_agribusiness_pipeline(...)`
    P-->>T: `progress_cb({step,status,output})`
    T->>Q: Push events
    T->>F: Save final report in `JOBS`
    T->>Q: Push `event=complete`

    Q-->>F: SSE payloads
    F-->>B: step updates + final report
    B->>B: Render markdown report + follow-up panel
```

### Planner runtime details

- `/api/plan` validates `message`, checks the agribusiness pipeline dependency, creates a job, and starts a background thread.
- `_run_job_background(...)` creates a per-thread event loop and executes the async planner pipeline.
- Step progress is pushed into `JOB_QUEUES[job_id]`.
- `_trace(...)` records job lifecycle and step timing into `JOBS[job_id]["trace"]`.
- `/api/plan/{job_id}/stream` emits SSE messages until `complete` or `error`.

## 3. Planner Agent Flow

The planner pipeline in `src/pipelines/agribusiness_pipeline.py` orchestrates the agent sequence below.

```mermaid
flowchart LR
    INPUT["Farmer input"] --> CULT["Cultivator"]
    CULT --> LOC["Location Check"]
    LOC --> CROP["Crop for Soil"]

    CROP --> WEA["Weather Analysis"]
    CROP --> MKT["Market Timing"]
    CROP --> SAL["Sales Channels"]
    CROP --> STO["Storage Proximity"]

    WEA --> PER["Perishability Risk"]
    MKT --> PER
    SAL --> PER
    STO --> PER

    PER --> FIN["Final Consolidator"]
    LOC --> FIN
    CROP --> FIN
    WEA --> FIN
    MKT --> FIN
    SAL --> FIN
    STO --> FIN

    FIN --> REPORT["Final markdown report + validation sources"]
```

## 4. Follow-up Flow

Follow-up starts only after a planner report is available.

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant F as Flask
    participant R as Follow-up Pipeline
    participant J as JOBS state

    U->>B: Ask follow-up question
    B->>F: POST `/api/followup`
    F->>J: Load report + saved followups
    F->>F: Merge server history with client history
    F->>R: `run_report_followup(report, question, history)`
    R-->>F: answer
    F->>J: Append question/answer to `followups`
    F-->>B: `{answer}`
    B->>B: Render follow-up response
```

### Follow-up runtime details

- Server-side history is reconstructed from `JOBS[job_id]["followups"]`.
- Client-provided history is merged with server memory.
- Exact `(role, content)` duplicates are removed.
- The merged window is capped at 40 turns before calling the follow-up pipeline.

## 5. Policy Search Flow

The schemes page is a classic form POST flow rather than SSE.

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant F as Flask
    participant P as Policy Pipeline

    U->>B: Submit location, crops, language
    B->>F: POST `/policies`
    F->>F: Validate form fields
    F->>P: `run_government_policy_search(...)`
    P-->>F: `report_markdown + sources`
    F-->>B: Render report and source links in HTML
```

### Policy runtime details

- Missing `location` or `crops` stays on the same page and shows a validation message.
- The server creates a temporary event loop for the async policy pipeline.
- `policy_report` and `policy_sources` are rendered directly into `templates/policies.html`.

## 6. Resource Library Flows

The video and startup pages are file-backed content views.

```mermaid
flowchart LR
    VIEWV["GET `/videos`"] --> LOADV["load_video_library()"]
    LOADV --> VFILE["video_library_urls.txt"]
    LOADV --> VTPL["Render `videos.html`"]

    VIEWS["GET `/startups`"] --> LOADS["load_startup_library()"]
    LOADS --> SFILE["startup_reference_library.txt"]
    LOADS --> STPL["Render `startups.html`"]

    SAVEV["POST `/library/videos/save`"] --> WRITEV["write_library_text(...)"]
    WRITEV --> VFILE

    SAVES["POST `/library/startups/save`"] --> WRITES["write_library_text(...)"]
    WRITES --> SFILE
```

### Library runtime details

- Video entries support either:
  - `Title | URL`
  - `URL`
- Startup entries support:
  - `Startup Name | Leverage | Description | URL`
- Save routes redirect back to the page with `?saved=1` on success.
- Save routes redirect with `?error=...` on file-system write errors.

## 7. Traceability Model

Trace data is stored in memory with the job record.

```mermaid
flowchart TD
    CREATE["job_created"] --> START["job_runner_started"]
    START --> STEP1["agent_step_running"]
    STEP1 --> STEP2["agent_step_completed"]
    STEP2 --> DONE["job_runner_completed or job_runner_failed"]
    DONE --> STREAM["stream_connected / stream_disconnected"]
    DONE --> FOLLOW["followup_received / followup_answered / followup_failed"]
```

The trace endpoint returns:

- `status`
- `error`
- `event_count`
- `events`
- `step_metrics`

## 8. Dependency Loading Strategy

The app lazy-loads runtime pipeline callables through `_load_runtime_callable(...)`.

This matters because:

- `/videos` and `/startups` can render without AI dependencies installed.
- `/api/plan`, `/api/followup`, and `/policies` fail gracefully with a clear dependency error if the active environment is missing required AI packages.

## 9. Test Coverage Added

Formal flow coverage now lives in:

- `test_app_flows.py`
- `test_resource_libraries.py`

Covered flows:

- index page
- health endpoint
- video library read/write flow
- startup library read/write flow
- planner create job flow
- planner SSE stream flow
- planner trace flow
- follow-up validation and success/error flows
- policy form validation and success/error flows
- dependency-missing failure paths

## 10. Main Runtime Entry Points

- Web app entry: `main.py`
- WSGI entry: `wsgi.py`
- Planner frontend logic: `static/app.js`
- Planner pipeline: `src/pipelines/agribusiness_pipeline.py`
- Follow-up pipeline: `src/pipelines/report_followup_pipeline.py`
- Policy pipeline: `src/pipelines/government_policy_pipeline.py`
