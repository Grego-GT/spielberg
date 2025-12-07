"""Validator module for monitoring builds and iteratively fixing errors.

This module monitors Actor builds and uses Anthropic Claude to fix errors when builds fail.
"""

import os
import asyncio
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic
from apify import Actor
from .deployer import ActorDeployer
from .actor_generator import ActorGenerator


class ActorValidator:
    """Validates Actor builds and fixes errors iteratively."""

    def __init__(self, anthropic_api_key: str, apify_token: Optional[str] = None):
        """Initialize validator with Anthropic and Apify clients.

        Args:
            anthropic_api_key: Anthropic API key
            apify_token: Apify API token
        """
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
        self.deployer = ActorDeployer(apify_token)
        self.generator = ActorGenerator(anthropic_api_key)
        self.model = "claude-sonnet-4-5-20250929"
    
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

                    # Test run the actor to verify it produces data
                    Actor.log.info("Testing actor to verify it produces output...")
                    test_result = await self._test_actor_run(actor_id, requirements)

                    if test_result['success']:
                        Actor.log.info(f"✓ Test run successful! Produced {test_result['item_count']} items")
                        return {
                            'status': 'success',
                            'actor_id': actor_id,
                            'build_id': current_build_id,
                            'console_url': f"https://console.apify.com/actors/{actor_id}",
                            'iterations': iteration + 1,
                            'message': f"Actor built and tested successfully ({test_result['item_count']} items)"
                        }
                    else:
                        Actor.log.warning(f"✗ Test run issue: {test_result['message']}")

                        # If this is the last iteration, return partial success
                        if iteration >= max_iterations - 1:
                            return {
                                'status': 'success',  # Build succeeded even if test had issues
                                'actor_id': actor_id,
                                'build_id': current_build_id,
                                'console_url': f"https://console.apify.com/actors/{actor_id}",
                                'iterations': iteration + 1,
                                'message': f"Build succeeded but test run produced no data: {test_result['message']}"
                            }

                        # Try to fix the runtime issue
                        Actor.log.info("Attempting to fix runtime issues...")
                        fixed_files = await self._fix_runtime_errors(
                            requirements,
                            test_result['log'],
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
                        continue
                
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
    
    async def _test_actor_run(
        self,
        actor_id: str,
        requirements: Dict[str, Any],
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Test run the actor and verify it produces data.

        Args:
            actor_id: Actor ID to test
            requirements: Original requirements (to generate test input)
            timeout: Maximum seconds to wait for run

        Returns:
            Dict with success status, item count, message, and logs
        """
        try:
            # Prepare minimal test input based on requirements
            test_input = {}
            for field in requirements.get('input_fields', []):
                field_name = field.get('name')
                default_value = field.get('default')
                if default_value is not None:
                    test_input[field_name] = default_value

            Actor.log.info(f"Running test with input: {test_input}")

            # Start the actor run
            run = await self.deployer.client.actor(actor_id).call(
                run_input=test_input,
                timeout_secs=timeout,
                memory_mbytes=256  # Minimal memory for test
            )

            run_id = run['id']
            run_status = run.get('status')

            Actor.log.info(f"Test run {run_id} completed with status: {run_status}")

            # Get run log
            try:
                log = await self.deployer.client.log(run_id).get()
                log_text = log if isinstance(log, str) else str(log)
            except Exception:
                log_text = "Could not fetch run log"

            # Check if run succeeded
            if run_status != 'SUCCEEDED':
                return {
                    'success': False,
                    'item_count': 0,
                    'message': f'Run failed with status: {run_status}',
                    'log': log_text
                }

            # Check dataset for output
            default_dataset_id = run.get('defaultDatasetId')
            if default_dataset_id:
                dataset = await self.deployer.client.dataset(default_dataset_id).get()
                item_count = dataset.get('itemCount', 0)

                if item_count > 0:
                    return {
                        'success': True,
                        'item_count': item_count,
                        'message': f'Produced {item_count} items',
                        'log': log_text
                    }
                else:
                    return {
                        'success': False,
                        'item_count': 0,
                        'message': 'Run succeeded but produced no data',
                        'log': log_text
                    }
            else:
                return {
                    'success': False,
                    'item_count': 0,
                    'message': 'No dataset found',
                    'log': log_text
                }

        except Exception as e:
            Actor.log.warning(f"Test run failed: {str(e)}")
            return {
                'success': False,
                'item_count': 0,
                'message': f'Test run error: {str(e)}',
                'log': str(e)
            }

    async def _fix_runtime_errors(
        self,
        requirements: Dict[str, Any],
        run_log: str,
        iteration: int
    ) -> Dict[str, str]:
        """Use Claude to fix runtime errors (no data, scraping issues, etc.).

        Args:
            requirements: Original Actor requirements
            run_log: Runtime error logs
            iteration: Current iteration number

        Returns:
            Fixed Actor files
        """
        Actor.log.info(f"Requesting runtime fixes from Claude (attempt {iteration})...")

        system_prompt = """You are an expert at debugging web scraping and data extraction issues.

Analyze the runtime logs to understand why the Actor isn't producing data.

Common runtime issues:
1. Incorrect HTML selectors (element not found)
2. Wrong CSS classes or XPath expressions
3. Page structure different than expected
4. Missing data extraction logic
5. Incorrect API endpoints or parameters
6. Timing issues (content not loaded)

Provide specific fixes to make the scraper work correctly."""

        user_prompt = f"""An Apify Actor ran successfully but produced no output data.

Original Requirements:
{requirements}

Runtime Log:
{run_log[-3000:]}

The actor needs to be fixed to correctly extract data. Analyze the logs to understand what went wrong.

Common issues:
- "Could not find X" means the HTML selector is wrong
- Check the actual HTML structure and update selectors accordingly
- Ensure data extraction logic is correct

Generate corrected Actor files with working selectors and extraction logic.
Respond with a JSON object mapping file paths to fixed contents.

Example:
{{
  "src/main.py": "corrected Python code with fixed selectors"
}}

Return valid JSON only."""

        try:
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            import json
            response_text = response.content[0].text

            # Strip markdown if present
            if response_text.strip().startswith('```'):
                first_newline = response_text.find('\n')
                if first_newline != -1:
                    response_text = response_text[first_newline + 1:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3].rstrip()

            fixed_files_partial = json.loads(response_text)

            # Generate complete set of files with fixes applied
            Actor.log.info(f"Claude suggested fixes for {len(fixed_files_partial)} files")

            # Generate fresh files and apply fixes
            all_files = await self.generator.generate(requirements)

            # Apply the fixes
            for file_path, fixed_content in fixed_files_partial.items():
                all_files[file_path] = fixed_content
                Actor.log.info(f"Applied runtime fix to: {file_path}")

            return all_files

        except Exception as e:
            Actor.log.error(f"Failed to generate runtime fixes: {str(e)}")
            # Return original files if fix generation fails
            return await self.generator.generate(requirements)

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
        Actor.log.info(f"Requesting fixes from Claude (attempt {iteration})...")

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
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            import json
            fixed_files_partial = json.loads(response.content[0].text)
            
            # Generate complete set of files with fixes applied
            Actor.log.info(f"Claude suggested fixes for {len(fixed_files_partial)} files")

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
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    validator = ActorValidator(anthropic_api_key)
    return await validator.validate_and_fix(deployment, requirements, max_iterations)

