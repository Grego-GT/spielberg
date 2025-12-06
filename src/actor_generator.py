"""Actor code generator module for creating complete Actor source code.

This module uses OpenAI GPT-4 to generate all necessary Actor files based on requirements.
"""

import os
import json
from typing import Dict, Any
from openai import AsyncOpenAI
from apify import Actor


class ActorGenerator:
    """Generates complete Actor source code from requirements."""
    
    def __init__(self, openai_api_key: str):
        """Initialize the actor generator with OpenAI client.
        
        Args:
            openai_api_key: OpenAI API key for GPT-4 access
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = "gpt-4-turbo-preview"
    
    async def generate(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Generate complete Actor source code from requirements.
        
        Args:
            requirements: Structured requirements from intent analyzer
            
        Returns:
            Dictionary mapping file paths to file contents
            
        Raises:
            Exception: If code generation fails
        """
        Actor.log.info(f"Generating code for Actor: {requirements.get('actor_name')}")
        
        # Generate all files
        files = {}
        
        # Generate main.py
        files['src/main.py'] = await self._generate_main_py(requirements)
        
        # Generate actor.json
        files['.actor/actor.json'] = self._generate_actor_json(requirements)
        
        # Generate input_schema.json
        files['.actor/input_schema.json'] = self._generate_input_schema(requirements)
        
        # Generate requirements.txt
        files['requirements.txt'] = self._generate_requirements_txt(requirements)
        
        # Generate Dockerfile
        files['Dockerfile'] = self._generate_dockerfile()
        
        # Generate __init__.py
        files['src/__init__.py'] = '"""Actor package."""\n'
        
        # Generate __main__.py
        files['src/__main__.py'] = '''"""Entry point for the Actor."""

import asyncio
from .main import main

if __name__ == '__main__':
    asyncio.run(main())
'''
        
        # Generate README.md
        files['README.md'] = self._generate_readme(requirements)
        
        Actor.log.info(f"Generated {len(files)} files for Actor")
        
        return files
    
    async def _generate_main_py(self, requirements: Dict[str, Any]) -> str:
        """Generate main.py using OpenAI.
        
        Args:
            requirements: Actor requirements
            
        Returns:
            Python code as string
        """
        Actor.log.info("Generating main.py with OpenAI...")
        
        system_prompt = self._get_main_py_system_prompt()
        user_prompt = f"""Generate a complete main.py for an Apify Actor with these requirements:

Actor Name: {requirements.get('actor_name')}
Description: {requirements.get('description')}
Actor Type: {requirements.get('actor_type')}

Input Fields:
{json.dumps(requirements.get('input_fields', []), indent=2)}

Expected Output:
{json.dumps(requirements.get('output_structure', {}), indent=2)}

Technical Notes:
{requirements.get('technical_notes', 'None')}

Dependencies Available:
{', '.join(requirements.get('dependencies', ['apify']))}

Generate complete, production-ready Python code following Apify best practices."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            code = response.choices[0].message.content
            
            # Extract code from markdown if present
            if '```python' in code:
                code = code.split('```python')[1].split('```')[0].strip()
            elif '```' in code:
                code = code.split('```')[1].split('```')[0].strip()
            
            Actor.log.info("Successfully generated main.py")
            return code
            
        except Exception as e:
            Actor.log.error(f"Failed to generate main.py: {str(e)}")
            raise Exception(f"OpenAI API error during code generation: {str(e)}")
    
    def _get_main_py_system_prompt(self) -> str:
        """Get system prompt for main.py generation."""
        return """You are an expert Python developer specializing in Apify Actors.

Generate a complete, production-ready main.py file that:
1. Uses the Apify SDK properly with async/await patterns
2. Follows the structure: async def main() -> None with async with Actor
3. Validates input using Actor.get_input()
4. Implements proper error handling with try/except blocks
5. Uses Actor.log for logging at key points
6. Saves output data using Actor.push_data()
7. Includes comprehensive docstrings
8. Follows PEP 8 style guidelines
9. Handles edge cases gracefully
10. Exits properly with await Actor.exit()

Best Practices:
- Import required packages at the top
- Validate all inputs before processing
- Log progress at major steps
- Use descriptive variable names
- Add helpful comments for complex logic
- Handle errors gracefully with informative messages
- Always use async with Actor context manager
- Save data incrementally when possible

