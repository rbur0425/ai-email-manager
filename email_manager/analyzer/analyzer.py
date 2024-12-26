import json
from typing import Optional
import logging

import anthropic
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

from ..config import config
from ..logger import get_logger
from ..models import EmailAnalysis, EmailContent
from ..database.models import EmailCategory
from .models import ClaudeAPIError, InsufficientCreditsError
from .prompts import get_analysis_prompt, get_summary_prompt
from ..database.manager import DatabaseManager  # Import DatabaseManager

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)  # Set logger level to DEBUG

class EmailAnalyzer:
    """Analyzes emails using Claude API to determine category and generate summaries."""

    def __init__(self, claude_client: Optional[Anthropic] = None, db_manager: Optional[DatabaseManager] = None):
        """Initialize the analyzer with optional Claude client and database manager."""
        if claude_client:
            self.client = claude_client
        else:
            self.client = Anthropic(api_key=config.claude.api_key)
            
        self.model = config.claude.model
        self._credits_exhausted = False
        
        if db_manager:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager()

    def analyze_email(self, email: EmailContent) -> EmailAnalysis:
        """Analyze email content using Claude to determine category and generate summary if needed."""
        try:
            # If credits are already known to be exhausted, fail fast
            if self._credits_exhausted:
                logger.error("Credits already exhausted, failing fast")
                raise InsufficientCreditsError("Claude API credits are exhausted")

            # Get initial analysis
            analysis_prompt = get_analysis_prompt(email)
            logger.debug(f"Sending analysis prompt: {analysis_prompt}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Debug log the raw response
            logger.debug(f"Raw Claude response type: {type(response)}")
            logger.debug(f"Raw Claude response: {response}")
            logger.debug(f"Response content type: {type(response.content)}")
            logger.debug(f"Response content: {response.content}")
            
            # Get the first message content
            response_text = response.content[0].text if isinstance(response.content, list) else response.content
            logger.debug(f"Extracted response text: {response_text}")
            
            # Parse analysis response
            analysis = self._parse_analysis_response(response_text)
            if analysis:
                # Record successful analysis
                self.db_manager.add_processing_history(
                    email_id=email.email_id,
                    action="analyzed",
                    category=analysis.category,
                    confidence=analysis.confidence,
                    success=True
                )
                return analysis
            
            # If parsing failed, return default result
            error_result = EmailAnalysis(
                category=EmailCategory.IMPORTANT,
                confidence=0.0,
                reasoning="Failed to parse response as JSON"
            )
            
            # Record failed analysis
            self.db_manager.add_processing_history(
                email_id=email.email_id,
                action="analyzed",
                category=error_result.category,
                confidence=error_result.confidence,
                success=False,
                error_message=error_result.reasoning
            )
            return error_result
            
        except APIError as e:
            error_message = str(e)
            
            # Check for insufficient credits error
            if 'credit balance is too low' in error_message.lower():
                self._credits_exhausted = True
                logger.error("Claude API credits exhausted. Please recharge your account.")
                raise InsufficientCreditsError("Claude API credits are exhausted") from e
            
            # Handle other API errors
            logger.error(f"Claude API error: {error_message}")
            error_result = EmailAnalysis(
                category=EmailCategory.IMPORTANT,
                confidence=0.0,
                reasoning=f"API Error: {error_message}"
            )
            
            try:
                # Try to record the error
                self.db_manager.add_processing_history(
                    email_id=email.email_id,
                    action="analyzed",
                    category=error_result.category,
                    confidence=error_result.confidence,
                    success=False,
                    error_message=error_result.reasoning
                )
            except Exception as db_error:
                logger.error(f"Failed to record analysis error: {db_error}")
                
            return error_result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing email: {error_msg}")
            
            error_result = EmailAnalysis(
                category=EmailCategory.IMPORTANT,
                confidence=0.0,
                reasoning=f"Error during analysis: {error_msg}"
            )
            
            try:
                # Try to record the error
                self.db_manager.add_processing_history(
                    email_id=email.email_id,
                    action="analyzed",
                    category=error_result.category,
                    confidence=error_result.confidence,
                    success=False,
                    error_message=error_msg
                )
            except Exception as db_error:
                logger.error(f"Failed to record analysis error: {db_error}")
                
            return error_result

    def _parse_analysis_response(self, response: str) -> Optional[EmailAnalysis]:
        """Parse Claude's JSON response into EmailAnalysis object."""
        try:
            logger.debug(f"Starting to parse response: {response}")
            
            # Parse JSON response
            data = json.loads(response)
            logger.debug(f"Parsed JSON data: {data}")
            
            # Validate required fields
            if not isinstance(data, dict):
                logger.error("Response is not a JSON object")
                return None
                
            if "category" not in data or "confidence" not in data or "reasoning" not in data:
                logger.error(f"Missing required fields in JSON response. Available fields: {data.keys()}")
                return None
                
            # Convert category string to enum
            try:
                category = EmailCategory[data["category"].upper()]
            except KeyError:
                logger.error(f"Invalid category from Claude: {data['category']}")
                return None
                
            # Extract confidence and reasoning
            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")
            
            return EmailAnalysis(
                category=category,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return None

    def generate_summary(self, email: EmailContent) -> Optional[str]:
        """Generate a summary for a tech/AI email using Claude.
        
        Args:
            email: The email to summarize
            
        Returns:
            A string containing bullet points summarizing the email content,
            or None if summary generation fails
            
        Raises:
            ClaudeAPIError: If there's an error calling the Claude API
            InsufficientCreditsError: If API credits are exhausted
        """
        try:
            # If credits are already known to be exhausted, fail fast
            if self._credits_exhausted:
                logger.error("Credits already exhausted, failing fast")
                raise InsufficientCreditsError("Claude API credits are exhausted")

            # Get summary
            summary_prompt = get_summary_prompt(email)
            logger.debug(f"Sending summary prompt: {summary_prompt}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": summary_prompt}]
            )
            
            # Debug log the raw response
            logger.debug(f"Raw summary response type: {type(response)}")
            logger.debug(f"Raw summary response: {response}")
            
            # Get the first message content
            response_text = response.content[0].text if isinstance(response.content, list) else response.content
            logger.debug(f"Extracted summary text: {response_text}")
            
            # Parse summary response
            try:
                data = json.loads(response_text)
                if not isinstance(data, dict) or "summary_points" not in data:
                    logger.error("Invalid summary response format")
                    return None
                    
                # Join bullet points with newlines
                summary = "\n".join(f"• {point}" for point in data["summary_points"])
                return summary
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse summary JSON response: {str(e)}")
                return None
                
        except APIError as e:
            error_message = str(e)
            
            # Check for insufficient credits error
            if 'credit balance is too low' in error_message.lower():
                self._credits_exhausted = True
                logger.error("Claude API credits exhausted. Please recharge your account.")
                raise InsufficientCreditsError("Claude API credits are exhausted") from e
            
            # Handle other API errors
            logger.error(f"Claude API error generating summary: {error_message}")
            raise ClaudeAPIError(f"Failed to generate summary: {error_message}") from e
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating summary: {error_msg}")
            raise ClaudeAPIError(f"Failed to generate summary: {error_msg}") from e