# Strata

Strata is a source-locked investigation agent for archived video: ask how
an official explanation, deadline, or status changed, and it reconstructs a
chronological trail of exact playable moments. Every displayed factual sentence
names the event IDs that support it. A separate challenge pass searches unused
footage for evidence that may qualify or revise the first answer.

The MVP archive follows NASA's 2022 Artemis I launch campaign. Source footage is
courtesy of NASA; NASA does not endorse this project.

## Current status

The backend engine, API contract, frontend, deterministic comparison rules,
evidence gate, sentence source lock, challenge logic, reel path, and Evidence
Packet export are implemented and tested.

The six official videos are ingested in one live VideoDB collection. All six
have spoken-word, OCR, and visual-context artifacts and retrieval indexes. The
two locked Phase 1 source windows have been replayed from distinct VideoDB
videos, and their chronological two-shot reel compiles to a playable stream.
The 12-question evaluation set is frozen in `data/evaluation_cases.json`.

The repository is **not marked submission-ready until the real two-arm
evaluation is completed and manually adjudicated**. The application reports
missing or failed live data honestly; it never substitutes sample investigation
responses.

Run the readiness gate at any time:

```bash
./.venv/bin/python -m pipeline.verify
```

## Architecture

- `frontend/` — Next.js investigation workspace with HLS playback, sentence to
  event inspection, challenge impact, reel generation, and packet download.
- `services/api/` — FastAPI routes, strict Pydantic schemas, VideoDB adapter,
  deterministic comparison, evidence gate, source lock, and investigation
  orchestration.
- `pipeline/` — independently runnable ingest, understanding, extraction,
  custom-index, evaluation, and verification stages.
- `data/archive_manifest.json` — versioned six-video source manifest and the two
  manually verified critical-path windows.

The investigation path is:

```text
VideoDB search → runtime hydration → dedupe → deterministic diff
→ playable-shot hydration → evidence gate → sentence source lock → API
```

The challenge path repeats archive-wide retrieval with counter-queries, boosts
unused source videos, applies the same gates, and preserves the first answer.

## VideoDB primitives used

Strata uses VideoDB for the media operations it is designed to provide:

- collection creation and URL upload;
- spoken-word, OCR, and VLM understanding artifacts;
- user-supplied temporal custom indexes (`claim_events_v1` and
  `timeline_findings_v1`);
- semantic search, structured query, and aggregate counts;
- exact timestamped HLS source streams;
- sandbox text generation for strict JSON claim extraction;
- editor timeline compilation for the chronological evidence reel.

All VideoDB calls pass through `services/api/adapters/videodb_client.py`.
Credentials stay server-side and never enter the manifest or frontend bundle.

## Local setup

Requirements: Python 3.11+ and Node.js compatible with Next.js 16.

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env.local
```

Add a real `VIDEODB_API_KEY` to `.env.local`. Process-level environment
variables take precedence, and `.env` remains supported for shared defaults.
Then install the frontend:

```bash
cd frontend
npm install
cd ..
```

Start both services in separate terminals:

```bash
./.venv/bin/uvicorn services.api.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

The frontend defaults to `http://127.0.0.1:8000`. For another backend URL, put
`NEXT_PUBLIC_API_BASE_URL=...` in `frontend/.env.local`.

## Build the live archive

The Phase 1 commands prove the locked two-source path:

```bash
./.venv/bin/python -m pipeline.ingest --phase1
./.venv/bin/python -m pipeline.understand --phase1
./.venv/bin/python -m pipeline.extract_claims --phase1
./.venv/bin/python -m pipeline.build_index
```

Manually replay these ingested VideoDB windows and compile them into one stream:

- 3 September: `01:26–01:41` — liquid-hydrogen leak and scrub;
- 30 September: `01:55–02:19` — Hurricane Ian forecast and rollback.

Confirm that they have different VideoDB `video_id` values. Then run the same
pipeline without `--phase1` for all six videos. The understand stage falls back
to bounded, timestamped records from the real VideoDB transcript if an
analyzer's oversized speech scenes cannot be embedded. Pipeline stages fail
visibly on missing credentials or media errors and do not write invented
substitutes.

## API

```text
GET  /api/health
GET  /api/archive
POST /api/investigations
GET  /api/investigations/{id}
POST /api/investigations/{id}/challenge
POST /api/investigations/{id}/reel
GET  /api/investigations/{id}/packet
```

Request and response models are defined in `services/api/schemas/`.

## Verification

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall -q services pipeline tests
cd frontend && npm run lint && npm run build
```

The comparative evaluation utilities live in `pipeline/evaluate.py`. They lock
the baseline prompt/configuration and calculate relevant-event recall and
unsupported-claim rate from explicit adjudications. Do not publish comparison
percentages until both real arms complete all 12 frozen questions.

Run both live arms and create the human-review worksheet:

```bash
./.venv/bin/python -m pipeline.run_evaluation
```

Review every atomic proposition in `data/evaluation_worksheet.json` against its
cited footage and set each `supported` field to `true` or `false`. Unreviewed
values remain `null`; the finalizer refuses to publish them:

```bash
./.venv/bin/python -m pipeline.finalize_evaluation
./.venv/bin/python -m pipeline.evaluate data/evaluation_results.json
```

No evaluation percentages in this README are estimated or fabricated.
