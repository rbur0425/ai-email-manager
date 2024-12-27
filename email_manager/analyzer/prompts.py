from ..models import EmailContent

def get_analysis_prompt(email: EmailContent) -> str:
    return f"""Analyze this email and determine its category. The email details are:

Subject: {email.subject}
From: {email.sender}
Content: {email.content}

Categorize this email into one of these categories:
1. non_essential: Advertisements, promotions, general newsletters
2. save_and_summarize: Important content that should be saved and summarized based on user preferences. This includes Technical or AI-related content, including tech newsletters, marketing newsletters, GitHub notifications, API updates
3. important: Other important emails that need attention like bills, receipts, registrations, reminders, appointments, etc.

IMPORTANT: Respond with ONLY a single JSON object and NO additional text. The JSON must have exactly this structure:
{{
    "category": "non_essential|save_and_summarize|important",
    "confidence": 0.0-1.0,
    "reasoning": "1-2 sentences explaining the categorization"
}}

Here are two example responses (DO NOT include these in your response, just follow the format):

Example 1:
{{
    "category": "save_and_summarize",
    "confidence": 0.95,
    "reasoning": "This is a detailed update about an important project that should be saved for future reference."
}}

Example 2:
{{
    "category": "important",
    "confidence": 0.97,
    "reasoning": "This is an email about your bill from the energy company National Grid."
}}"""

def get_summary_prompt(email: EmailContent) -> str:
    return f"""Generate a concise 1-9 bullet point summary of this important email:

Subject: {email.subject}
From: {email.sender}
Content: {email.content}

Focus on:
- Key points and main message
- Important updates or changes
- Interesting or imporatant news
- Action items or deadlines
- Relevant links or resources
- Critical details to remember

IMPORTANT: Respond with ONLY a single JSON object and NO additional text. The JSON must have exactly this structure:
{{
    "summary_points": [
        "Point 1 about key updates",
        "Point 2 about important changes",
        "Point 3 about action items",
        "Point 4 about deadlines",
        "Point 5 about resources"
    ]
}}

Example (DO NOT include this in your response, just follow the format):
{{
    "summary_points": [
        "Project deadline extended to March 15th",
        "New requirements added for user authentication",
        "Team meeting scheduled for next Tuesday at 2 PM"
    ]
}}"""