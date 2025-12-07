"""Intent analyzer module for understanding user requirements and generating technical specifications.

This module uses Anthropic Claude to analyze natural language prompts and extract structured
requirements for Actor generation.
"""

import os
import json
from typing import Dict, Any, List
from anthropic import AsyncAnthropic
from apify import Actor


class IntentAnalyzer:
    """Analyzes user prompts and generates structured Actor requirements."""

    def __init__(self, anthropic_api_key: str):
        """Initialize the intent analyzer with Anthropic client.

        Args:
            anthropic_api_key: Anthropic API key for Claude access
        """
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
        self.model = "claude-sonnet-4-5-20250929"
    
    async def analyze(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze user prompt and generate structured requirements.
        
        Args:
            user_prompt: Natural language description of desired Actor
            
        Returns:
            Dictionary containing structured Actor requirements
            
        Raises:
            Exception: If OpenAI API call fails
        """
        Actor.log.info(f"Analyzing user prompt: {user_prompt[:100]}...")
        
        system_prompt = self._get_system_prompt()
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            requirements_text = response.content[0].text

            if not requirements_text or len(requirements_text.strip()) == 0:
                raise Exception("Claude returned empty requirements")

            # Strip markdown code blocks if present
            requirements_text = requirements_text.strip()
            if requirements_text.startswith('```'):
                # Find the first newline after the opening ```
                first_newline = requirements_text.find('\n')
                if first_newline != -1:
                    requirements_text = requirements_text[first_newline + 1:]
                # Remove the closing ```
                if requirements_text.endswith('```'):
                    requirements_text = requirements_text[:-3].rstrip()

            requirements = json.loads(requirements_text)

            # Validate required fields
            required_fields = ['actor_name', 'actor_title', 'description', 'actor_type']
            missing_fields = [f for f in required_fields if f not in requirements]
            if missing_fields:
                Actor.log.warning(f"Missing required fields in requirements: {missing_fields}")

            Actor.log.info(f"Generated requirements for Actor: {requirements.get('actor_name', 'unknown')}")
            Actor.log.info(f"Actor type: {requirements.get('actor_type', 'unknown')}")

            return requirements

        except json.JSONDecodeError as e:
            Actor.log.error(f"Failed to parse JSON requirements: {str(e)}")
            Actor.log.error(f"Raw response: {requirements_text[:500] if 'requirements_text' in locals() else 'N/A'}")
            raise Exception(f"Invalid JSON response from Claude: {str(e)}")
        except Exception as e:
            Actor.log.error(f"Failed to analyze intent: {str(e)}")
            Actor.log.error(f"Model: {self.model}")
            raise Exception(f"Anthropic API error during intent analysis: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for intent analysis.
        
        Returns:
            System prompt string for GPT-4
        """
        return """You are an expert Apify Actor architect. Your job is to analyze user requests and generate detailed technical requirements for building Apify Actors.

Analyze the user's natural language description and extract:
1. Actor purpose and functionality
2. Actor type (scraper, data-processor, automation-tool, or other)
3. Required input fields with types and descriptions
4. Expected output structure
5. Required Python packages/dependencies
6. Technical implementation notes

Generate a JSON response with this exact structure:
{
  "actor_name": "lowercase-name-with-hyphens",
  "actor_title": "Human Readable Title",
  "description": "Clear description of what the Actor does",
  "actor_type": "scraper|data-processor|automation-tool|other",
  "dependencies": ["package1", "package2"],
  "input_fields": [
    {
      "name": "fieldName",
      "type": "string|integer|boolean|array|object",
      "title": "Field Title",
      "description": "What this field is for",
      "required": true|false,
      "default": "default_value (optional)",
      "editor": "textfield|textarea|select|json (optional)"
    }
  ],
  "output_structure": {
    "field1": "description of field1",
    "field2": "description of field2"
  },
  "technical_notes": "Implementation guidance, special considerations, recommended approaches"
}

Guidelines:
- Keep actor names short, descriptive, and URL-friendly
- **CRITICAL: Keep description under 250 characters (maximum 300 allowed)**
- Description should be concise, clear, and actionable
- Choose appropriate input field types and editors
- Suggest realistic dependencies (prefer built-in libraries when possible)
- For scrapers, include URL input fields
- For processors, include data input fields
- Be specific about expected output format
- Consider error handling and edge cases in technical notes

DEPENDENCY REQUIREMENTS FOR SCRAPERS:
- **NEVER suggest 'selenium' or 'webdriver' - these are NOT compatible with Apify's Docker images**
- For simple static HTML scraping: use 'beautifulsoup4' and 'httpx' (FASTEST, recommended)
- For multi-page static scraping with crawling: use 'beautifulsoup4' and 'httpx' (simple approach)
- For JavaScript-heavy sites ONLY: use 'crawlee[playwright]' (includes browser automation)
- For API-based scraping: use 'httpx' or 'requests'
- **IMPORTANT**: When suggesting crawlee, always specify the extra: 'crawlee[beautifulsoup]' or 'crawlee[playwright]'
- Example dependencies:
  - Simple scraping: ["beautifulsoup4", "httpx"]
  - JS-heavy scraping: ["crawlee[playwright]"]
- Prefer simple HTTP + BeautifulSoup approach over crawlee when possible

IMPORTANT: Respond ONLY with valid JSON matching the structure above. No other text."""


async def analyze_intent(user_prompt: str) -> Dict[str, Any]:
    """Main function to analyze user intent and generate requirements.

    Args:
        user_prompt: Natural language description from user

    Returns:
        Structured requirements dictionary

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
        Exception: If analysis fails
    """
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    analyzer = IntentAnalyzer(anthropic_api_key)
    return await analyzer.analyze(user_prompt)

