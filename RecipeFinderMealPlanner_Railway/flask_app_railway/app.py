"""
app.py – Recipe Finder & Meal Planner
Flask web application using TheMealDB free API.
Implements: if statements, loops, lists, files, functions, classes/inheritance

Author: [Your Name]
Course: [Course Name]
"""

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash

from models import Recipe, MealPlan
from file_helpers import (
    load_favorites, add_favorite, remove_favorite,
    load_meal_plan, save_meal_plan, clear_meal_plan,
)

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION SETUP
# ─────────────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(_ROOT, "templates"),
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────
def fetch_meal_by_id(meal_id: str):
    """Fetch full recipe details from TheMealDB. Returns Recipe or None."""
    try:
        resp  = requests.get(f"{MEALDB_BASE}/lookup.php?i={meal_id}", timeout=10)
        meals = resp.json().get("meals")
        if not meals:
            return None
        return Recipe.from_api(meals[0])
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query          = request.args.get("q", "").strip()
    recipe_objects = []
    message        = ""

    if not query:
        message = "Please enter a search term."
        return render_template("results.html", recipes=recipe_objects,
                               message=message, query=query)
    try:
        resp      = requests.get(f"{MEALDB_BASE}/search.php?s={query}", timeout=10)
        raw_meals = resp.json().get("meals")
    except Exception:
        raw_meals = None

    if raw_meals is None:
        message = f'No recipes found for "{query}". Try a different term!'
    else:
        for meal_dict in raw_meals:
            recipe_objects.append(Recipe.from_api(meal_dict))

    return render_template("results.html", recipes=recipe_objects,
                           message=message, query=query)


@app.route("/search/ingredient")
def search_by_ingredient():
    ingredient     = request.args.get("i", "").strip()
    recipe_objects = []
    message        = ""

    if not ingredient:
        message = "Please enter an ingredient."
        return render_template("results.html", recipes=recipe_objects,
                               message=message, query=ingredient)
    try:
        resp      = requests.get(f"{MEALDB_BASE}/filter.php?i={ingredient}", timeout=10)
        raw_meals = resp.json().get("meals")
    except Exception:
        raw_meals = None

    if raw_meals is None:
        message = f'No recipes found containing "{ingredient}".'
    else:
        for meal_dict in raw_meals:
            recipe_objects.append(Recipe(
                record_id=meal_dict.get("idMeal", ""),
                name=meal_dict.get("strMeal", ""),
                category="", area="", instructions="",
                thumbnail_url=meal_dict.get("strMealThumb", ""),
                ingredients=[],
            ))

    return render_template("results.html", recipes=recipe_objects,
                           message=message, query=ingredient)


@app.route("/recipe/<meal_id>")
def recipe_detail(meal_id):
    recipe = fetch_meal_by_id(meal_id)
    if recipe is None:
        flash("Recipe not found.", "warning")
        return redirect(url_for("index"))
    favorites   = load_favorites()
    is_favorite = any(fav.id == meal_id for fav in favorites)
    return render_template("detail.html", recipe=recipe, is_favorite=is_favorite)


@app.route("/favorites")
def favorites():
    return render_template("favorites.html", favorites=load_favorites())


@app.route("/favorites/add", methods=["POST"])
def favorites_add():
    meal_id = request.form.get("meal_id", "").strip()
    if not meal_id:
        flash("Invalid recipe ID.", "danger")
        return redirect(url_for("index"))
    recipe = fetch_meal_by_id(meal_id)
    if recipe is None:
        flash("Could not retrieve recipe details.", "danger")
        return redirect(url_for("index"))
    if add_favorite(recipe):
        flash(f'"{recipe.name}" saved to favorites!', "success")
    else:
        flash(f'"{recipe.name}" is already in your favorites.', "info")
    return redirect(url_for("recipe_detail", meal_id=meal_id))


@app.route("/favorites/remove/<meal_id>", methods=["POST"])
def favorites_remove(meal_id):
    remove_favorite(meal_id)
    flash("Recipe removed from favorites.", "info")
    return redirect(url_for("favorites"))


@app.route("/mealplan")
def meal_plan():
    return render_template("mealplan.html",
                           plan=load_meal_plan(), favorites=load_favorites())


@app.route("/mealplan/assign", methods=["POST"])
def meal_plan_assign():
    day_name = request.form.get("day", "").strip()
    meal_id  = request.form.get("meal_id", "").strip()
    if not day_name or not meal_id:
        flash("Please select both a day and a recipe.", "warning")
        return redirect(url_for("meal_plan"))
    recipe = fetch_meal_by_id(meal_id)
    if recipe is None:
        flash("Could not load that recipe.", "danger")
        return redirect(url_for("meal_plan"))
    plan = load_meal_plan()
    if plan.assign_meal(day_name, recipe):
        save_meal_plan(plan)
        flash(f'"{recipe.name}" assigned to {day_name}!', "success")
    else:
        flash(f'"{day_name}" is not a valid day.', "danger")
    return redirect(url_for("meal_plan"))


@app.route("/mealplan/remove/<day_name>", methods=["POST"])
def meal_plan_remove(day_name):
    plan = load_meal_plan()
    plan.remove_meal(day_name)
    save_meal_plan(plan)
    flash(f"{day_name} cleared from your meal plan.", "info")
    return redirect(url_for("meal_plan"))


@app.route("/mealplan/clear", methods=["POST"])
def meal_plan_clear():
    clear_meal_plan()
    flash("Meal plan cleared.", "info")
    return redirect(url_for("meal_plan"))


@app.route("/categories")
def categories():
    try:
        resp           = requests.get(f"{MEALDB_BASE}/categories.php", timeout=10)
        all_categories = resp.json().get("categories", [])
    except Exception:
        all_categories = []
    category_list = [
        {"name": c.get("strCategory", ""),
         "thumbnail": c.get("strCategoryThumb", ""),
         "description": c.get("strCategoryDescription", "")}
        for c in all_categories
    ]
    return render_template("categories.html", categories=category_list)


@app.route("/category/<category_name>")
def category_meals(category_name):
    try:
        resp      = requests.get(f"{MEALDB_BASE}/filter.php?c={category_name}", timeout=10)
        raw_meals = resp.json().get("meals")
    except Exception:
        raw_meals = None

    recipe_objects = []
    if raw_meals:
        for meal_dict in raw_meals:
            recipe_objects.append(Recipe(
                record_id=meal_dict.get("idMeal", ""),
                name=meal_dict.get("strMeal", ""),
                category=category_name, area="", instructions="",
                thumbnail_url=meal_dict.get("strMealThumb", ""),
                ingredients=[],
            ))
    message = "" if recipe_objects else f'No meals found in "{category_name}".'
    return render_template("results.html", recipes=recipe_objects,
                           message=message, query=category_name)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# Railway injects PORT as an environment variable — we must bind to it.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
