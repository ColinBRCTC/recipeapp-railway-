"""
models.py – Data model classes for the Recipe Finder & Meal Planner
Implements: Objects, Classes, Inheritance, Methods
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class DataModel:
    """Base class: shared serialization for all data records."""

    def __init__(self, record_id: str):
        self.id = record_id

    def to_dict(self) -> dict:
        return {"id": self.id}

    @classmethod
    def from_dict(cls, data: dict) -> "DataModel":
        return cls(record_id=data["id"])


# ─────────────────────────────────────────────────────────────────────────────
# USER  (inherits DataModel + Flask-Login's UserMixin)
# UserMixin provides the 4 properties Flask-Login requires:
#   is_authenticated, is_active, is_anonymous, get_id()
# ─────────────────────────────────────────────────────────────────────────────
class User(UserMixin, DataModel):
    """A registered user account."""

    def __init__(self, user_id: str, username: str, password_hash: str):
        super().__init__(record_id=user_id)
        self.username      = username
        self.password_hash = password_hash

    def get_id(self) -> str:
        """Flask-Login uses this to store the user ID in the session."""
        return self.id

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data["id"],
            username=data["username"],
            password_hash=data["password_hash"],
        )

    @staticmethod
    def create(user_id: str, username: str, password: str) -> "User":
        """Create a new User with a securely hashed password."""
        return User(
            user_id=user_id,
            username=username,
            password_hash=generate_password_hash(password),
        )


# ─────────────────────────────────────────────────────────────────────────────
# RECIPE  (inherits DataModel)
# ─────────────────────────────────────────────────────────────────────────────
class Recipe(DataModel):
    """A single recipe. Inherits DataModel for serialization."""

    def __init__(self, record_id, name, category, area,
                 instructions, thumbnail_url, ingredients, youtube_url=""):
        super().__init__(record_id)
        self.name          = name
        self.category      = category
        self.area          = area
        self.instructions  = instructions
        self.thumbnail_url = thumbnail_url
        self.ingredients   = ingredients
        self.youtube_url   = youtube_url

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "area": self.area, "instructions": self.instructions,
            "thumbnail_url": self.thumbnail_url, "ingredients": self.ingredients,
            "youtube_url": self.youtube_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Recipe":
        return cls(
            record_id=data.get("id", ""), name=data.get("name", ""),
            category=data.get("category", ""), area=data.get("area", ""),
            instructions=data.get("instructions", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            ingredients=data.get("ingredients", []),
            youtube_url=data.get("youtube_url", ""),
        )

    @classmethod
    def from_api(cls, meal: dict) -> "Recipe":
        ingredients = []
        for counter in range(1, 21):
            ingredient = meal.get(f"strIngredient{counter}", "") or ""
            measure    = meal.get(f"strMeasure{counter}", "") or ""
            if ingredient.strip():
                ingredients.append(f"{measure.strip()} {ingredient.strip()}".strip())
        return cls(
            record_id=meal.get("idMeal", ""), name=meal.get("strMeal", ""),
            category=meal.get("strCategory", ""), area=meal.get("strArea", ""),
            instructions=meal.get("strInstructions", ""),
            thumbnail_url=meal.get("strMealThumb", ""),
            ingredients=ingredients, youtube_url=meal.get("strYoutube", ""),
        )

    def get_instructions_steps(self) -> list:
        return [s.strip() for s in (self.instructions or "").splitlines() if s.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# MEALPLAN  (inherits DataModel)
# ─────────────────────────────────────────────────────────────────────────────
class MealPlan(DataModel):
    """A 7-day meal plan tied to one user."""

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]

    def __init__(self):
        super().__init__(record_id="weekly_plan")
        self.plan = {day: None for day in self.DAYS}

    def assign_meal(self, day_name: str, recipe: Recipe) -> bool:
        if day_name in self.plan:
            self.plan[day_name] = recipe
            return True
        return False

    def remove_meal(self, day_name: str) -> bool:
        if day_name in self.plan:
            self.plan[day_name] = None
            return True
        return False

    def to_dict(self) -> dict:
        serialized = {}
        for day, recipe in self.plan.items():
            serialized[day] = recipe.to_dict() if recipe is not None else None
        return {"id": self.id, "plan": serialized}

    @classmethod
    def from_dict(cls, data: dict) -> "MealPlan":
        meal_plan = cls()
        for day, recipe_data in data.get("plan", {}).items():
            if recipe_data is not None:
                meal_plan.plan[day] = Recipe.from_dict(recipe_data)
        return meal_plan
