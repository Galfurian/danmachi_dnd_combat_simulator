#!/usr/bin/env python3
"""
Test script to verify the new spell targeting system works correctly.
"""

import sys
import os
from pathlib import Path

# Add the simulator directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'simulator'))

from core.content import ContentRepository

def test_spell_targeting():
    """Test that the new target_restrictions system works properly."""
    
    # Load content repository to get spells
    data_dir = Path(__file__).parent / "data"
    content_repo = ContentRepository(data_dir)
    
    # Just create mock character objects for testing
    class MockCharacter:
        def __init__(self, name, char_type):
            self.name = name
            self.type = char_type
            
        def is_alive(self):
            return True
    
    from entities.character import CharacterType
    
    # Create test characters
    player = MockCharacter("TestPlayer", CharacterType.PLAYER)
    ally = MockCharacter("TestAlly", CharacterType.ALLY) 
    enemy = MockCharacter("TestEnemy", CharacterType.ENEMY)
    
    # Get spells from repository
    shield_of_faith = content_repo.get_spell("Shield of Faith")
    cure_wounds = content_repo.get_spell("Cure Wounds")
    wrathful_smite = content_repo.get_spell("Wrathful Smite")
    divine_favor = content_repo.get_spell("Divine Favor")

    print("=== Testing Spell Targeting System ===")
    print(f"Player: {player.name} ({player.type})")
    print(f"Ally: {ally.name} ({ally.type})")  
    print(f"Enemy: {enemy.name} ({enemy.type})")
    print()
    
    # Test different spells with their target restrictions
    spells_to_test = [
        (shield_of_faith, "Shield of Faith", ["SELF", "ALLY"]),
        (cure_wounds, "Cure Wounds", ["SELF", "ALLY"]),
        (wrathful_smite, "Wrathful Smite", ["ENEMY"]),
        (divine_favor, "Divine Favor", ["SELF"])
    ]
    
    for spell, spell_name, expected_restrictions in spells_to_test:
        if spell is None:
            print(f"❌ Spell '{spell_name}' not found")
            continue
            
        print(f"🔮 Testing {spell_name} (restrictions: {spell.target_restrictions})")
        
        # Test targeting player (should work for SELF spells)
        can_target_self = spell.is_valid_target(player, player)
        should_target_self = "SELF" in expected_restrictions or "ANY" in expected_restrictions
        print(f"  Player -> Player: {can_target_self} (expected: {should_target_self})")
        
        # Test targeting ally (should work for ALLY spells)
        can_target_ally = spell.is_valid_target(player, ally)
        should_target_ally = "ALLY" in expected_restrictions or "ANY" in expected_restrictions
        print(f"  Player -> Ally: {can_target_ally} (expected: {should_target_ally})")
        
        # Test targeting enemy (should work for ENEMY spells)
        can_target_enemy = spell.is_valid_target(player, enemy)
        should_target_enemy = "ENEMY" in expected_restrictions or "ANY" in expected_restrictions
        print(f"  Player -> Enemy: {can_target_enemy} (expected: {should_target_enemy})")
        
        # Verify results
        success = (can_target_self == should_target_self and 
                  can_target_ally == should_target_ally and 
                  can_target_enemy == should_target_enemy)
        print(f"  Result: {'✅ PASS' if success else '❌ FAIL'}")
        print()

if __name__ == "__main__":
    test_spell_targeting()