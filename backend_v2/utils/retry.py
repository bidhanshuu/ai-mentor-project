# -*- coding: utf-8 -*-
"""
retry.py
--------
Timeout and retry utilities for resilient API calls.
Handles transient errors (429, 5xx) with exponential backoff.
"""

import asyncio
import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryTimeoutError(Exception):
    """Custom timeout error for clarity."""
    pass


async def retry_with_timeout(
    func: Callable,
    *args: Any,
    max_retries: int = 2,
    timeout_seconds: int = 25,
    backoff_base: float = 2.0,
    **kwargs: Any,
) -> Any:
    """
    Execute async function with timeout and retry logic for transient errors.

    Args:
        func: Async function to call
        max_retries: Number of retries on transient errors (429, 5xx)
        timeout_seconds: Timeout per attempt (20-30s recommended)
        backoff_base: Exponential backoff multiplier (2.0 = double each retry)
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Function result

    Raises:
        RetryTimeoutError: If timeout exceeded on all attempts
        RuntimeError: If all retries exhausted on non-transient errors
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            logger.debug(
                f"[Retry] Attempt {attempt + 1}/{max_retries + 1} "
                f"(timeout: {timeout_seconds}s)"
            )
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds,
            )
            if attempt > 0:
                logger.info(f"[Retry] Success on attempt {attempt + 1}")
            return result

        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(
                f"[Retry] Timeout on attempt {attempt + 1}/{max_retries + 1}: "
                f"{timeout_seconds}s exceeded"
            )
            if attempt >= max_retries:
                raise RetryTimeoutError(
                    f"Request timeout after {max_retries + 1} attempts"
                ) from e

        except Exception as e:
            error_msg = str(e)

            # Check if it's a transient error we should retry
            is_transient = any(
                code in error_msg
                for code in ["429", "500", "502", "503", "502", "504"]
            )

            if is_transient and attempt < max_retries:
                wait_time = backoff_base ** attempt
                logger.warning(
                    f"[Retry] Transient error (attempt {attempt + 1}): {error_msg} | "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                last_error = e
            else:
                if is_transient:
                    logger.error(
                        f"[Retry] Transient error exhausted retries: {error_msg}"
                    )
                else:
                    logger.error(f"[Retry] Non-transient error: {error_msg}")
                raise

    raise RuntimeError(f"All {max_retries + 1} attempts failed") from last_error
