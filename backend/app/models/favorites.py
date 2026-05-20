from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FavoriteRecipe(Base):
    __tablename__ = "favorite_recipes"

    user_preferences_id: Mapped[int] = mapped_column(ForeignKey("user_preferences.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    frequency_weight: Mapped[int] = mapped_column(Integer, default=1)

    recipe: Mapped["Recipe"] = relationship("Recipe")

    def __repr__(self) -> str:
        return f"<FavoriteRecipe recipe={self.recipe_id} weight={self.frequency_weight}>"
