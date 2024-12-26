from ..models import EmailContent

def get_analysis_prompt(email: EmailContent) -> str:
    return f"""Analyze this email and determine its category. The email details are:

Subject: {email.subject}
From: {email.sender}
Content: {email.content}

Categorize this email into one of these categories:
1. non_essential: Advertisements, promotions, newsletters without significant tech content
2. tech_ai: Technical or AI-related content, including tech newsletters, GitHub notifications, API updates
3. important: Other important emails that need attention like bills, receipts, registrations, reminders, etc.

IMPORTANT: Respond with ONLY a single JSON object and NO additional text. The JSON must have exactly this structure:
{{
    "category": "non_essential|tech_ai|important",
    "confidence": 0.0-1.0,
    "reasoning": "1-2 sentences explaining the categorization"
}}

Here are two example responses (DO NOT include these in your response, just follow the format):

Example 1:
{{
    "category": "tech_ai",
    "confidence": 0.95,
    "reasoning": "This is a GitHub notification about code changes in a repository, containing technical details about commits and pull requests."
}}

Example 2:
{{
    "category": "important",
    "confidence": 0.97,
    "reasoning": "This is an email about your bill from the energy company National Grid."
}}"""

def get_summary_prompt(email: EmailContent) -> str:
    return f"""Generate a concise 1-9 bullet point summary of this technical/AI-related email:

Subject: {email.subject}
From: {email.sender}
Content: {email.content}

Focus on:
- Key technical concepts or announcements
- Important updates or changes
- Action items or deadlines
- Links to documentation or resources

IMPORTANT: Respond with ONLY a single JSON object and NO additional text. The JSON must have exactly this structure:
{{
    "summary_points": [
        "Point 1 about key updates",
        "Point 2 about technical changes",
        "Point 3 about action items",
        "Point 4 about deadlines",
        "Point 5 about links",
        "Point 6 about resources"
    ]
}}

Example (DO NOT include this in your response, just follow the format):
{{
    "summary_points": [
        "New API version 2.3 released with improved error handling",
        "Breaking change: Authentication endpoint changed to /v2/auth",
        "Documentation updated at docs.example.com/v2"
    ]
}}"""