"""
Solution generation with retry logic

This module provides a function to generate solutions with retry logic
for the model specified in llm_config.
"""
import logging
from .services.llm_factory import LLMServiceFactory

logger = logging.getLogger(__name__)


def generate_solution_with_retry(problem_metadata, update_progress_callback, llm_config=None):
    """
    Generate solution with retry logic (no fallback to different models)

    Strategy:
    1. Use the model specified in llm_config (default: gpt-5)
    2. Try the selected model 2 times total (1 initial attempt + 1 retry)
    3. NO fallback to another model
    4. If both attempts fail, return the last attempt result with error

    Args:
        problem_metadata: Problem metadata dict with title, constraints, samples
        update_progress_callback: Function to update progress (takes message string)
        llm_config: Optional LLM configuration dict with model, reasoning_effort, max_output_tokens
                   Default: {'model': 'gpt-5', 'reasoning_effort': 'medium', 'max_output_tokens': 8192}

    Returns:
        tuple: (solution_result, validation_passed, validation_error, used_service)
    """
    # Apply default LLM config if not provided
    if llm_config is None:
        llm_config = {
            'model': 'gpt-5',
            'reasoning_effort': 'medium',
            'max_output_tokens': 8192
        }

    # Extract model from llm_config (default to gpt-5)
    model = llm_config.get('model', 'gpt-5').lower()

    # Determine service type from model name
    if model.startswith('gpt'):
        service_name = 'openai'
    elif model.startswith('gemini'):
        service_name = 'gemini'
    else:
        # Default to gpt-5 if model format is unrecognized
        logger.warning(f"Unrecognized model '{model}', defaulting to gpt-5")
        service_name = 'openai'
        model = 'gpt-5'

    # Max 2 attempts for ANY model
    max_attempts = 2
    solution_result = None
    validation_passed = False
    validation_error = None

    logger.info(f"Solution generation using {service_name.upper()} (model: {model}) with {max_attempts} attempts max")
    update_progress_callback(f"🔄 Generating solution with {service_name.upper()} (model: {model})...")

    # Create the selected LLM service
    try:
        current_llm_service = LLMServiceFactory.create_service(service_name)
    except Exception as e:
        logger.error(f"Failed to create {service_name} service: {e}")
        raise ValueError(f"{service_name.upper()} service not available: {e}")

    # Reset previous_attempt
    previous_attempt = None

    # Try up to max_attempts times with the SAME service
    for attempt in range(1, max_attempts + 1):
        try:
            update_progress_callback(
                f"🧠 Step 2/2: Generating solution with {service_name.upper()} "
                f"(attempt {attempt}/{max_attempts})..."
            )

            # Pass llm_config to OpenAI service only (Gemini doesn't use it)
            if service_name == 'openai':
                solution_result = current_llm_service.generate_solution_for_problem(
                    problem_metadata,
                    previous_attempt=previous_attempt,
                    progress_callback=lambda msg: update_progress_callback(f"🧠 {msg}"),
                    llm_config=llm_config
                )
            else:
                # Gemini doesn't accept llm_config
                solution_result = current_llm_service.generate_solution_for_problem(
                    problem_metadata,
                    previous_attempt=previous_attempt,
                    progress_callback=lambda msg: update_progress_callback(f"🧠 {msg}")
                )

            solution_code = solution_result['solution_code']
            logger.info(f"Generated solution with {service_name} on attempt {attempt}: {len(solution_code)} characters")

            # Validate solution with user-provided samples
            samples = problem_metadata.get('samples', [])
            if samples:
                update_progress_callback(f"✓ Testing solution with {len(samples)} sample{'s' if len(samples) > 1 else ''}...")

                validation_passed, validation_error = current_llm_service._validate_solution_with_samples(
                    solution_code,
                    samples
                )

                if validation_passed:
                    logger.info(f"✓ Solution passed all {len(samples)} samples on {service_name} attempt {attempt}")
                    update_progress_callback(f"✓ Solution verified with {len(samples)} samples using {service_name.upper()}")
                    return (solution_result, validation_passed, validation_error, service_name)
                else:
                    logger.warning(
                        f"{service_name} attempt {attempt}/{max_attempts} "
                        f"failed validation: {validation_error}"
                    )

                    if attempt < max_attempts:
                        # Prepare retry with error context
                        previous_attempt = {
                            'code': solution_code,
                            'error': validation_error,
                            'attempt_number': attempt
                        }
                        update_progress_callback(f"⚠ Sample test failed, retrying with error context...")
                        continue
                    else:
                        # Last attempt failed
                        logger.warning(f"⚠ {service_name} failed after {max_attempts} attempts")
                        break
            else:
                logger.warning("No samples to validate")
                return (solution_result, True, None, service_name)  # No samples, consider as passed

        except Exception as e:
            logger.error(f"{service_name} attempt {attempt} failed: {e}", exc_info=True)
            if attempt < max_attempts:
                previous_attempt = {
                    'code': solution_result['solution_code'] if solution_result else '',
                    'error': str(e),
                    'attempt_number': attempt
                }
                update_progress_callback(f"⚠ Attempt {attempt} failed: {str(e)[:100]}... Retrying...")
                continue
            else:
                # Last attempt failed - raise exception to fail the task
                logger.error(f"{service_name} failed after {max_attempts} attempts with error: {e}")
                raise ValueError(f"Solution generation failed after {max_attempts} attempts: {str(e)}")

    # All attempts failed validation - raise exception to fail the task
    logger.error(f"All {max_attempts} attempts with {service_name} exhausted. Last validation error: {validation_error}")
    raise ValueError(f"Solution generation failed validation after {max_attempts} attempts: {validation_error}")
