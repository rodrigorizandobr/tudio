# Tudio V2 — AI-Powered Video Generator

Tudio is a full-stack platform that automates end-to-end video production using AI. Given a topic or prompt, it generates a structured script (chapters → subchapters → scenes), searches for matching visuals (images and stock footage), synthesizes voice narration, assembles multi-format video clips, burns animated captions, and publishes directly to YouTube — all from a single interface.

---

## Table of Contents

- [What Problem It Solves](#what-problem-it-solves)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration (Environment Variables)](#configuration-environment-variables)
- [Running the Application](#running-the-application)
- [How It Works — Full Pipeline](#how-it-works--full-pipeline)
- [API Reference](#api-reference)
- [Available Commands](#available-commands)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Security](#security)

---

## What Problem It Solves

Creating video content is time-consuming: writing a script, finding images/footage, recording narration, adding subtitles, and editing everything together can take hours. Tudio compresses this entire workflow into minutes. A creator provides a topic and target duration; the platform handles the rest — from scripted scenes to a finished video file ready to upload.

---

## Key Features

### AI Script Generation
- Uses the **OpenAI Assistants API** (with persistent threads) to iteratively generate: chapters → subchapters → scenes.
- Configurable **AI Agents** let you define custom system prompts for different content styles (e.g., documentary, educational, podcast).
- Supports multiple languages (default: `pt-BR`).
- Define **custom characters** with persona descriptions and voice assignments.

### Visual Asset Pipeline
- **Image search** from multiple providers: Unsplash, Google (SerpApi), Bing, and a local cache.
- **Stock video search** from Pexels, Pixabay, and Google.
- Built-in **image cropping** per scene, with original and cropped versions stored separately.
- **Auto-image mode** can automatically fetch and assign images to scenes after script generation.

### AI Narration (Text-to-Speech)
- Generates scene-level voice narration using **OpenAI TTS** with 14+ available voices.
- Each character in the script can be assigned a specific voice (alloy, nova, shimmer, echo, onyx, etc.).
- Audio files are stored per-scene at `storage/audios/<video_id>/`.

### Video Rendering
- Assembles final videos using **MoviePy** + **FFmpeg**.
- Supports multiple output aspect ratios: **16:9** (horizontal/YouTube), **9:16** (vertical/Reels), **1:1** (square).
- Optional background music track (MP3 upload and management).
- Progress is tracked in real-time per video (0–100%).

### Animated Captions
- Word-by-word caption generation using **OpenAI Whisper** for precise timing.
- 5 caption animation styles: `karaoke`, `word_pop`, `typewriter`, `highlight`, `bounce`.
- Captions are burned into the video using FFmpeg's ASS subtitle filter.
- Configurable font, color, size, and position per style.

### YouTube Publishing
- Full **Google OAuth 2.0** integration to connect YouTube channels.
- Direct video upload to YouTube with title, description, and tags from the project metadata.

### Project Management
- **Soft delete & restore** for video projects.
- **Duplicate** a video project.
- **Audit logging**: every user action (create, delete, publish, etc.) is recorded in Datastore.
- Per-video status tracking: `pending → processing → rendering → completed / error / cancelled`.

### Authentication & Access Control
- **JWT-based authentication** with 24-hour token expiration.
- **RBAC** (Role-Based Access Control) via Groups with rule sets stored in Datastore.
- Rate limiting per IP using SlowAPI.

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│              Frontend (Vue 3 + Vite)    │
│  Dashboard · Video Wizard · Agents ·    │
│  Voices · Music · Social · Settings     │
└─────────────────┬───────────────────────┘
                  │ HTTP (REST)
┌─────────────────▼───────────────────────┐
│            Backend (FastAPI)            │
│                                         │
│  ┌──────────┐  ┌────────────────────┐   │
│  │ API v1   │  │  Background Tasks  │   │
│  │ Routers  │  │  (Video Pipeline)  │   │
│  └────┬─────┘  └──────────┬─────────┘   │
│       │                   │             │
│  ┌────▼───────────────────▼──────────┐  │
│  │           Services Layer          │  │
│  │ VideoService · AudioService ·     │  │
│  │ RenderService · CaptionService ·  │  │
│  │ SocialService · AgentService …    │  │
│  └────────────────┬──────────────────┘  │
│                   │                     │
│  ┌────────────────▼──────────────────┐  │
│  │       Repositories (Datastore)    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │              │
  Google Cloud     OpenAI API
  Datastore        (Assistants · TTS · Whisper)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python 3.10+) |
| Frontend framework | Vue 3 + TypeScript + TailwindCSS (Vite) |
| Database | Google Cloud Datastore (Firestore in Datastore mode) |
| AI API | OpenAI (Assistants API, TTS, Whisper) |
| Video processing | MoviePy + FFmpeg |
| Image processing | Pillow (PIL) |
| Audio processing | stable-ts (Whisper alignment) |
| Authentication | JWT (python-jose + passlib) |
| Rate limiting | SlowAPI |
| Scheduling | APScheduler |
| E2E testing | Playwright |
| Unit testing | pytest + vitest |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for frontend build and E2E tests)
- **FFmpeg** with `libass` support (required for caption rendering)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `apt-get install ffmpeg`
  - Verify: `ffmpeg -filters | grep ass`
- **Google Cloud SDK (gcloud CLI)** — authenticated with a project that has Datastore enabled
- An **OpenAI API Key**

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd tudio
```

### 2. Set up Google Cloud

```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set your project (dev environment)
gcloud config set project tudio-dev
```

Make sure **Firestore in Datastore mode** is enabled in your GCP project.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials (see [Configuration](#configuration-environment-variables) below).

### 4. Install all dependencies

```bash
make install
```

This installs both Python backend dependencies and Node.js frontend dependencies.

Or manually:

```bash
# Backend
python -m pip install -r requirements.txt
playwright install chromium

# Frontend
cd frontend && npm install
```

---

## Configuration (Environment Variables)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key (Assistants, TTS, Whisper) |
| `OPENAI_MODEL` | No | `gpt-3.5-turbo` | OpenAI model to use for script generation |
| `JWT_SECRET_KEY` | **Yes** (prod) | `CHANGE_ME_IN_PRD_SECRET_KEY` | Secret key for signing JWT tokens |
| `APP_ENV` | No | `dev` | Environment: `dev`, `hml`, or `prd` (maps to GCP project) |
| `UNSPLASH_ACCESS_KEY` | No | — | Unsplash API key for image search |
| `SERPAPI_API_KEY` | No | — | SerpApi key for Google image/video search |
| `PEXELS_API_KEY` | No | — | Pexels API key for stock video search |
| `PIXABAY_API_KEY` | No | — | Pixabay API key for stock video search |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID (YouTube publishing) |
| `GOOGLE_CLIENT_SECRET` | No | — | Google OAuth client secret (YouTube publishing) |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:8000/api/v1/social/auth/callback` | OAuth callback URL |
| `USE_PROXY` | No | `False` | Enable HTTP/SOCKS5 proxy for outbound requests |
| `PROXY_HOST` | No | `localhost` | Proxy host |
| `PROXY_PORT` | No | `1080` | Proxy port |

### GCP Project mapping (via `APP_ENV`)

| `APP_ENV` | GCP Project |
|---|---|
| `dev` | `tudio-dev` |
| `hml` | `tudio-hml` |
| `prd` | `tudio-prd` |

---

## Running the Application

### Start (foreground, with auto-reload)

```bash
make start
```

### Start (background)

```bash
make start-bg
```

Logs are written to `storage/logs/server.out`.

### Stop

```bash
make stop
```

### Access

| Interface | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/doc |
| Static files / media | http://localhost:8000/api/storage/ |

On first startup, the application automatically seeds:
- A **Super Admin** group with full permissions (`*`).
- An **admin user** (`rodrigorizando@gmail.com`).
- A **default AI Agent** from the prompts defined in `.env`.

---

## How It Works — Full Pipeline

When a user creates a new video project, it goes through the following automated pipeline (all steps run in background tasks):

```
1. User submits a prompt + target duration + language + agent + characters
         │
2. OpenAI Assistants API generates the script structure:
   ├── Chapters (high-level topics)
   │   └── Sub-chapters (logical sections)
   │       └── Scenes (individual clips with narration text + image/video prompts)
         │
3. For each scene:
   ├── Image search (Unsplash / SerpApi / Bing) — if auto-image is enabled
   ├── Image download + crop to target aspect ratio
   └── TTS narration generated (OpenAI TTS voice per character)
         │
4. Video rendering (MoviePy + FFmpeg):
   ├── Each scene → image clip + audio clip → scene video
   ├── All scenes concatenated
   ├── Optional background music mixed in
   └── Output: final_horizontal.mp4 (16:9) and/or final_vertical.mp4 (9:16)
         │
5. (Optional) Caption generation:
   ├── Word-level timestamps via Whisper or forced alignment
   ├── ASS subtitle file generated
   └── Captions burned into video via FFmpeg
         │
6. (Optional) YouTube publish via Google OAuth
```

**Progress tracking**: Each video has a `progress` field (0–100%) updated throughout the pipeline, visible in real-time from the frontend.

---

## API Reference

Base path: `/api/v1`

| Router | Prefix | Description |
|---|---|---|
| Videos | `/videos` | Create, list, get, delete, restore, duplicate video projects; trigger rendering and narration |
| Auth | `/auth` | Login (JWT), refresh token |
| Users | `/users` | User management |
| Agents | `/agents` | CRUD for AI agents with custom prompts |
| Images | `/images` | Search (Unsplash, SerpApi, Bing, cache) + download + crop |
| Video Search | `/video-search` | Search (Pexels, Pixabay, Google) + download stock footage |
| Voices | `/voices` | List available TTS voices with metadata and demo URLs |
| Music | `/music` | Upload, list, and delete background music tracks |
| Social | `/social` | Google OAuth flow + YouTube channel listing + video upload |
| Captions | *(root)* | `/videos/{id}/captions/generate` — trigger caption generation |
| Settings | `/settings` | Application settings |

Full interactive documentation is available at **http://localhost:8000/doc** after starting the server.

---

## Available Commands

| Task | `make` | Description |
|---|---|---|
| Install all dependencies | `make install` | Backend (pip) + frontend (npm) |
| Start server (foreground) | `make start` | Uvicorn with `--reload` |
| Start server (background) | `make start-bg` | Runs as background process, outputs PID |
| Stop server | `make stop` | Kills process by PID file + port scan |
| Run all tests | `make test` | Unit + integration + E2E |
| Run unit tests | `make test-unit` | Backend pytest + frontend vitest |
| Run integration tests | `make test-int` | Backend integration tests |
| Run E2E tests | `make test-e2e` | Playwright browser tests |
| Build frontend | `make build` | Vite production build |
| Clean artifacts | `make clean` | Removes dist, `__pycache__`, coverage |

NPM aliases are also available from the project root (e.g., `npm run start`, `npm test`).

---

## Testing

```bash
# All tests (unit + integration + E2E)
make test

# Backend unit tests only (with coverage)
PYTHONPATH=. python -m pytest backend/tests/unit --cov=backend --cov-report=term-missing

# Backend integration tests only
PYTHONPATH=. python -m pytest backend/tests/integration

# Frontend unit tests
cd frontend && npm run test:unit

# E2E tests (requires running server)
cd frontend && npx playwright test
```

Coverage thresholds:
- Unit tests: 70% minimum
- Integration tests: 80% minimum

---

## Project Structure

```
tudio/
├── backend/                    # FastAPI backend
│   ├── main.py                 # Application entrypoint (CORS, middleware, routing)
│   ├── api/v1/routers/         # REST API endpoints
│   ├── services/               # Business logic
│   │   ├── video_service.py    # Script generation orchestration
│   │   ├── render_service.py   # MoviePy video assembly
│   │   ├── audio_service.py    # OpenAI TTS narration
│   │   ├── caption_service.py  # Whisper + ASS caption pipeline
│   │   ├── image_storage_service.py
│   │   ├── social_service.py   # Google OAuth + YouTube upload
│   │   ├── agent_service.py    # AI Agent management
│   │   └── openai_service.py   # OpenAI Assistants API wrapper
│   ├── repositories/           # Datastore persistence layer
│   ├── models/                 # Pydantic data models
│   ├── core/                   # Config, logger, rate limiting, caption styles
│   └── middleware/             # Security headers middleware
├── frontend/                   # Vue 3 + TypeScript SPA
│   └── src/
│       ├── views/              # Dashboard, VideoWizard, Agents, Music, Social, etc.
│       ├── components/         # Reusable UI components
│       ├── stores/             # Pinia state management
│       └── services/           # API client services
├── storage/                    # Local file storage (git-ignored)
│   ├── audios/                 # Generated TTS audio files
│   ├── videos/                 # Rendered video outputs
│   ├── images/                 # Downloaded/cropped scene images
│   ├── musics/                 # Uploaded background music tracks
│   ├── data/                   # JSON persistence (fallback)
│   ├── cache/                  # Image/video search cache
│   └── logs/                   # Application logs
├── tests/                      # Top-level integration/E2E tests
├── Makefile                    # Build and task automation
├── requirements.txt            # Python dependencies
└── start.sh / stop.sh         # Convenience startup/shutdown scripts
```

---

## Security

The application implements several security measures aligned with OWASP guidelines:

- **Security headers** (via `SecurityHeadersMiddleware`): CSP, `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`, `Referrer-Policy`, `Permissions-Policy`.
- **CORS** restricted to known origins.
- **Rate limiting** per IP (SlowAPI) to prevent abuse; disabled during testing via `BYPASS_RATE_LIMIT=True`.
- **JWT authentication** required on all protected endpoints.
- **Password hashing** with bcrypt.
- **Audit logs** for all sensitive operations (create, delete, publish, etc.), stored in Datastore.
- **Input validation** via Pydantic models on all API endpoints.

> **Important**: Before deploying to production, replace `JWT_SECRET_KEY` in `.env` with a strong randomly generated secret, and restrict `allow_origins` in CORS settings to your production domain.
| :--- | :--- | :--- |
| **Start (Foreground)** | `make start` | `npm start` |
| **Start (Background)** | `make start-bg` | - |
| **Stop Server** | `make stop` | `npm stop` |
| **Full Build** | `make build` | `npm run build` |
| **All Tests** | `make test` | `npm test` |
| **Unit Tests Only** | `make test-unit` | `npm run test:unit` |
| **Integration Tests** | `make test-int` | `npm run test:int` |
| **E2E Tests** | `make test-e2e` | `npm run test:e2e` |
| **Clean Cache** | `make clean` | - |

> [!NOTE]
> `npm start` now runs the server in the foreground, showing logs directly in your terminal. Use `Ctrl+C` to stop it.

### Legacy Scripts
*   `./start.sh`: Full pre-flight check, install, build, and start with quality gates.
*   `./stop.sh`: Graceful shutdown.

## Architecture
... (rest of the file)
