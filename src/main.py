"""Main orchestrator for the Spielberg Actor.

This module coordinates all phases of Actor generation: intent analysis, code generation,
deployment, and validation.
"""

from __future__ import annotations
import os
from typing import Any, Dict
from apify import Actor

from .intent_analyzer import analyze_intent
from .actor_generator import generate_actor_code
from .deployer import deploy_actor
from .validator import validate_and_fix


async def main() -> None:
    """Main entry point for the Spielberg Actor.
    
    This function orchestrates the complete Actor generation pipeline:
    1. Get and validate user input
    2. Analyze intent and generate requirements
    3. Generate Actor source code
    4. Deploy Actor to Apify platform
    5. Validate build and fix errors iteratively
    6. Output results
    """
    async with Actor:
        Actor.log.info("🎬 Spielberg Actor Generator started")
        
        try:
            # Step 1: Get and validate input
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 1: Getting user input")
            Actor.log.info("=" * 60)
            
            actor_input = await Actor.get_input()
            if not actor_input:
                raise ValueError("No input provided")
            
            user_prompt = actor_input.get('userPrompt')
            if not user_prompt:
                raise ValueError("userPrompt is required")
            
            Actor.log.info(f"User prompt: {user_prompt}")
            
            # Validate OpenAI API key
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Please set it in Actor settings under Environment variables."
                )
            
            Actor.log.info("✓ Input validated")
            
            # Step 2: Analyze intent and generate requirements
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 2: Analyzing intent and generating requirements")
            Actor.log.info("=" * 60)
            
            requirements = await analyze_intent(user_prompt)
            
            Actor.log.info(f"✓ Requirements generated for: {requirements.get('actor_title')}")
            Actor.log.info(f"  Actor type: {requirements.get('actor_type')}")
            Actor.log.info(f"  Input fields: {len(requirements.get('input_fields', []))}")
            Actor.log.info(f"  Dependencies: {', '.join(requirements.get('dependencies', []))}")
            
            # Save requirements to key-value store
            await Actor.set_value('requirements', requirements)
            
            # Step 3: Generate Actor code
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 3: Generating Actor source code")
            Actor.log.info("=" * 60)
            
            actor_files = await generate_actor_code(requirements)
            
            Actor.log.info(f"✓ Generated {len(actor_files)} files:")
            for file_path in sorted(actor_files.keys()):
                size = len(actor_files[file_path])
                Actor.log.info(f"  - {file_path} ({size} bytes)")
            
            # Save generated files to key-value store
            for file_path, content in actor_files.items():
                safe_key = file_path.replace('/', '_').replace('.', '_')
                await Actor.set_value(f"generated_{safe_key}", content, content_type='text/plain')
            
            # Step 4: Deploy Actor to Apify
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 4: Deploying Actor to Apify platform")
            Actor.log.info("=" * 60)
            
            actor_name = requirements.get('actor_name', 'generated-actor')
            deployment = await deploy_actor(actor_files, actor_name)
            
            Actor.log.info(f"✓ Actor deployed:")
            Actor.log.info(f"  Actor ID: {deployment['actor_id']}")
            Actor.log.info(f"  Build ID: {deployment['build_id']}")
            Actor.log.info(f"  Console URL: {deployment['console_url']}")
            
            # Step 5: Validate build and fix errors if needed
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 5: Validating build and fixing errors")
            Actor.log.info("=" * 60)
            
            result = await validate_and_fix(
                deployment=deployment,
                requirements=requirements,
                max_iterations=3
            )
            
            Actor.log.info(f"✓ Validation complete: {result['status']}")
            Actor.log.info(f"  Iterations: {result.get('iterations', 0)}")
            Actor.log.info(f"  Message: {result.get('message', 'N/A')}")
            
            # Step 6: Output results
            Actor.log.info("=" * 60)
            Actor.log.info("STEP 6: Saving results")
            Actor.log.info("=" * 60)
            
            output_data = {
                'status': result['status'],
                'actorId': result['actor_id'],
                'consoleUrl': result['console_url'],
                'actorName': actor_name,
                'actorTitle': requirements.get('actor_title'),
                'buildId': result.get('build_id'),
                'iterations': result.get('iterations', 0),
                'message': result.get('message', ''),
                'error': result.get('error'),
                'generatedFiles': list(actor_files.keys()),
                'requirements': {
                    'actor_type': requirements.get('actor_type'),
                    'description': requirements.get('description'),
                    'dependencies': requirements.get('dependencies', [])
                }
            }
            
            await Actor.push_data(output_data)
            
            # Log final status
            Actor.log.info("=" * 60)
            if result['status'] == 'success':
                Actor.log.info("🎉 SUCCESS! Actor created and deployed successfully!")
                Actor.log.info(f"🔗 View your Actor: {result['console_url']}")
            else:
                Actor.log.warning("⚠️  Actor created but build failed")
                Actor.log.warning(f"🔗 Check build logs: {result['console_url']}")
                if result.get('error'):
                    Actor.log.error(f"Error details: {result['error'][:500]}")
            
            Actor.log.info("=" * 60)
            Actor.log.info("🎬 Spielberg Actor Generator finished")
            
        except ValueError as e:
            # Input validation errors
            Actor.log.error(f"❌ Input validation error: {str(e)}")
            await Actor.push_data({
                'status': 'failed',
                'error': str(e),
                'errorType': 'validation_error'
            })
            await Actor.fail(status_message=str(e))
            
        except Exception as e:
            # Unexpected errors
            Actor.log.error(f"❌ Unexpected error: {str(e)}")
            Actor.log.exception(e)
            
            await Actor.push_data({
                'status': 'failed',
                'error': str(e),
                'errorType': 'unexpected_error'
            })
            await Actor.fail(status_message=f"Actor generation failed: {str(e)}")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

