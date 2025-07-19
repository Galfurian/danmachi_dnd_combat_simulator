#!/usr/bin/env python3
"""
Test script to verify category-based default targeting works.
"""

import sys
import os
from pathlib import Path

# Add the simulator directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'simulator'))

def test_category_based_targeting():
    """Test that category-based default targeting works correctly."""
    
    # Just create mock character objects for testing
    class MockCharacter:
        def __init__(self, name, char_type):
            self.name = name
            self.type = char_type
            self.hp = 50
            self.HP_MAX = 100
            
        def is_alive(self):
            return self.hp > 0
    
    from entities.character import CharacterType
    from actions.base_action import BaseAction
    from core.constants import ActionType, ActionCategory
    
    # Create test characters
    player = MockCharacter("TestPlayer", CharacterType.PLAYER)
    ally = MockCharacter("TestAlly", CharacterType.ALLY) 
    enemy = MockCharacter("TestEnemy", CharacterType.ENEMY)
    
    print("=== Testing Category-Based Default Targeting ===")
    print(f"Player: {player.name} ({player.type}) HP: {player.hp}/{player.HP_MAX}")
    print(f"Ally: {ally.name} ({ally.type}) HP: {ally.hp}/{ally.HP_MAX}")  
    print(f"Enemy: {enemy.name} ({enemy.type}) HP: {enemy.hp}/{enemy.HP_MAX}")
    print()
    
    # Test different action categories (no target_restrictions defined)
    test_actions = [
        ("Sword Attack", ActionCategory.OFFENSIVE, ["ENEMY"]),
        ("Healing Potion", ActionCategory.HEALING, ["SELF", "ALLY"]),  
        ("Blessing", ActionCategory.BUFF, ["SELF", "ALLY"]),
        ("Curse", ActionCategory.DEBUFF, ["ENEMY"]),
        ("Identify", ActionCategory.UTILITY, ["ANY"]),
        ("Debug Info", ActionCategory.DEBUG, ["ANY"])
    ]
    
    for action_name, category, expected_targets in test_actions:
        # Create action with no target_restrictions (should use category-based defaults)
        action = BaseAction(
            name=action_name,
            type=ActionType.STANDARD,
            category=category,
            description=f"Test {category.name} action",
            # No target_restrictions specified - should use category defaults
        )
        
        print(f"🎯 Testing {action_name} ({category.name})")
        
        # Test targeting
        can_target_self = action.is_valid_target(player, player)
        can_target_ally = action.is_valid_target(player, ally)
        can_target_enemy = action.is_valid_target(player, enemy)
        
        should_target_self = "SELF" in expected_targets or "ANY" in expected_targets
        should_target_ally = "ALLY" in expected_targets or "ANY" in expected_targets  
        should_target_enemy = "ENEMY" in expected_targets or "ANY" in expected_targets
        
        print(f"  Player -> Player: {can_target_self} (expected: {should_target_self})")
        print(f"  Player -> Ally: {can_target_ally} (expected: {should_target_ally})")
        print(f"  Player -> Enemy: {can_target_enemy} (expected: {should_target_enemy})")
        
        # Verify results
        success = (can_target_self == should_target_self and 
                  can_target_ally == should_target_ally and 
                  can_target_enemy == should_target_enemy)
        print(f"  Result: {'✅ PASS' if success else '❌ FAIL'}")
        print()
    
    print("=== Testing Healing Special Case (Full Health) ===")
    # Test healing when target is at full health
    full_health_ally = MockCharacter("FullHealthAlly", CharacterType.ALLY)
    full_health_ally.hp = full_health_ally.HP_MAX  # At full health
    
    healing_action = BaseAction(
        name="Heal Spell",
        type=ActionType.STANDARD,
        category=ActionCategory.HEALING
    )
    
    can_heal_injured = healing_action.is_valid_target(player, ally)  # HP: 50/100
    can_heal_full = healing_action.is_valid_target(player, full_health_ally)  # HP: 100/100
    
    print(f"🏥 Heal injured ally (50/100 HP): {can_heal_injured} (expected: True)")
    print(f"🏥 Heal full health ally (100/100 HP): {can_heal_full} (expected: False)")
    
    healing_success = can_heal_injured and not can_heal_full
    print(f"  Result: {'✅ PASS' if healing_success else '❌ FAIL'}")

if __name__ == "__main__":
    test_category_based_targeting()
