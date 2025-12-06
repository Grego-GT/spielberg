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
        self.model = "gpt-5-mini-2025-08-07"
    
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
                temperature=1,
                max_completion_tokens=3000
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

OFFICIAL DOCUMENTATION REFERENCES:
- Full Apify Documentation: https://docs.apify.com/llms-full.txt
- Apify MCP Tools: https://mcp.apify.com/?tools=actors,docs,runs,storage
- Apify Python SDK: https://docs.apify.com/sdk/python

Generate a complete, production-ready main.py file following official Apify best practices.

CRITICAL RULES (from official docs):
1. NEVER reject input with errors - Actors should gracefully handle any input (even empty/None)
2. Use 'async with Actor:' context manager (NOT 'async with Actor() as actor:')
3. Use 'await Actor.get_input()' to get input (returns None if no input provided)
4. If no input is needed, simply ignore it - don't raise errors
5. Use 'await Actor.push_data()' to save results to dataset
6. Always use 'Actor.log.info()' for logging (not actor.log.info)
7. The Actor SDK automatically handles initialization and cleanup

REQUIRED STRUCTURE (Apify SDK v3.x pattern):
```python
from apify import Actor

async def main() -> None:
    \"\"\"Main Actor entry point.\"\"\"
    async with Actor:
        # Get input - returns None if not provided (this is NORMAL and OK!)
        actor_input = await Actor.get_input() or {}
        
        # Log start
        Actor.log.info('Actor starting...')
        
        # Your Actor logic here
        result = process_data(actor_input)
        
        # Save results to dataset
        await Actor.push_data(result)
        
        Actor.log.info('Actor finished successfully')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

BEST PRACTICES FROM OFFICIAL APIFY DOCUMENTATION:
- Accept well-defined JSON input and produce structured JSON output
- Validate input with proper error handling but NEVER reject empty/None input
- Use Actor.log methods: .info(), .warning(), .error(), .debug()
- Use Actor.push_data() for dataset items (can be called multiple times)
- Use Actor.set_value() for key-value store items
- Clean and validate data before pushing to dataset
- Handle errors gracefully with try/except and informative messages
- Exit automatically via context manager - no manual Actor.exit() needed
- For scrapers: use CheerioCrawler for static HTML (10x faster than browsers)
- For browser automation: use PlaywrightCrawler for JavaScript-heavy sites

KEY APIFY SDK METHODS:
- Actor.get_input() → dict | None (get input, returns None if empty)
- Actor.push_data(item) → None (save to dataset)
- Actor.set_value(key, value) → None (save to key-value store)
- Actor.log.info/warning/error/debug(message) → None (logging)

COMMON MISTAKES TO AVOID:
- ❌ DON'T: if input_data is not None: raise ValueError("No input expected")
- ❌ DON'T: async with Actor() as actor: (wrong syntax)
- ❌ DON'T: actor.log.info() (use Actor.log.info instead)
- ❌ DON'T: await Actor.exit() (context manager handles this)
- ❌ DON'T: Reject None or empty input
- ✅ DO: actor_input = await Actor.get_input() or {}
- ✅ DO: async with Actor: (correct syntax)
- ✅ DO: Actor.log.info('message') (class method, not instance)
- ✅ DO: Accept and gracefully handle unexpected input fields
- ✅ DO: Use try/except for error handling

REFERENCE EXAMPLE FROM APIFY DOCS:
```python
from apify import Actor

async def main() -> None:
    async with Actor:
        Actor.log.info('Hello from the Actor!')
        actor_input = await Actor.get_input() or {}
        
        # Process data
        data = {'message': 'Hello World', 'input_received': actor_input}
        
        # Save to dataset
        await Actor.push_data(data)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

Generate ONLY the Python code following these patterns. No markdown formatting, no explanations."""
    
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

