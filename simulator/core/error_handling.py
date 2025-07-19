"""
Centralized error handling and logging system.
"""
import logging
import traceback
from typing import Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GameError:
    message: str
    severity: ErrorSeverity
    context: dict[str, Any]
    exception: Optional[Exception] = None


class ErrorHandler:
    """Centralized error handling for the game."""
    
    def __init__(self):
        self.logger = logging.getLogger("game_errors")
        self.error_history: list[GameError] = []
        
    def handle(self, 
              message: str, 
              severity: ErrorSeverity, 
              context: dict[str, Any] | None = None,
              exception: Optional[Exception] = None) -> None:
        """Handle an error based on its severity."""
        # Create the GameError object internally
        error = GameError(
            message=message,
            severity=severity,
            context=context or {},
            exception=exception
        )
        self.error_history.append(error)
        
        # Prefix context keys to avoid conflicts with logging system reserved keys
        safe_context = {f"ctx_{key}": value for key, value in error.context.items()} if error.context else {}
        
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
    
    def safe_execute(self, 
                    operation: Callable[[], T], 
                    default: T, 
                    error_message: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[dict] = None) -> T:
        """Safely execute an operation with error handling."""
        try:
            return operation()
        except Exception as e:
            error = GameError(
                message=f"{error_message}: {str(e)}",
                severity=severity,
                context=context or {},
                exception=e
            )
            self.handle_error(error)
            return default
    
    def validate_required(self, value: Any, name: str, context: dict[str, Any] | None = None) -> Any:
        """Validate that a required value is not None."""
        if value is None:
            error = GameError(
                message=f"Required value '{name}' is None",
                severity=ErrorSeverity.HIGH,
                context=context or {}
            )
            self.handle_error(error)
            raise ValueError(f"Required value '{name}' cannot be None")
        return value


# Global error handler instance
ERROR_HANDLER = ErrorHandler()


def safe_operation(default_value: Any = None, 
                  error_message: str = "Operation failed",
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for safe operation execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            return ERROR_HANDLER.safe_execute(
                lambda: func(*args, **kwargs),
                default_value,
                error_message,
                severity
            )
        return wrapper
    return decorator


# Convenience functions for each severity level
def log_info(message: str, context: dict[str, Any] | None = None, exception: Optional[Exception] = None) -> None:
    """Log an info-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.LOW, context, exception)


def log_warning(message: str, context: dict[str, Any] | None = None, exception: Optional[Exception] = None) -> None:
    """Log a warning-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.MEDIUM, context, exception)


def log_error(message: str, context: dict[str, Any] | None = None, exception: Optional[Exception] = None) -> None:
    """Log an error-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.HIGH, context, exception)


def log_critical(message: str, context: dict[str, Any] | None = None, exception: Optional[Exception] = None) -> None:
    """Log a critical-level message."""
    ERROR_HANDLER.handle(message, ErrorSeverity.CRITICAL, context, exception)
