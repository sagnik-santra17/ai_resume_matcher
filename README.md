# AI Resume Matcher (ATS API)

A FastAPI service that scores how well a resume matches a job description, the way an Applicant Tracking System (ATS) would. Upload a resume PDF and a job description, and get back a match score, missing keywords, and a short explanation — powered by Google's Gemini AI.

Live URL: https://ai-resume-matcher-uxrk.onrender.com/docs

## Features

- **Single endpoint** — `POST /analyze_resume` accepts a job description and a resume PDF in one request.
- **PDF text extraction** — parses the uploaded resume with `pypdf`, with validation for file type and empty/unreadable PDFs.
- **AI-powered scoring** — sends a structured prompt to Gemini and gets back a strict JSON response: score out of 10, missing keywords, and reasoning.
- **Retry logic** — automatically retries up to 3 times on transient `503` errors from the Gemini API.
- **Fallback models** — if the primary model (`gemini-3.7-flash`) fails, it seamlessly tries `gemini-2.0-flash-exp` and then `gemini-1.5-flash` before giving up.
- **Logging** — every retry and model switch is logged, so you can monitor performance and failure rates.
- **Dockerized** — ships with a `Dockerfile` and `docker-compose.yml` for one-command startup

## Tech Stack

- **FastAPI** — web framework and request validation
- **Pydantic** — response schema (`AnalysisResult`)
- **pypdf** — resume text extraction
- **google-genai** — Gemini API client
- **python-dotenv** — environment variable loading
- **Docker / Docker Compose** — containerized deployment

## API

### `POST /analyze_resume`

**Request** (`multipart/form-data`):

| Field             | Type     | Description                               |
| ----------------- | -------- | ----------------------------------------- |
| `job_description` | `string` | The job description text to match against |
| `resume_file`     | `file`   | Resume as a `.pdf` file                   |

**Response** (`200 OK`):

```json
{
  "match_score_out_of_10": 7.5,
  "missing_keywords": ["docker", "kubernetes"],
  "reasoning": "The resume covers most core requirements but lacks direct experience with containerization tools mentioned in the job description."
}
```

**Error responses:**

| Status | Cause                                                                           |
| ------ | ------------------------------------------------------------------------------- |
| 400    | File is not a `.pdf`, or the PDF has no extractable text (e.g. a scanned image) |
| 500    | Text extraction failed, or the AI request failed after retries                  |
| 503    | All AI models are temporarily unavailable. Try again later.                     |

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/sagnik-santra17/ai_resume_matcher.git
cd ai_resume_matcher
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run locally

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 4. Run with Docker

```bash
docker-compose up --build
```

Make sure your `.env` file with `GEMINI_API_KEY` is present in the project root — `docker-compose.yml` passes it into the container.

## Project Structure

```text
ai_resume_matcher/
├── main.py              # FastAPI app and /analyze_resume endpoint
├── utils.py              # Gemini client setup, prompt construction, and fallback logic
├── requirements.txt       # Python dependencies
├── Dockerfile              # Container image definition
├── docker-compose.yml       # Local orchestration
└── .gitignore
```

## Notes

- Only text-based PDFs are supported; scanned/image-only resumes will be rejected.
- The API uses a fallback chain of Gemini models: `gemini-3.7-flash` → `gemini-2.0-flash-exp` → `gemini-1.5-flash`. This ensures higher availability even if one model is overloaded.
- All retries and model switches are logged — check the console (or `docker logs`) to monitor what's happening behind the scenes.
- The retry delay starts at 2 seconds and is not exponential (fixed delay) to keep the response time predictable.
