# AI-Powered CV Ranking System Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [Environment Configuration](#environment-configuration)
5. [API Documentation](#api-documentation)
6. [AI Explanation System](#ai-explanation-system)
7. [Audit Logging](#audit-logging)
8. [EU AI Act Compliance](#eu-ai-act-compliance)
9. [Human Oversight](#human-oversight)
10. [Bias Detection](#bias-detection)

## Project Overview

The AI-Powered CV Ranking System is a Django-based backend application designed to automatically rank candidates against job requirements using AI embeddings and similarity analysis. This system is built with high-risk AI system principles in mind, providing:

- **Transparency**: Detailed explanations for every ranking decision
- **Human Oversight**: Mandatory human review and override capabilities
- **Audit Trail**: Comprehensive logging of all system actions
- **Bias Detection**: Built-in bias monitoring and reporting
- **Compliance**: EU AI Act compliance features

## Architecture

### System Components

```
ai_cv_system/
├── manage.py                 # Django management script
├── .env                     # Environment variables
├── config/                  # Django configuration
│   ├── settings.py
│   └── urls.py
├── apps/                    # Django applications
│   ├── users/              # User management & authentication
│   ├── candidates/         # CV upload & candidate management
│   ├── jobs/              # Job posting management
│   ├── ranking/           # AI ranking system
│   ├── ai/                # AI configuration & metrics
│   └── audit/             # Audit logging & compliance
├── services/              # Business logic layer
│   ├── parser_service.py    # CV text extraction
│   ├── embedding_service.py # OpenAI embeddings
│   ├── ranking_service.py   # Candidate ranking
│   ├── explain_service.py   # AI explanations
│   └── bias_service.py      # Bias detection
└── docs/                  # Documentation
```

### Service Layer Architecture

The system follows a service-oriented architecture where:
- **Views** handle HTTP requests/responses
- **Services** contain business logic
- **Models** manage data persistence
- **Serializers** handle data validation and serialization

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation Steps

1. **Clone or extract the project:**
   ```bash
   cd ai_cv_system
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env  # Create from template
   # Edit .env file with your configurations
   ```

5. **Run database migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://127.0.0.1:8000/`

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Django Configuration (Optional)
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database (Optional - defaults to SQLite)
DATABASE_URL=sqlite:///db.sqlite3
```

### OpenAI API Key

To get full AI functionality, you need an OpenAI API key:

1. Visit [OpenAI API Platform](https://platform.openai.com/api-keys)
2. Create an account and generate an API key
3. Add it to your `.env` file as `OPENAI_API_KEY`

**Note**: If no OpenAI API key is provided, the system will use dummy embeddings for demonstration purposes.

## API Documentation

### Authentication

All API endpoints require authentication using token-based authentication.

#### Register User
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "recruiter1",
  "email": "recruiter@company.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "first_name": "John",
  "last_name": "Doe",
  "role": "recruiter",
  "company": "Tech Corp"
}
```

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "recruiter1",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "recruiter1",
    "email": "recruiter@company.com",
    "role": "recruiter",
    "company": "Tech Corp"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

### Candidate Management

#### Upload CV
```http
POST /api/candidates/upload/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: multipart/form-data

name: John Smith
email: john.smith@email.com
phone: +1234567890
cv_file: [PDF or DOCX file]
```

#### List Candidates
```http
GET /api/candidates/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# Optional query parameters:
# ?search=python          # Search in name, email, skills
# ?min_experience=3        # Filter by minimum experience
# ?skills=python,django    # Filter by skills
```

### Job Management

#### Create Job
```http
POST /api/jobs/create/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "title": "Senior Python Developer",
  "company": "Tech Corp",
  "location": "San Francisco, CA",
  "description": "We are looking for an experienced Python developer...",
  "requirements": "5+ years Python experience, Django, REST APIs...",
  "job_type": "full_time",
  "level": "senior",
  "required_skills": ["Python", "Django", "REST API", "PostgreSQL"],
  "preferred_skills": ["Docker", "AWS", "React"],
  "min_experience": 5,
  "max_experience": 10,
  "salary_min": 120000,
  "salary_max": 180000,
  "currency": "USD"
}
```

#### List Jobs
```http
GET /api/jobs/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# Optional filters:
# ?search=python           # Search in title, company, description
# ?job_type=full_time     # Filter by job type
# ?level=senior           # Filter by level
# ?location=San Francisco  # Filter by location
```

### AI Ranking System

#### Run Ranking
```http
POST /api/ranking/run/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "job_id": 1,
  "candidate_ids": [1, 2, 3, 4, 5],  # Optional - if not provided, ranks all active candidates
  "notes": "Initial screening for senior developer position"
}
```

**Response:**
```json
{
  "message": "Ranking completed successfully",
  "session": {
    "id": 1,
    "job": 1,
    "job_title": "Senior Python Developer",
    "created_by_username": "recruiter1",
    "created_at": "2024-03-15T10:30:00Z",
    "candidates_count": 5
  },
  "rankings_count": 5,
  "top_candidates": [
    {
      "id": 1,
      "candidate": {
        "id": 3,
        "name": "Alice Johnson",
        "email": "alice@email.com",
        "skills": ["Python", "Django", "REST API", "PostgreSQL", "Docker"]
      },
      "ai_score": 92.5,
      "ai_rank": 1,
      "matched_skills": ["Python", "Django", "REST API", "PostgreSQL"],
      "missing_skills": [],
      "explanation": "Excellent match - candidate profile strongly aligns with job requirements. Matched skills: Python, Django, REST API, PostgreSQL. Additional preferred skills found: Docker. Candidate meets experience requirement (6 vs 5 years required).",
      "bias_flags": [],
      "human_decision": "pending",
      "is_reviewed": false
    }
  ]
}
```

#### Get Job Rankings
```http
GET /api/ranking/1/  # Get rankings for job ID 1
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

#### Human Override
```http
POST /api/ranking/1/override/  # Override ranking ID 1
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "human_decision": "accepted",
  "human_score": 95.0,
  "human_feedback": "Strong technical skills and cultural fit based on interview"
}
```

### Audit Logs

#### Get Audit Logs
```http
GET /api/audit/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# Optional filters:
# ?action_type=ranking     # Filter by action type
# ?risk_level=high        # Filter by risk level
# ?days=7                 # Show logs from last 7 days
# ?search=candidate       # Search in descriptions
```

## AI Explanation System

The system provides detailed explanations for every ranking decision, ensuring transparency and enabling human oversight.

### Explanation Components

1. **Matched Skills**: Skills found in both CV and job requirements
2. **Missing Skills**: Required skills not found in candidate's CV
3. **Experience Analysis**: Comparison of candidate's experience vs. job requirements
4. **Education Assessment**: Educational background evaluation
5. **Overall Score Explanation**: Human-readable interpretation of the numeric score

### Score Categories

- **90-100**: Excellent match - strong alignment with job requirements
- **80-89**: Very good match - meets most qualifications
- **70-79**: Good match - meets key requirements with minor gaps
- **60-69**: Moderate match - relevant experience but some gaps
- **40-59**: Partial match - some relevant skills but significant gaps
- **0-39**: Low match - poor alignment with job requirements

### Example Explanation

```json
{
  "matched_skills": ["Python", "Django", "REST API", "PostgreSQL"],
  "missing_skills": ["AWS", "Docker"],
  "explanation": "Very good match - candidate has most required qualifications. Matched skills: Python, Django, REST API, PostgreSQL. Missing required skills: AWS, Docker. Additional preferred skills found: React. Candidate meets experience requirement (6 vs 5 years required). Candidate has master's level education.",
  "bias_flags": [],
  "score_category": "very_good",
  "skills_match_ratio": 0.67,
  "experience_match": true
}
```

## Audit Logging

### Comprehensive Logging

The system logs ALL actions for compliance and monitoring:

- **User Actions**: Login, logout, profile updates
- **CV Operations**: Upload, parsing, embedding generation
- **Job Management**: Creation, updates, deletions
- **AI Operations**: Ranking runs, explanation generation
- **Human Decisions**: Overrides, reviews, feedback
- **System Events**: Errors, security incidents

### Log Entry Structure

```json
{
  "id": 123,
  "user": "recruiter1",
  "action_type": "ranking",
  "action_description": "AI ranking performed for job 'Senior Python Developer' with 5 candidates",
  "risk_level": "high",
  "timestamp": "2024-03-15T10:30:00Z",
  "success": true,
  "ai_confidence": 85.0,
  "ai_explanation": "AI-generated candidate ranking based on CV-job matching",
  "metadata": {
    "job_id": 1,
    "candidates_count": 5,
    "session_id": 1
  }
}
```

### Risk Levels

- **Low**: Routine operations (profile updates, data reads)
- **Medium**: Data modifications, uploads
- **High**: AI decisions, ranking operations
- **Critical**: Security incidents, system failures

## EU AI Act Compliance

This system implements key requirements for high-risk AI systems under the EU AI Act:

### Mandatory Requirements Implemented

1. **Human Oversight** (Article 14)
   - Human review required for all ranking decisions
   - Override capabilities for human operators
   - Clear escalation procedures

2. **Transparency** (Article 13)
   - Detailed explanations for all AI decisions
   - Clear indication when AI is being used
   - User understanding of system capabilities and limitations

3. **Accuracy and Robustness** (Article 15)
   - Fallback mechanisms (dummy embeddings when OpenAI unavailable)
   - Error handling and graceful degradation
   - Performance monitoring and analytics

4. **Data Governance** (Article 10)
   - Comprehensive audit logging
   - Data quality checks (CV parsing validation)
   - Bias monitoring and detection

5. **Record Keeping** (Article 12)
   - Automatic logging of all system interactions
   - Audit trail preservation
   - Compliance reporting capabilities

### Risk Management

The system implements several risk mitigation measures:

- **Bias Detection**: Automated detection of potential bias indicators
- **Human Oversight**: Mandatory human review for high-stakes decisions
- **Transparency**: Complete explanations for all AI decisions
- **Monitoring**: Continuous performance and bias monitoring
- **Fallback**: System continues to function without AI components

## Human Oversight

### Mandatory Human Review

All AI ranking decisions require human oversight:

1. **Initial Review**: Human recruiter reviews AI rankings
2. **Override Capability**: Humans can override AI decisions
3. **Feedback Collection**: System captures human feedback
4. **Learning Loop**: Human decisions inform system improvements

### Override Process

```python
# Example override workflow
1. AI generates rankings with explanations
2. Human reviewer examines top candidates
3. Human makes accept/reject/shortlist decisions
4. System logs all human decisions with reasoning
5. Human feedback is stored for analysis
```

### Decision Categories

- **Accepted**: Candidate progresses to next stage
- **Rejected**: Candidate is not suitable
- **Shortlisted**: Candidate needs further evaluation
- **Pending**: Awaiting human review

## Bias Detection

### Automated Bias Monitoring

The system continuously monitors for potential bias:

### Protected Characteristics Monitored

1. **Gender**: Detection of gender-related terms in CVs
2. **Age**: Identification of age indicators
3. **Ethnicity**: Non-ASCII name detection, ethnic keywords
4. **Religion**: Religious affiliation mentions
5. **Family Status**: Marital status, family references
6. **Education**: Elite institution bias detection
7. **Socioeconomic**: Expensive area indicators

### Bias Flags

When potential bias indicators are detected, the system:

1. **Flags the ranking** with specific bias types
2. **Logs the detection** for audit purposes
3. **Alerts human reviewers** to potential issues
4. **Tracks patterns** across multiple rankings

### Bias Reporting

Regular bias reports include:

- Flag frequency and types
- Score differences between flagged/unflagged candidates
- Human override patterns
- Recommendations for system improvements

## Best Practices

### For Administrators

1. **Regular Monitoring**: Check audit logs and bias reports weekly
2. **Human Training**: Ensure all human reviewers understand bias risks
3. **System Updates**: Keep bias detection patterns current
4. **Compliance Reviews**: Conduct regular EU AI Act compliance audits

### For Recruiters

1. **Review All Rankings**: Don't rely solely on AI scores
2. **Document Decisions**: Provide detailed feedback for overrides
3. **Watch for Bias**: Be alert to potential bias indicators
4. **Continuous Learning**: Stay updated on fair hiring practices

### For Developers

1. **Service Layer**: Always use service classes for business logic
2. **Logging**: Log all significant actions with appropriate risk levels
3. **Error Handling**: Implement graceful fallbacks for AI failures
4. **Testing**: Include bias detection in testing procedures

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   - Check API key validity
   - Verify rate limits not exceeded
   - System falls back to dummy embeddings

2. **CV Parsing Failures**
   - Ensure file format is supported (PDF/DOCX)
   - Check file size limits (10MB)
   - Verify file is not corrupted

3. **Poor Ranking Quality**
   - Review job description quality
   - Check skill keywords accuracy
   - Verify candidate CV completeness

### Support

For technical support:
1. Check audit logs for error details
2. Review Django logs in the application directory
3. Verify environment configuration
4. Contact system administrator with specific error messages

---

*This documentation is part of an AI system designed for high-risk applications requiring transparency, human oversight, and regulatory compliance.*