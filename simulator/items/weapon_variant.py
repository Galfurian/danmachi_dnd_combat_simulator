from typing import Any, Dict, List
from items.weapon import Weapon
from actions.attack_action import BaseAttack
from combat.damage import DamageComponent, DamageType
from effects.effect import Effect
import copy


def create_weapon_variant(base_weapon: Weapon, variant_data: dict) -> Weapon:
    """Create a weapon variant by deep copying the base weapon and applying modifications.
    
    Args:
        base_weapon (Weapon): The base weapon to modify
        variant_data (dict): Dictionary containing variant modifications
        
    Returns:
        Weapon: A new weapon with applied modifications
    """
    # Deep copy the base weapon to avoid modifying the original
    variant_weapon = copy.deepcopy(base_weapon)
    
    # Apply basic modifications
    if "name" in variant_data:
        variant_weapon.name = variant_data["name"]
    
    if "description" in variant_data:
        variant_weapon.description = variant_data["description"]
    
    # Apply attack modifications
    if "attacks" in variant_data:
        for attack_name, attack_mods in variant_data["attacks"].items():
            # Find the attack to modify (checking both original name and prefixed name)
            for attack in variant_weapon.attacks:
                attack_base_name = attack.name.split(" - ")[-1] if " - " in attack.name else attack.name
                if attack_base_name == attack_name:
                    _apply_attack_modifications(attack, attack_mods)
                    break
    
    # Update attack names to match the new weapon name
    for attack in variant_weapon.attacks:
        attack_base_name = attack.name.split(" - ")[-1] if " - " in attack.name else attack.name
        attack.name = f"{variant_weapon.name} - {attack_base_name}"
    
    return variant_weapon


def load_weapon_variants(variants_file: str, base_weapons: Dict[str, Weapon]) -> Dict[str, Weapon]:
    """Load weapon variants from a JSON file and create variant weapons.
    
    Args:
        variants_file (str): Path to the variants JSON file
        base_weapons (Dict[str, Weapon]): Dictionary of base weapons
        
    Returns:
        Dict[str, Weapon]: Dictionary of variant weapons
    """
    import json
    
    with open(variants_file, 'r') as f:
        variants_data = json.load(f)
    
    variant_weapons = {}
    
    for variant_data in variants_data:
        base_weapon_name = variant_data["base_weapon"]
        if base_weapon_name not in base_weapons:
            print(f"Warning: Base weapon '{base_weapon_name}' not found for variant '{variant_data['name']}'")
            continue
        
        base_weapon = base_weapons[base_weapon_name]
        variant_weapon = create_weapon_variant(base_weapon, variant_data)
        variant_weapons[variant_weapon.name] = variant_weapon
    
    return variant_weapons


def _apply_attack_modifications(attack: BaseAttack, modifications: dict):
    """Apply modifications to a specific attack."""
    if "damage" in modifications:
        # Replace damage components
        new_damage = []
        for damage_data in modifications["damage"]:
            damage_component = DamageComponent(
                damage_roll=damage_data["damage_roll"],
                damage_type=DamageType[damage_data["damage_type"]]
            )
            new_damage.append(damage_component)
        attack.damage = new_damage
    
    if "attack_roll" in modifications:
        attack.attack_roll = modifications["attack_roll"]
    
    if "cooldown" in modifications:
        attack.cooldown = modifications["cooldown"]
    
    if "description" in modifications:
        attack.description = modifications["description"]
    
    # Handle effects if provided
    if "effect" in modifications:
        effect_data = modifications["effect"]
        if effect_data is not None:
            attack.effect = Effect.from_dict(effect_data)
        else:
            attack.effect = None
