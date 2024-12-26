import os
import sys
from pathlib import Path

# Add the project root to Python path to allow imports
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from email_manager.gmail.service import GmailService
from email_manager.analyzer.analyzer import EmailAnalyzer
from email_manager.analyzer.models import EmailContent, InsufficientCreditsError

def main():
    print("Testing Email Analysis System...")
    
    try:
        # Initialize services
        gmail_service = GmailService()
        email_analyzer = EmailAnalyzer()
        
        print("\nFetching recent unread emails...")
        # Get 3 unread emails for testing
        messages = gmail_service.get_unread_emails(max_results=3)
        
        if not messages:
            print("No unread emails found.")
            return
            
        print(f"\nAnalyzing {len(messages)} emails...")
        for msg in messages:
            try:
                # Convert Gmail message to our EmailContent format
                email_content = EmailContent(
                    email_id=msg['id'],
                    subject=msg.get('subject', 'No Subject'),
                    sender=msg.get('from', 'Unknown Sender'),
                    content=msg.get('snippet', ''),  # Using snippet for brevity
                    date=msg.get('date', '')
                )
                
                # Analyze the email
                print(f"\nAnalyzing email: {email_content.subject}")
                print(f"From: {email_content.sender}")
                print(f"Content: {email_content.content[:200]}...")
                print()
                
                analysis = email_analyzer.analyze_email(email_content)
                
                # Print results
                print("Analysis Results:")
                print(f"Category: {analysis.category.value}")
                print(f"Confidence: {analysis.confidence:.2f}")
                print(f"Reasoning: {analysis.reasoning}")
                
                if analysis.summary:
                    print("\nTechnical Summary:")
                    print(analysis.summary)
                
            except InsufficientCreditsError:
                print("\nERROR: Claude API credits exhausted. Please recharge your account.")
                print("Stopping email analysis.")
                return
                
            except Exception as e:
                print(f"\nError processing email: {str(e)}")
                continue
                
            finally:
                print("-" * 80)
                
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()