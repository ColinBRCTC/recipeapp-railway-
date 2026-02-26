"""
file_helpers.py – File I/O helper functions for Recipe Finder & Meal Planner
Implements: Files, Functions, Lists (arrays)
"""

import json
import os

from models import MealPlan, Recipe

# Anchor all paths to the directory containing this file so they resolve
# correctly regardless of what directory the server is started from.
_ROOT          = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(_ROOT, "data")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")
MEAL_PLAN_FILE = os.path.join(DATA_DIR, "meal_plan.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_favorites() -> list:
    """Read favorites.json → list of Recipe objects. Returns [] if missing."""
    favorites_list = []
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        for recipe_dict in raw_data:        # loop over stored dicts
            favorites_list.append(Recipe.from_dict(recipe_dict))
    return favorites_list


def save_favorites(favorites_list: list) -> None:
    """Serialize a list of Recipe objects and write to favorites.json."""
    _ensure_data_dir()
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in favorites_list], f, indent=2, ensure_ascii=False)


def add_favorite(new_recipe: Recipe) -> bool:
    """Add a recipe to favorites if not already saved. Returns True if added."""
    current = load_favorites()
    for saved in current:                   # loop + if: duplicate check
        if saved.id == new_recipe.id:
            return False
    current.append(new_recipe)
    save_favorites(current)
    return True


def remove_favorite(meal_id: str) -> None:
    """Remove a recipe by ID and rewrite the file."""
    updated = [r for r in load_favorites() if r.id != meal_id]
    save_favorites(updated)


def load_meal_plan() -> MealPlan:
    """Load meal_plan.json → MealPlan object. Returns blank plan if missing."""
    if os.path.exists(MEAL_PLAN_FILE):
        with open(MEAL_PLAN_FILE, "r", encoding="utf-8") as f:
            return MealPlan.from_dict(json.load(f))
    return MealPlan()


def save_meal_plan(meal_plan: MealPlan) -> None:
    _ensure_data_dir()
    with open(MEAL_PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(meal_plan.to_dict(), f, indent=2, ensure_ascii=False)


def clear_meal_plan() -> None:
    save_meal_plan(MealPlan())
