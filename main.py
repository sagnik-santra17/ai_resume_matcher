import json 
import time
import logging
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from pypdf import PdfReader

from utils import generate_ats_prompt, client


# ------------------------------------------------------------------------------------------------------ #


# Logging 
logger = logging.getLogger(__name__)


# Main FastAPI application
app = FastAPI(
    title="ATS API: Check your Resume score against a Job Description",
    description="An API for ATS (Applicant Tracking System) and technical recruiters.",
    version="1.0.0"
)

# Basemodel: The output schema of the API
class AnalysisResult(BaseModel):
    match_score_out_of_10: float
    missing_keywords: list[str]
    reasoning: str

# Main endpoint: Analyze the Resume against the Job Description
@app.post("/analyze_resume", response_model=AnalysisResult)
async def analyze_resume(
    job_description: str = Form(...), 
    resume_file: UploadFile = File(...) 
):

    # 1. Validate the file type (only ".pdf" files are allowed)
    if not resume_file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only PDF files are allowed."
        )

    # 2. Extract the resume text from the PDF
    try:
        reader = PdfReader(resume_file.file)
        resume_text = ""

        for page in reader.pages:
            resume_text += page.extract_text() or ""

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to extract resume text: {str(e)}"
        )

    # 3. Check if the PDF file empty
    if not resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="The uploaded PDF does not contain any readable text. Scanned image PDFs are not supported."
        )

    # 4. Generate the prompt for the ATS model
    prompt = generate_ats_prompt(job_description, resume_text)


    # 5. Call Gemini with fallback models and retry for 503 errors
    models = [
        "gemini-3.7-flash", # -> primary
        "gemini-2.0-flash-exp", # -> fallback 1
        "gemini-1.5-flash" # -> fallback 2
    ]

    max_retries = 3
    retry_delay = 2

    for model in models:
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting with model: {model} (try {attempt+1}/{max_retries})")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )

                result_data = json.loads(response.text)
                return AnalysisResult(**result_data)

            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"{model} 503, retry {attempt+1}/{max_retries} in {retry_delay}s")
                    time.sleep(retry_delay)
                    continue
                # If this model failed after all retries, log and try next model
                logger.warning(f"{model} failed after {attempt+1} attempts: {str(e)}")
                break  # exit retry loop for this model

    # If all models fail
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="All AI models temporarily unavailable. Please try again later."
    )