Generate ONLY the Python code, no explanations. Start with imports and end with the main() function."""
    
    def _generate_actor_json(self, requirements: Dict[str, Any]) -> str:
        """Generate actor.json configuration.
        
        Args:
            requirements: Actor requirements
            
        Returns:
            JSON string
        """
        actor_config = {
            "actorSpecification": 1,
            "name": requirements.get('actor_name', 'generated-actor'),
            "title": requirements.get('actor_title', 'Generated Actor'),
            "description": requirements.get('description', 'Actor generated by Spielberg'),
            "version": "0.1",
            "buildTag": "latest",
            "meta": {
                "templateId": "python-empty",
                "generatedBy": "spielberg-v1.0"
            },
            "dockerfile": "./Dockerfile"
        }
        
        return json.dumps(actor_config, indent=2)
    
    def _generate_input_schema(self, requirements: Dict[str, Any]) -> str:
        """Generate input_schema.json.
        
        Args:
            requirements: Actor requirements
            
        Returns:
            JSON string
        """
        properties = {}
        required_fields = []
        
        for field in requirements.get('input_fields', []):
            field_name = field.get('name')
            properties[field_name] = {
                "title": field.get('title', field_name.replace('_', ' ').title()),
                "type": field.get('type', 'string'),
                "description": field.get('description', ''),
            }
            
            if field.get('editor'):
                properties[field_name]['editor'] = field.get('editor')
            
            if 'default' in field:
                properties[field_name]['default'] = field.get('default')
            
            if field.get('required', False):
                required_fields.append(field_name)
        
        schema = {
            "title": f"{requirements.get('actor_title', 'Actor')} Input",
            "type": "object",
            "schemaVersion": 1,
            "properties": properties,
            "required": required_fields
        }
        
        return json.dumps(schema, indent=2)
    
    def _generate_requirements_txt(self, requirements: Dict[str, Any]) -> str:
        """Generate requirements.txt.
        
        Args:
            requirements: Actor requirements
            
        Returns:
            Requirements file content
        """
        deps = requirements.get('dependencies', [])
        
        # Always include apify
        if 'apify' not in deps:
            deps = ['apify'] + deps
        
        # Add version constraints for safety
        versioned_deps = []
        for dep in deps:
            if '>=' not in dep and '==' not in dep and '<' not in dep:
                # Add minimum version constraint
                if dep == 'apify':
                    versioned_deps.append('apify>=1.7.0')
                else:
                    versioned_deps.append(dep)
            else:
                versioned_deps.append(dep)
        
        return '\n'.join(versioned_deps) + '\n'
    
    def _generate_dockerfile(self) -> str:
        """Generate standard Dockerfile."""
        return '''# Use Apify's official Python 3.13 base image
FROM apify/actor-python:3.13

USER myuser

# Copy requirements first for better caching
COPY --chown=myuser:myuser requirements.txt ./

# Install dependencies
RUN echo "Python version:" \\
 && python --version \\
 && echo "Pip version:" \\
 && pip --version \\
 && echo "Installing dependencies:" \\
 && pip install -r requirements.txt \\
 && echo "All installed Python packages:" \\
 && pip freeze

# Copy source code
COPY --chown=myuser:myuser . ./

# Compile Python code
RUN python3 -m compileall -q src/

# Run the Actor
CMD ["python3", "-m", "src"]
'''
    
    def _generate_readme(self, requirements: Dict[str, Any]) -> str:
        """Generate README.md.
        
        Args:
            requirements: Actor requirements
            
        Returns:
            Markdown string
        """
        actor_name = requirements.get('actor_title', 'Generated Actor')
        description = requirements.get('description', 'Actor generated by Spielberg')
        
        readme = f"""# {actor_name}

{description}

## Description

This Actor was automatically generated by Spielberg, an AI-powered Actor generator.

**Actor Type:** {requirements.get('actor_type', 'general')}

## Input

This Actor accepts the following input parameters:

"""
        
        for field in requirements.get('input_fields', []):
            field_name = field.get('name')
            field_type = field.get('type', 'string')
            field_desc = field.get('description', 'No description')
            required = "**Required**" if field.get('required') else "Optional"
            
            readme += f"- **{field_name}** ({field_type}, {required}): {field_desc}\n"
        
        readme += f"""

## Output

The Actor saves results to the default dataset. Expected output structure:

"""
        
        output = requirements.get('output_structure', {})
        if output:
            readme += "```json\n"
            readme += json.dumps(output, indent=2)
            readme += "\n```\n"
        else:
            readme += "See Actor runs for output format.\n"
        
        readme += """

## Usage

Run the Actor from the Apify Console or via API:

```bash
apify call {actor_name} --input '{"field": "value"}'
```

## Technical Notes

"""
        
        tech_notes = requirements.get('technical_notes', 'None provided')
        readme += f"{tech_notes}\n"
        
        readme += """

---

*Generated by Spielberg v1.0*
"""
        
        return readme


async def generate_actor_code(requirements: Dict[str, Any]) -> Dict[str, str]:
    """Main function to generate Actor code from requirements.
    
    Args:
        requirements: Structured requirements dictionary
        
    Returns:
        Dictionary mapping file paths to file contents
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set
        Exception: If generation fails
    """
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    generator = ActorGenerator(openai_api_key)
    return await generator.generate(requirements)

