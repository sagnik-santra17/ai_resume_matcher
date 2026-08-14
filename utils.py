from dotenv import load_dotenv
from google import genai




# Loading the environment variables
load_dotenv()

# Creating the Gemini client
client = genai.Client()



# Constructing a clean, structured prompt for the Gemini model
def generate_ats_prompt(job_description: str, resume_text: str) -> str:

  return f"""
    You are an expert ATS (Applicant Tracking System) and technical recruiter.
    Analyze the following Resume against the Job Description.
    
    Job Description:
    {job_description}
    
    Resume Text:
    {resume_text}
    
    Task:
    1. Give a match score out of 10 (float, e.g., 7.5).
    2. Identify important technical or domain-specific keywords/skills missing from the resume that are present in the job description (e.g., python, photoshop, agile, django).
    3. Provide a brief explanation for the score.
    
    Respond strictly in valid JSON format matching this schema:
    {{
      "match_score_out_of_10": 0.0,
      "missing_keywords": ["keyword1", "keyword2"],
      "reasoning": "brief text explanation"
    }}
    """