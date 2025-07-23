"""
Centralized error handling and logging system.
"""

import logging
import traceback
from typing import Any, Callable, TypeVar, Optional
from dataclasses import dataclass
from enum import Enum

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Enumeration of error severity levels for the game's error handling system."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GameError:
    """Represents a game error with severity, context, and optional exception information."""
    message: str
    severity: ErrorSeverity
    context: dict[str, Any]
    exception: Optional[Exception] = None


class ErrorHandler:
    """Centralized error handling for the game."""

    def __init__(self) -> None:
        """Initialize the ErrorHandler with a logger and empty error history."""
        self.logger = logging.getLogger("game_errors")
        self.error_history: list[GameError] = []

    def handle(
        self,
        message: str,
        severity: ErrorSeverity,
        context: Optional[dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Handle an error based on its severity."""
        # Create the GameError object internally
        error = GameError(
            message=message,
            severity=severity,
            context=context or {},
            exception=exception,
        )
        self.error_history.append(error)

        # Prefix context keys to avoid conflicts with logging system reserved keys
        safe_context = (
            {f"ctx_{key}": value for key, value in error.context.items()}
            if error.context
            else {}
        )

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL: {error.message}", extra=safe_context)
            if error.exception:
                self.logger.critical(traceback.format_exc())
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"ERROR: {error.message}", extra=safe_context)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"WARNING: {error.message}", extra=safe_context)
        else:
            self.logger.info(f"INFO: {error.message}", extra=safe_context)

    def handle_error(self, error: GameError) -> None:
        """Handle an error based on its severity. (Legacy method - prefer handle())"""
        self.handle(error.message, error.severity, error.context, error.exception)

    def safe_execute(
        self,
        operation: Callable[[], T],
        default: T,
        error_message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[dict] = None,
    ) -> T:
        """Safely execute an operation with error handling."""
        try:
            return operation()
        except Exception as e:
            error = GameError(
                message=f"{error_message}: {str(e)}",
                severity=severity,
                context=context or {},
                exception=e,
            )
            self.handle_error(error)
            return default

    def validate_required(
        self, value: Any, name: str, context: Optional[dict[str, Any]] = None
    ) -> Any:
        """Validate that a required value is not None."""
        if value is None:
            error = GameError(
                message=f"Required value '{name}' is None",
                severity=ErrorSeverity.HIGH,
                context=context or {},
            )
            self.handle_error(error)
            raise ValueError(f"Required value '{name}' cannot be None")
        return value


# Global error handler instance
ERROR_HANDLER = ErrorHandler()


def safe_operation(
    default_value: Any = None,
    error_message: str = "Operation failed",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
) -> Callable:
    """
    Decorator for safe operation execution.
    
    Args:
        default_value (Any): Default value to return on error.
        error_message (str): Error message prefix for logging.
        severity (ErrorSeverity): Severity level for errors.
        
    Returns:
        Callable: The decorator function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            """Wrapper function that executes the decorated function safely."""
            return ERROR_HANDLER.safe_execute(
                lambda: func(*args, **kwargs), default_value, error_message, severity
            )

        return wrapper

    return decorator


# Convenience functions for each severity level
def log_info(
    message: str,
    context: Optional[dict[str, Any]] = None,
    exception: Optional[Exception] = None,
) -> None:
    """Log an info-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.LOW, context, exception)


def log_warning(
    message: str,
    context: Optional[dict[str, Any]] = None,
    exception: Optional[Exception] = None,
) -> None:
    """Log a warning-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.MEDIUM, context, exception)


def log_error(
    message: str,
    context: Optional[dict[str, Any]] = None,
    exception: Optional[Exception] = None,
) -> None:
    """Log an error-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.HIGH, context, exception)


def log_critical(
    message: str,
    context: Optional[dict[str, Any]] = None,
    exception: Optional[Exception] = None,
) -> None:
    """Log a critical-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.CRITICAL, context, exception)


# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================
# These helpers provide a clean, readable way to validate inputs with consistent
# error handling, logging, and correction behaviors.


def require_non_empty_string(
    value: Any, param_name: str, context: Optional[dict[str, Any]] = None
) -> str:
    """
    Validates that a value is a non-empty string.

    Args:
        value: The value to validate
        param_name: Human-readable parameter name for error messages
        context: Additional context for logging

    Returns:
        str: The validated string value

    Raises:
        ValueError: If validation fails
    """
    if not value or not isinstance(value, str):
        log_error(
            f"{param_name} must be a non-empty string, got: {value}",
            {
                **(context or {}),
                "param_name": param_name,
                "value": value,
                "type": type(value).__name__,
            },
        )
        raise ValueError(f"Invalid {param_name}: {value}")
    return value


def require_enum_type(
    value: Any, enum_class: type, param_name: str, context: Optional[dict[str, Any]] = None
) -> Any:
    """
    Validates that a value is of the specified enum type.

    Args:
        value: The value to validate
        enum_class: The expected enum class
        param_name: Human-readable parameter name for error messages
        context: Additional context for logging

    Returns:
        The validated enum value

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, enum_class):
        log_error(
            f"{param_name} must be {enum_class.__name__} enum, got: {type(value).__name__}",
            {
                **(context or {}),
                "param_name": param_name,
                "expected_type": enum_class.__name__,
                "actual_type": type(value).__name__,
                "value": value,
            },
        )
        raise ValueError(
            f"Invalid {param_name}: expected {enum_class.__name__}, got {type(value).__name__}"
        )
    return value


def ensure_string(
    value: Any,
    param_name: str,
    default: str = "",
    context: Optional[dict[str, Any]] = None,
) -> str:
    """
    Ensures a value is a string, converting or using default if needed.
    Logs a warning for non-string types but continues execution.

    Args:
        value: The value to ensure is a string
        param_name: Human-readable parameter name for error messages
        default: Default value if conversion fails
        context: Additional context for logging

    Returns:
        str: The string value or default
    """
    if not isinstance(value, str):
        log_warning(
            f"{param_name} should be string, got: {type(value).__name__}, converting",
            {
                **(context or {}),
                "param_name": param_name,
                "value": value,
                "type": type(value).__name__,
            },
        )
        return str(value) if value is not None else default
    return value


def ensure_non_negative_int(
    value: Any, param_name: str, default: int = 0, context: Optional[dict[str, Any]] = None
) -> int:
    """
    Ensures a value is a non-negative integer, correcting if needed.
    Logs a warning for invalid values but continues execution.

    Args:
        value: The value to ensure is a non-negative integer
        param_name: Human-readable parameter name for error messages
        default: Default value if correction is needed
        context: Additional context for logging

    Returns:
        int: The corrected integer value
    """
    if not isinstance(value, int) or value < 0:
        log_warning(
            f"{param_name} must be non-negative integer, got: {value}, correcting to {default}",
            {
                **(context or {}),
                "param_name": param_name,
                "value": value,
                "corrected_to": default,
            },
        )
        return max(0, int(value) if isinstance(value, (int, float)) else default)
    return value


def ensure_int_in_range(
    value: Any,
    param_name: str,
    min_val: int,
    max_val: Optional[int] = None,
    default: Optional[int] = None,
    context: Optional[dict[str, Any]] = None,
) -> int:
    """
    Ensures a value is an integer within the specified range, correcting if needed.
    Logs a warning for out-of-range values but continues execution.

    Args:
        value: The value to validate
        param_name: Human-readable parameter name for error messages
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive), None for no maximum
        default: Default value if correction is needed, uses min_val if None
        context: Additional context for logging

    Returns:
        int: The corrected integer value
    """
    if default is None:
        default = min_val

    if (
        not isinstance(value, int)
        or value < min_val
        or (max_val is not None and value > max_val)
    ):
        range_desc = (
            f">= {min_val}" if max_val is None else f"between {min_val} and {max_val}"
        )
        log_warning(
            f"{param_name} must be integer {range_desc}, got: {value}, correcting to {default}",
            {
                **(context or {}),
                "param_name": param_name,
                "value": value,
                "min_val": min_val,
                "max_val": max_val,
                "corrected_to": default,
            },
        )

        # Try to convert and clamp
        try:
            converted = int(value) if isinstance(value, (int, float)) else default
            if converted < min_val:
                return min_val
            elif max_val is not None and converted > max_val:
                return max_val
            else:
                return converted
        except (ValueError, TypeError):
            return default
    return value


def ensure_list_of_type(
    value: Any,
    expected_type: type,
    param_name: str,
    default: Optional[list] = None,
    converter: Optional[Callable[[Any], Any]] = None,
    validator: Optional[Callable[[Any], bool]] = None,
    context: Optional[dict[str, Any]] = None,
) -> list:
    """
    Ensures a value is a list of the specified type, correcting if needed.
    Logs warnings for invalid values but continues execution.

    Args:
        value: The value to validate
        expected_type: The expected type for list items
        param_name: Human-readable parameter name for error messages
        default: Default value if correction is needed
        converter: Optional function to convert invalid items to expected type
        validator: Optional function to validate items of the expected type
        context: Additional context for logging

    Returns:
        list: The validated/corrected list
    """
    if default is None:
        default = []

    if value is None:
        return default

    if not isinstance(value, list):
        log_warning(
            f"{param_name} should be list, got: {type(value).__name__}, using default",
            {
                **(context or {}),
                "param_name": param_name,
                "value": value,
                "type": type(value).__name__,
            },
        )
        return default

    # Ensure all items are of the expected type
    cleaned_list = []
    had_invalid_items = False

    for i, item in enumerate(value):
        if isinstance(item, expected_type):
            # Item is correct type, now validate if validator is provided
            if validator and not validator(item):
                had_invalid_items = True
                log_warning(
                    f"{param_name}[{i}] failed validation, skipping item: {item}",
                    {
                        **(context or {}),
                        "param_name": param_name,
                        "index": i,
                        "item": item,
                        "expected_type": expected_type.__name__,
                    },
                )
                continue  # Skip invalid items
            else:
                cleaned_list.append(item)
        else:
            # Item is wrong type, try to convert
            had_invalid_items = True
            if converter:
                try:
                    converted_item = converter(item)
                    if isinstance(converted_item, expected_type):
                        # Validate converted item if validator is provided
                        if validator and not validator(converted_item):
                            log_warning(
                                f"{param_name}[{i}] converted item failed validation, skipping: {converted_item}",
                                {
                                    **(context or {}),
                                    "param_name": param_name,
                                    "index": i,
                                    "original": item,
                                    "converted": converted_item,
                                    "expected_type": expected_type.__name__,
                                },
                            )
                            continue
                        cleaned_list.append(converted_item)
                    else:
                        log_warning(
                            f"{param_name}[{i}] converter returned wrong type, skipping item: {item}",
                            {
                                **(context or {}),
                                "param_name": param_name,
                                "index": i,
                                "item": item,
                                "expected_type": expected_type.__name__,
                                "converter_result_type": type(converted_item).__name__,
                            },
                        )
                except Exception as e:
                    log_warning(
                        f"{param_name}[{i}] conversion failed, skipping item: {item}",
                        {
                            **(context or {}),
                            "param_name": param_name,
                            "index": i,
                            "item": item,
                            "error": str(e),
                        },
                    )
            else:
                # No converter provided, use default conversion for common types
                try:
                    if expected_type == str:
                        converted = str(item) if item is not None else ""
                    elif expected_type == int:
                        converted = int(item)
                    elif expected_type == float:
                        converted = float(item)
                    else:
                        # Can't convert without explicit converter
                        log_warning(
                            f"{param_name}[{i}] wrong type and no converter provided, skipping: {item}",
                            {
                                **(context or {}),
                                "param_name": param_name,
                                "index": i,
                                "item": item,
                                "expected_type": expected_type.__name__,
                                "actual_type": type(item).__name__,
                            },
                        )
                        continue
                    
                    # Validate converted item if validator is provided
                    if validator and not validator(converted):
                        log_warning(
                            f"{param_name}[{i}] converted item failed validation, skipping: {converted}",
                            {
                                **(context or {}),
                                "param_name": param_name,
                                "index": i,
                                "original": item,
                                "converted": converted,
                            },
                        )
                        continue
                    
                    cleaned_list.append(converted)
                except (ValueError, TypeError) as e:
                    log_warning(
                        f"{param_name}[{i}] conversion failed, skipping item: {item}",
                        {
                            **(context or {}),
                            "param_name": param_name,
                            "index": i,
                            "item": item,
                            "error": str(e),
                        },
                    )

    if had_invalid_items:
        log_warning(
            f"{param_name} had invalid items, cleaned list created",
            {
                **(context or {}),
                "param_name": param_name,
                "original_length": len(value),
                "cleaned_length": len(cleaned_list),
                "expected_type": expected_type.__name__,
            },
        )

    return cleaned_list


def ensure_list_of_strings(
    value: Any,
    param_name: str,
    default: Optional[list[str]] = None,
    context: Optional[dict[str, Any]] = None,
) -> list[str]:
    """
    Ensures a value is a list of strings, correcting if needed.
    This is a convenience wrapper around ensure_list_of_type for backward compatibility.
    
    Args:
        value: The value to validate
        param_name: Human-readable parameter name for error messages
        default: Default value if correction is needed
        context: Additional context for logging

    Returns:
        list[str]: The validated/corrected list of strings
    """
    return ensure_list_of_type(
        value=value,
        expected_type=str,
        param_name=param_name,
        default=default or [],
        context=context,
    )


def validate_required_object(
    obj: Any,
    param_name: str,
    required_attributes: Optional[list[str]] = None,
    context: Optional[dict[str, Any]] = None,
) -> Any:
    """
    Validates that an object exists and optionally has required attributes/methods.
    Raises an error if validation fails - used for critical dependencies.

    Args:
        obj: The object to validate
        param_name: Human-readable parameter name for error messages
        required_attributes: List of attribute/method names that must exist on the object
        context: Additional context for logging

    Returns:
        Any: The validated object

    Raises:
        ValueError: If validation fails
    """
    if obj is None:
        log_error(
            f"{param_name} cannot be None",
            {**(context or {}), "param_name": param_name},
        )
        raise ValueError(f"{param_name} is required but was None")

    if required_attributes:
        missing_attrs = []
        for attr in required_attributes:
            if not hasattr(obj, attr):
                missing_attrs.append(attr)

        if missing_attrs:
            log_error(
                f"{param_name} missing required attributes: {missing_attrs}",
                {
                    **(context or {}),
                    "param_name": param_name,
                    "missing_attributes": missing_attrs,
                    "object_type": type(obj).__name__,
                },
            )
            raise ValueError(
                f"{param_name} missing required attributes: {missing_attrs}"
            )

    return obj


def safe_get_attribute(
    obj: Any, attr_name: str, default: Any = None, param_name: str = "object"
) -> Any:
    """
    Safely gets an attribute from an object, returning default if not found.
    Logs a warning if the attribute is missing.

    Args:
        obj: The object to get the attribute from
        attr_name: The name of the attribute to get
        default: Default value if attribute is missing
        param_name: Human-readable name for the object (for logging)

    Returns:
        Any: The attribute value or default
    """
    if obj is None:
        return default

    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    else:
        log_warning(
            f"{param_name} missing attribute '{attr_name}', using default: {default}",
            {
                "param_name": param_name,
                "attr_name": attr_name,
                "default": default,
                "object_type": type(obj).__name__,
            },
        )
        return default
