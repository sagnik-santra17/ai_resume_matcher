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


    # 5. Call Gemini with the utility prompt (with auto-retry for 503 errors)
    max_retries = 3
    retry_delay = 2  # seconds to wait before retrying

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.7-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                },
            )

            # If successful, parse and return immediately
            result_data = json.loads(response.text)
            return AnalysisResult(**result_data)

        except Exception as e:
            # Check if it's a temporary 503 server error and we have retries left
            if "503" in str(e) and attempt < max_retries - 1:
                # Log the retry attempt so we can monitor how often this happens
                logger.warning(f"Gemini 503 error, retry {attempt+1}/{max_retries} in {retry_delay}s")
                time.sleep(retry_delay)
                continue  # Try the loop again

            # If it's a different error (like 400 or 404), or we ran out of retries, raise it
            logger.error(f"Gemini failed after {attempt+1} attempts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI processing failed: {str(e)}"
            )
