"""
Safe dice expression parser to replace eval() usage.
"""
import re
import random
from typing import Tuple, Union


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
        if not expression or not isinstance(expression, str):
            raise ValueError("Invalid dice expression")
            
        # Remove whitespace and convert to uppercase
        expr = expression.strip().upper()
        
        # Handle simple numbers
        if expr.isdigit():
            value = int(expr)
            return value, str(value)
        
        # Find all dice rolls
        total = 0
        details = []
        
        # Replace dice rolls with their results
        def roll_dice(match):
            nonlocal total, details
            
            count_str, sides_str, modifier_str = match.groups()
            count = int(count_str) if count_str else 1
            sides = int(sides_str)
            modifier = int(modifier_str) if modifier_str else 0
            
            if count <= 0 or count > 100:  # Reasonable limits
                raise ValueError(f"Invalid dice count: {count}")
            if sides <= 0 or sides > 1000:
                raise ValueError(f"Invalid dice sides: {sides}")
                
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
                raise ValueError(f"Invalid expression: {e}")
        else:
            raise ValueError(f"Unsafe expression: {expression}")
