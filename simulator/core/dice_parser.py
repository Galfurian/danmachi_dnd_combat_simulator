"""
Safe dice expression parser to replace eval() usage.
"""
import re
import random
from typing import Tuple, Union
from core.error_handling import error_handler, ErrorSeverity, GameError


class DiceParser:
    """Safe parser for dice expressions without using eval()."""
    
    DICE_PATTERN = re.compile(r'(\d*)d(\d+)([+-]\d+)?', re.IGNORECASE)
    SIMPLE_MATH = re.compile(r'^[\d\s\+\-\*\/\(\)]+$')
    
    @staticmethod
    def parse_dice(expression: str) -> Tuple[int, str]:
        """
        Safely parse and roll dice expressions.
        
        Args:
            expression: Dice expression like "1d20+5" or "2d6"
            
        Returns:
            Tuple of (result, description)
            
        Raises:
            ValueError: If expression is invalid
        """
        if not expression:
            error_handler.handle_error(GameError(
                "Empty dice expression provided",
                ErrorSeverity.MEDIUM,
                {"expression": expression}
            ))
            raise ValueError("Invalid dice expression: empty")
            
        if not isinstance(expression, str):
            error_handler.handle_error(GameError(
                f"Dice expression must be string, got {type(expression).__name__}",
                ErrorSeverity.MEDIUM,
                {"expression": expression, "type": type(expression).__name__}
            ))
            raise ValueError("Invalid dice expression: not string")
            
        # Remove whitespace and convert to uppercase
        try:
            expr = expression.strip().upper()
        except Exception as e:
            error_handler.handle_error(GameError(
                f"Error processing dice expression: {str(e)}",
                ErrorSeverity.HIGH,
                {"expression": expression},
                e
            ))
            raise ValueError(f"Error processing expression: {e}")
        
        # Handle simple numbers
        if expr.isdigit():
            try:
                value = int(expr)
                if value < 0:
                    error_handler.handle_error(GameError(
                        f"Negative values not allowed in dice expressions: {value}",
                        ErrorSeverity.MEDIUM,
                        {"expression": expression, "value": value}
                    ))
                    raise ValueError(f"Negative value: {value}")
                return value, str(value)
            except ValueError as e:
                error_handler.handle_error(GameError(
                    f"Invalid numeric expression: {expression}",
                    ErrorSeverity.MEDIUM,
                    {"expression": expression},
                    e
                ))
                raise
        
        # Find all dice rolls
        total = 0
        details = []
        
        # Replace dice rolls with their results
        def roll_dice(match):
            nonlocal total, details
            
            try:
                count_str, sides_str, modifier_str = match.groups()
                count = int(count_str) if count_str else 1
                sides = int(sides_str)
                modifier = int(modifier_str) if modifier_str else 0
                
                if count <= 0:
                    error_handler.handle_error(GameError(
                        f"Invalid dice count: {count}",
                        ErrorSeverity.HIGH,
                        {"expression": expression, "count": count, "sides": sides}
                    ))
                    raise ValueError(f"Invalid dice count: {count}")
                    
                if count > 100:  # Reasonable limits
                    error_handler.handle_error(GameError(
                        f"Too many dice: {count} (limit: 100)",
                        ErrorSeverity.HIGH,
                        {"expression": expression, "count": count, "sides": sides}
                    ))
                    raise ValueError(f"Too many dice: {count}")
                    
                if sides <= 0:
                    error_handler.handle_error(GameError(
                        f"Invalid dice sides: {sides}",
                        ErrorSeverity.HIGH,
                        {"expression": expression, "count": count, "sides": sides}
                    ))
                    raise ValueError(f"Invalid dice sides: {sides}")
                    
                if sides > 1000:
                    error_handler.handle_error(GameError(
                        f"Too many sides: {sides} (limit: 1000)",
                        ErrorSeverity.HIGH,
                        {"expression": expression, "count": count, "sides": sides}
                    ))
                    raise ValueError(f"Too many sides: {sides}")
                    
                rolls = [random.randint(1, sides) for _ in range(count)]
                roll_sum = sum(rolls) + modifier
                
                total += roll_sum
                
                if count == 1:
                    detail = f"d{sides}({rolls[0]})"
                else:
                    detail = f"{count}d{sides}({'+'.join(map(str, rolls))})"
                    
                if modifier != 0:
                    detail += f"{modifier:+d}"
                    
                details.append(detail)
                return str(roll_sum)
                
            except Exception as e:
                error_handler.handle_error(GameError(
                    f"Error rolling dice in expression '{expression}': {str(e)}",
                    ErrorSeverity.HIGH,
                    {"expression": expression, "match": match.group()},
                    e
                ))
                raise ValueError(f"Error rolling dice: {e}")
        
        try:
            # Replace dice expressions
            processed = DiceParser.DICE_PATTERN.sub(roll_dice, expr)
            
            # Handle any remaining simple math
            if DiceParser.SIMPLE_MATH.match(processed):
                try:
                    # Safe evaluation of simple arithmetic
                    total = eval(processed, {"__builtins__": {}}, {})
                    description = " + ".join(details) if details else processed
                    return int(total), description
                except Exception as e:
                    error_handler.handle_error(GameError(
                        f"Error evaluating processed expression '{processed}': {str(e)}",
                        ErrorSeverity.HIGH,
                        {"original": expression, "processed": processed},
                        e
                    ))
                    raise ValueError(f"Invalid expression: {e}")
            else:
                error_handler.handle_error(GameError(
                    f"Unsafe expression detected: {expression}",
                    ErrorSeverity.HIGH,
                    {"expression": expression, "processed": processed}
                ))
                raise ValueError(f"Unsafe expression: {expression}")
                
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            error_handler.handle_error(GameError(
                f"Unexpected error parsing dice expression '{expression}': {str(e)}",
                ErrorSeverity.CRITICAL,
                {"expression": expression},
                e
            ))
            raise ValueError(f"Unexpected error: {e}")
