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
        
    def handle_error(self, error: GameError) -> None:
        """Handle an error based on its severity."""
        self.error_history.append(error)
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL: {error.message}", extra=error.context)
            if error.exception:
                self.logger.critical(traceback.format_exc())
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"ERROR: {error.message}", extra=error.context)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"WARNING: {error.message}", extra=error.context)
        else:
            self.logger.info(f"INFO: {error.message}", extra=error.context)
    
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
    
    def validate_required(self, value: Any, name: str, context: dict = None) -> Any:
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
error_handler = ErrorHandler()


def safe_operation(default_value: T = None, 
                  error_message: str = "Operation failed",
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for safe operation execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            return error_handler.safe_execute(
                lambda: func(*args, **kwargs),
                default_value,
                error_message,
                severity
            )
        return wrapper
    return decorator
