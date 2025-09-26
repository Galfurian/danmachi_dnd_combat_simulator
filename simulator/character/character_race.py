
from pydantic import BaseModel, Field


class CharacterRace(BaseModel):
    """
    Represents a character's race, including natural AC, default and available
    actions and spells.
    """

    name: str = Field(
        description="The name of the race",
    )
    natural_ac: int = Field(
        default=0,
        description="The natural armor class provided by the race",
    )
    default_actions: list[str] = Field(
        default_factory=list,
        description="Default actions available to the race",
    )
    default_spells: list[str] = Field(
        default_factory=list,
        description="Default spells available to the race",
    )

    def __hash__(self) -> int:
        """
        Hash the character class based on its name.

        Returns:
            int:
                The hash value of the character class.

        """
        return hash(self.name)
