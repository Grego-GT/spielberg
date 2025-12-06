"""Intent analyzer module for understanding user requirements and generating technical specifications.

This module uses OpenAI GPT-4 to analyze natural language prompts and extract structured
requirements for Actor generation.
"""

import os
import json
from typing import Dict, Any, List
from openai import AsyncOpenAI
from apify import Actor


class IntentAnalyzer:
    """Analyzes user prompts and generates structured Actor requirements."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the intent analyzer with OpenAI client.
        
        Args:
            openai_api_key: OpenAI API key for GPT-4 access
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = "gpt-4-turbo-preview"
    
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            requirements_text = response.choices[0].message.content
            requirements = json.loads(requirements_text)
            
            Actor.log.info(f"Generated requirements for Actor: {requirements.get('actor_name', 'unknown')}")
            Actor.log.info(f"Actor type: {requirements.get('actor_type', 'unknown')}")
            
            return requirements
            
        except Exception as e:
            Actor.log.error(f"Failed to analyze intent: {str(e)}")
            raise Exception(f"OpenAI API error during intent analysis: {str(e)}")
    
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
- Choose appropriate input field types and editors
- Suggest realistic dependencies (prefer built-in libraries when possible)
- For scrapers, include URL input fields
- For processors, include data input fields
- Be specific about expected output format
- Consider error handling and edge cases in technical notes

IMPORTANT: Respond ONLY with valid JSON matching the structure above. No other text."""


async def analyze_intent(user_prompt: str) -> Dict[str, Any]:
    """Main function to analyze user intent and generate requirements.
    
    Args:
        user_prompt: Natural language description from user
        
    Returns:
        Structured requirements dictionary
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set
        Exception: If analysis fails
    """
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    analyzer = IntentAnalyzer(openai_api_key)
    return await analyzer.analyze(user_prompt)

