import json
from typing import Optional

import anthropic
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

from ..config import config
from ..logger import get_logger
from .models import (
    EmailAnalysis,
    EmailCategory,
    EmailContent,
    ClaudeAPIError,
    InsufficientCreditsError,
)
from .prompts import get_analysis_prompt, get_summary_prompt

logger = get_logger(__name__)

class EmailAnalyzer:
    def __init__(self):
        self.client = Anthropic(api_key=config.claude.api_key)
        self.model = config.claude.model
        self._credits_exhausted = False

    def analyze_email(self, email: EmailContent) -> EmailAnalysis:
        """Analyze email content using Claude to determine category and generate summary if needed."""
        try:
            # If credits are already known to be exhausted, fail fast
            if self._credits_exhausted:
                raise InsufficientCreditsError("Claude API credits are exhausted")

            # Get initial analysis
            analysis_prompt = get_analysis_prompt(email)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Debug log the raw response
            logger.debug(f"Raw Claude response: {response}")
            logger.debug(f"Response content type: {type(response.content)}")
            logger.debug(f"Response content: {response.content}")
            
            # Get the first message content
            response_text = response.content[0].text if isinstance(response.content, list) else response.content
            
            # Parse analysis response
            analysis = self._parse_analysis_response(response_text)
            
            # If tech/AI related, generate summary
            if analysis.category == EmailCategory.TECH_AI:
                summary_prompt = get_summary_prompt(email)
                summary_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                
                try:
                    summary_text = summary_response.content[0].text if isinstance(summary_response.content, list) else summary_response.content
                    logger.debug(f"Summary response type: {type(summary_text)}")
                    logger.debug(f"Summary text: {summary_text}")
                    
                    # Handle TextBlock objects
                    if hasattr(summary_text, 'text'):
                        summary_text = summary_text.text
                        
                    try:
                        summary_data = json.loads(summary_text)
                        analysis.summary = "\n".join(summary_data.get("summary_points", []))
                    except json.JSONDecodeError:
                        # If not JSON, use the text directly but format it nicely
                        if isinstance(summary_text, str):
                            # Try to extract bullet points if present
                            points = [line.strip() for line in summary_text.split('\n') if line.strip().startswith('-')]
                            if points:
                                analysis.summary = "\n".join(points)
                            else:
                                analysis.summary = summary_text
                        else:
                            analysis.summary = str(summary_text)
                            
                except Exception as e:
                    logger.error(f"Error processing summary: {e}")
                    if hasattr(summary_response.content, 'text'):
                        analysis.summary = summary_response.content.text
                    else:
                        analysis.summary = str(summary_response.content)

            return analysis
            
        except APIError as e:
            error_message = str(e)
            
            # Check for insufficient credits error
            if 'credit balance is too low' in error_message.lower():
                self._credits_exhausted = True
                logger.error("Claude API credits exhausted. Please recharge your account.")
                raise InsufficientCreditsError("Claude API credits are exhausted") from e
            
            # Handle other API errors
            logger.error(f"Claude API error: {error_message}")
            return self._create_fallback_analysis(f"API Error: {error_message}")
            
        except APIConnectionError as e:
            logger.error(f"Connection error with Claude API: {str(e)}")
            return self._create_fallback_analysis("Connection error with Claude API")
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {str(e)}")
            return self._create_fallback_analysis("Rate limit exceeded, please try again later")
            
        except Exception as e:
            logger.error(f"Error analyzing email: {str(e)}")
            return self._create_fallback_analysis(f"Error during analysis: {str(e)}")

    def _create_fallback_analysis(self, reason: str) -> EmailAnalysis:
        """Create a fallback analysis when errors occur."""
        return EmailAnalysis(
            category=EmailCategory.IMPORTANT,  # Default to important to avoid missing critical emails
            confidence=0.0,
            reasoning=reason
        )

    def _parse_analysis_response(self, response: str) -> EmailAnalysis:
        """Parse Claude's JSON response into EmailAnalysis object."""
        try:
            logger.debug(f"Parsing response: {response}")
            
            # Parse JSON response
            data = json.loads(response)
            
            # Validate required fields
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")
                
            if "category" not in data or "confidence" not in data or "reasoning" not in data:
                raise ValueError("Missing required fields in JSON response")
                
            # Convert category string to enum
            try:
                category = EmailCategory(data["category"].lower())
            except ValueError:
                logger.error(f"Invalid category value: {data['category']}")
                category = EmailCategory.IMPORTANT
                
            # Validate confidence is float between 0 and 1
            try:
                confidence = float(data["confidence"])
                confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            except (ValueError, TypeError):
                logger.error("Invalid confidence value")
                confidence = 0.0
                
            # Get reasoning
            reasoning = str(data.get("reasoning", "No reasoning provided"))

            return EmailAnalysis(
                category=category,
                confidence=confidence,
                reasoning=reasoning
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            return self._create_fallback_analysis("Failed to parse response as JSON")
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return self._create_fallback_analysis(f"Error parsing analysis: {str(e)}")