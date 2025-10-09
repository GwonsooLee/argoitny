"""
Solution generation with Gemini → OpenAI fallback logic

This module provides a function to generate solutions with automatic fallback
from Gemini to OpenAI when Gemini fails after max retries.
"""
import logging
from .services.llm_factory import LLMServiceFactory

logger = logging.getLogger(__name__)


def generate_solution_with_fallback(problem_metadata, update_progress_callback):
    """
    Generate solution with Gemini → OpenAI fallback

    Strategy:
    1. Try Gemini 3 times
    2. If all Gemini attempts fail, try OpenAI 3 times
    3. Return best result

    Args:
        problem_metadata: Problem metadata dict with title, constraints, samples
        update_progress_callback: Function to update progress (takes message string)

    Returns:
        tuple: (solution_result, validation_passed, validation_error, used_service)
    """
    max_attempts_per_service = 3
    solution_result = None
    validation_passed = False
    validation_error = None
    used_service = None

    # List of LLM services to try in order (Gemini first, then OpenAI)
    llm_services_to_try = []

    # Try Gemini first
    try:
        gemini_service = LLMServiceFactory.create_service('gemini')
        llm_services_to_try.append(('gemini', gemini_service))
        logger.info("Will try Gemini first for solution generation")
    except Exception as e:
        logger.warning(f"Gemini service not available: {e}")

    # Add OpenAI as fallback
    try:
        openai_service = LLMServiceFactory.create_service('openai')
        llm_services_to_try.append(('openai', openai_service))
        logger.info("OpenAI available as fallback")
    except Exception as e:
        logger.warning(f"OpenAI service not available: {e}")

    if not llm_services_to_try:
        raise ValueError("No LLM services available (both Gemini and OpenAI failed)")

    # Try each service in order
    for service_name, current_llm_service in llm_services_to_try:
        logger.info(f"Trying {service_name} for solution generation...")
        update_progress_callback(f"🔄 Trying {service_name.upper()} for solution generation...")

        # Reset previous_attempt for new service
        previous_attempt = None

        for attempt in range(1, max_attempts_per_service + 1):
            try:
                update_progress_callback(
                    f"🧠 Step 2/2: Generating solution with {service_name.upper()} "
                    f"(attempt {attempt}/{max_attempts_per_service})..."
                )

                solution_result = current_llm_service.generate_solution_for_problem(
                    problem_metadata,
                    previous_attempt=previous_attempt,
                    progress_callback=lambda msg: update_progress_callback(f"🧠 {msg}")
                )

                solution_code = solution_result['solution_code']
                logger.info(f"Generated solution with {service_name} on attempt {attempt}: {len(solution_code)} characters")

                # Validate solution with samples
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
                        used_service = service_name
                        return (solution_result, validation_passed, validation_error, used_service)
                    else:
                        logger.warning(
                            f"{service_name} attempt {attempt}/{max_attempts_per_service} "
                            f"failed validation: {validation_error}"
                        )

                        if attempt < max_attempts_per_service:
                            # Prepare retry with error context
                            previous_attempt = {
                                'code': solution_code,
                                'error': validation_error,
                                'attempt_number': attempt
                            }
                            update_progress_callback(f"⚠ Sample test failed, analyzing mistake...")
                            continue
                        else:
                            # Last attempt failed for this service
                            logger.warning(f"⚠ {service_name} failed after {max_attempts_per_service} attempts")
                            used_service = service_name
                            break
                else:
                    logger.warning("No samples to validate")
                    used_service = service_name
                    return (solution_result, True, None, used_service)  # No samples, consider as passed

            except Exception as e:
                logger.error(f"{service_name} attempt {attempt} failed: {e}")
                if attempt < max_attempts_per_service:
                    previous_attempt = {
                        'code': solution_result['solution_code'] if solution_result else '',
                        'error': str(e),
                        'attempt_number': attempt
                    }
                    continue
                else:
                    logger.error(f"{service_name} failed after {max_attempts_per_service} attempts")
                    used_service = service_name
                    break

        # Check if we got a valid solution
        if validation_passed:
            logger.info(f"Successfully generated solution with {service_name}")
            return (solution_result, validation_passed, validation_error, used_service)
        else:
            logger.warning(
                f"All {max_attempts_per_service} attempts with {service_name} failed, "
                f"will try next service if available..."
            )

    # All services failed - return last attempt
    logger.error("All services exhausted, returning last attempt")
    return (solution_result, validation_passed, validation_error, used_service)
