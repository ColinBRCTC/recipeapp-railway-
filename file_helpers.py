"""
file_helpers.py – File I/O helpers for Recipe Finder & Meal Planner
Favorites and meal plans are now stored per-user using the user's ID in the filename.
Implements: Files, Functions, Lists (arrays)
"""

import json
import os
import uuid

from models import MealPlan, Recipe, User

_ROOT    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_ROOT, "data")

# Shared user registry
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ── Per-user file paths ───────────────────────────────────────────────────────

def _favorites_file(user_id: str) -> str:
    """Each user gets their own favorites_<user_id>.json file."""
    return os.path.join(DATA_DIR, f"favorites_{user_id}.json")


def _meal_plan_file(user_id: str) -> str:
    """Each user gets their own meal_plan_<user_id>.json file."""
    return os.path.join(DATA_DIR, f"meal_plan_{user_id}.json")


# ── User account helpers ──────────────────────────────────────────────────────

def load_all_users() -> dict:
    """
    Load the users registry.
    Returns a dict of { username_lowercase: User }.
    """
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Loop over stored dicts and rebuild User objects
    users = {}
    for user_dict in raw:
        user = User.from_dict(user_dict)
        users[user.username.lower()] = user
    return users


def _save_all_users(users: dict) -> None:
    """Write the full user registry back to disk."""
    _ensure_data_dir()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([u.to_dict() for u in users.values()], f, indent=2)


def get_user_by_id(user_id: str):
    """Find a User by their unique ID. Returns None if not found."""
    all_users = load_all_users()
    for user in all_users.values():         # loop over all users
        if user.id == user_id:
            return user
    return None


def get_user_by_username(username: str):
    """Find a User by username (case-insensitive). Returns None if not found."""
    all_users = load_all_users()
    return all_users.get(username.lower())  # if key absent → None


def register_user(username: str, password: str):
    """
    Create a new user account.
    Returns (User, None) on success, or (None, error_message) on failure.
    """
    # Validate username length
    if len(username) < 3:
        return None, "Username must be at least 3 characters."
    if len(username) > 30:
        return None, "Username must be 30 characters or fewer."

    # Validate password length
    if len(password) < 6:
        return None, "Password must be at least 6 characters."

    all_users = load_all_users()

    # Check for duplicate username (if statement)
    if username.lower() in all_users:
        return None, "That username is already taken. Please choose another."

    # Create the new user with a unique ID
    new_user = User.create(
        user_id=str(uuid.uuid4()),
        username=username,
        password=password,
    )
    all_users[username.lower()] = new_user
    _save_all_users(all_users)
    return new_user, None


# ── Favorites helpers (per-user) ──────────────────────────────────────────────

def load_favorites(user_id: str) -> list:
    """Load this user's saved recipes. Returns [] if none saved yet."""
    path = _favorites_file(user_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Recipe.from_dict(d) for d in raw]      # loop + list


def save_favorites(user_id: str, favorites_list: list) -> None:
    """Write this user's favorites list to their personal file."""
    _ensure_data_dir()
    with open(_favorites_file(user_id), "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in favorites_list], f, indent=2, ensure_ascii=False)


def add_favorite(user_id: str, new_recipe: Recipe) -> bool:
    """
    Add a recipe to this user's favorites if not already saved.
    Returns True if added, False if duplicate.
    """
    current = load_favorites(user_id)
    for saved in current:                           # loop + if: duplicate check
        if saved.id == new_recipe.id:
            return False
    current.append(new_recipe)
    save_favorites(user_id, current)
    return True


def remove_favorite(user_id: str, meal_id: str) -> None:
    """Remove one recipe from this user's favorites."""
    updated = [r for r in load_favorites(user_id) if r.id != meal_id]
    save_favorites(user_id, updated)


# ── Meal plan helpers (per-user) ──────────────────────────────────────────────

def load_meal_plan(user_id: str) -> MealPlan:
    """Load this user's meal plan. Returns an empty plan if none exists."""
    path = _meal_plan_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return MealPlan.from_dict(json.load(f))
    return MealPlan()


def save_meal_plan(user_id: str, meal_plan: MealPlan) -> None:
    """Write this user's meal plan to their personal file."""
    _ensure_data_dir()
    with open(_meal_plan_file(user_id), "w", encoding="utf-8") as f:
        json.dump(meal_plan.to_dict(), f, indent=2, ensure_ascii=False)


def clear_meal_plan(user_id: str) -> None:
    """Reset this user's meal plan to empty."""
    save_meal_plan(user_id, MealPlan())
