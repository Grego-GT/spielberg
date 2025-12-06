"""Validator module for monitoring builds and iteratively fixing errors.

This module monitors Actor builds and uses OpenAI to fix errors when builds fail.
"""

import os
import asyncio
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from apify import Actor
from .deployer import ActorDeployer
from .actor_generator import ActorGenerator


class ActorValidator:
    """Validates Actor builds and fixes errors iteratively."""
    
    def __init__(self, openai_api_key: str, apify_token: Optional[str] = None):
        """Initialize validator with OpenAI and Apify clients.
        
        Args:
            openai_api_key: OpenAI API key
            apify_token: Apify API token
        """
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.deployer = ActorDeployer(apify_token)
        self.generator = ActorGenerator(openai_api_key)
        self.model = "gpt-4-turbo-preview"
    
    async def validate_and_fix(
        self, 
        deployment: Dict[str, Any], 
        requirements: Dict[str, Any],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """Validate Actor build and fix errors if needed.
        
        Args:
            deployment: Initial deployment information
            requirements: Original Actor requirements
            max_iterations: Maximum number of fix attempts
            
        Returns:
            Final validation result with status and details
        """
        actor_id = deployment['actor_id']
        build_id = deployment['build_id']
        
        Actor.log.info(f"Starting validation for Actor {actor_id}")
        
        iteration = 0
        current_build_id = build_id
        
        while iteration < max_iterations:
            Actor.log.info(f"Validation iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Wait for build to complete
                build_status = await self.deployer.wait_for_build(actor_id, current_build_id)
                status = build_status.get('status')
                
                if status == 'SUCCEEDED':
                    Actor.log.info("✓ Build succeeded!")
                    return {
                        'status': 'success',
                        'actor_id': actor_id,
                        'build_id': current_build_id,
                        'console_url': f"https://console.apify.com/actors/{actor_id}",
                        'iterations': iteration + 1,
                        'message': 'Actor built successfully'
                    }
                
                elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                    Actor.log.warning(f"✗ Build {status.lower()}")
                    
                    # Get build logs
                    build_log = await self.deployer.get_build_log(actor_id, current_build_id)
                    Actor.log.info(f"Build log excerpt: {build_log[-500:]}")
                    
                    # If this is the last iteration, return failure
                    if iteration >= max_iterations - 1:
                        return {
                            'status': 'failed',
                            'actor_id': actor_id,
                            'build_id': current_build_id,
                            'console_url': f"https://console.apify.com/actors/{actor_id}",
                            'iterations': iteration + 1,
                            'message': f'Build failed after {max_iterations} attempts',
                            'error': build_log[-1000:] if build_log else 'No logs available'
                        }
                    
                    # Try to fix the error
                    Actor.log.info("Attempting to fix build errors...")
                    fixed_files = await self._fix_build_errors(
                        requirements, 
                        build_log,
                        iteration + 1
                    )
                    
                    # Update Actor with fixed code
                    await self.deployer.update_actor_version(
                        actor_id,
                        '0.1',
                        fixed_files
                    )
                    
                    # Trigger new build
                    new_build = await self.deployer._trigger_build(actor_id)
                    current_build_id = new_build['id']
                    Actor.log.info(f"Triggered new build: {current_build_id}")
                    
                    iteration += 1
                    
                else:
                    # Unknown status, wait a bit more
                    Actor.log.warning(f"Unexpected build status: {status}")
                    await asyncio.sleep(10)
                    
            except TimeoutError as e:
                Actor.log.error(f"Build timeout: {str(e)}")
                return {
                    'status': 'failed',
                    'actor_id': actor_id,
                    'build_id': current_build_id,
                    'console_url': f"https://console.apify.com/actors/{actor_id}",
                    'iterations': iteration + 1,
                    'message': 'Build timed out',
                    'error': str(e)
                }
            
            except Exception as e:
                Actor.log.error(f"Validation error: {str(e)}")
                return {
                    'status': 'failed',
                    'actor_id': actor_id,
                    'build_id': current_build_id,
                    'console_url': f"https://console.apify.com/actors/{actor_id}",
                    'iterations': iteration + 1,
                    'message': 'Validation error',
                    'error': str(e)
                }
        
        # Should not reach here, but just in case
        return {
            'status': 'failed',
            'actor_id': actor_id,
            'build_id': current_build_id,
            'console_url': f"https://console.apify.com/actors/{actor_id}",
            'iterations': max_iterations,
            'message': f'Could not fix errors in {max_iterations} attempts'
        }
    
    async def _fix_build_errors(
        self,
        requirements: Dict[str, Any],
        build_log: str,
        iteration: int
    ) -> Dict[str, str]:
        """Use OpenAI to fix build errors.
        
        Args:
            requirements: Original Actor requirements
            build_log: Build error logs
            iteration: Current iteration number
            
        Returns:
            Fixed Actor files
        """
        Actor.log.info(f"Requesting fixes from OpenAI (attempt {iteration})...")
        
        system_prompt = """You are an expert at debugging and fixing Apify Actor build errors.

Analyze the build error logs and original requirements, then generate corrected Actor code.

Common issues to check:
1. Missing or incorrect imports
2. Syntax errors in Python code
3. Incorrect Apify SDK usage
4. Missing dependencies in requirements.txt
5. Dockerfile configuration issues
6. File path or structure problems

Focus on the most likely cause of the error and provide a minimal fix."""

        user_prompt = f"""An Apify Actor build failed. Please analyze the error and generate fixed code.

Original Requirements:
{requirements}

Build Error Log:
{build_log[-2000:]}

Generate corrected Actor files. Focus on fixing the specific error shown in the logs.
Respond with a JSON object mapping file paths to fixed contents for files that need changes.

Example response format:
{{
  "src/main.py": "fixed Python code here",
  "requirements.txt": "fixed requirements here"
}}

Only include files that need to be changed. Return valid JSON only."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            fixed_files_partial = json.loads(response.choices[0].message.content)
            
            # Generate complete set of files with fixes applied
            Actor.log.info(f"OpenAI suggested fixes for {len(fixed_files_partial)} files")
            
            # Generate fresh files and apply fixes
            all_files = await self.generator.generate(requirements)
            
            # Apply the fixes
            for file_path, fixed_content in fixed_files_partial.items():
                all_files[file_path] = fixed_content
                Actor.log.info(f"Applied fix to: {file_path}")
            
            return all_files
            
        except Exception as e:
            Actor.log.error(f"Failed to generate fixes: {str(e)}")
            # Return original files if fix generation fails
            return await self.generator.generate(requirements)


async def validate_and_fix(
    deployment: Dict[str, Any],
    requirements: Dict[str, Any],
    max_iterations: int = 3
) -> Dict[str, Any]:
    """Main function to validate and fix Actor builds.
    
    Args:
        deployment: Deployment information
        requirements: Original requirements
        max_iterations: Maximum fix attempts
        
    Returns:
        Final validation result
    """
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    validator = ActorValidator(openai_api_key)
    return await validator.validate_and_fix(deployment, requirements, max_iterations)

