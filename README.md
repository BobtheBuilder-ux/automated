# Automated Job Application System

An automated system that generates tailored cover letters based on uploaded CVs and job descriptions using OpenAI's GPT-4.

## Features

- Upload CV (PDF)
- Upload optional certificates
- Extract text from CV
- Generate customized cover letters using GPT-4
- Save cover letters as PDFs
- Enforce application limits (4 per day, 30 per week)

## Tech Stack

- FastAPI (Python web framework)
- Jinja2 (HTML templating)
- OpenAI API (GPT-4)
- pdfplumber (PDF text extraction)
- xhtml2pdf (PDF generation)
- Redis (Rate limiting)

## Folder Structure

```
project-root/
│
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── routes/
│   │   └── application.py      # Handles form submission
│   ├── services/
│   │   ├── gpt_generator.py    # GPT prompt + OpenAI call
│   │   ├── file_handler.py     # Save uploaded files
│   │   ├── pdf_parser.py       # Parse CV PDF
│   │   └── pdf_writer.py       # Save cover letter to PDF
│   ├── utils/
│   │   └── limiter.py          # Redis-based application counter
│   ├── templates/
│   │   └── form.html           # HTML form
│   └── static/uploads/         # Uploaded CVs and cover letters
│
├── frontend/                   # Placeholder for React or Vue frontend
│
├── .env                        # Environment variables
└── requirements.txt            # Dependencies
```

## Prerequisites

- Python 3.7+
- Redis server running locally or remotely
- OpenAI API key

## Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd automated-job-application
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://localhost:6379
DAILY_LIMIT=4
WEEKLY_LIMIT=30
```

5. Make sure Redis is running:

```bash
# For local Redis installation
redis-server
```

## Running the Application

1. Navigate to the project root:

```bash
cd automated-job-application
```

2. Run the FastAPI application:

```bash
cd backend
uvicorn main:app --reload
```

3. Access the application at:
   
   http://127.0.0.1:8000/

## Usage

1. Fill out the job application form with:
   - Full name
   - Email address
   - Job title
   - Upload CV (PDF)
   - Optional certificate (PDF or ZIP)

2. Submit the form to generate a tailored cover letter

3. View the generated cover letter and download the PDF version

## Rate Limiting

- Each email address is limited to 4 applications per day
- Each email address is limited to 30 applications per week

## Future Enhancements

- React/Vue frontend for a more interactive UI
- User authentication and job application history
- Integration with job listing APIs
- Enhanced CV parsing and data extraction
- Email notifications for application status