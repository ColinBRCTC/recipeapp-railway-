"""
app.py – Recipe Finder & Meal Planner (with user authentication)
Flask web application using TheMealDB free API + Flask-Login.
Implements: if statements, loops, lists, files, functions, classes/inheritance

Author: [Your Name]
Course: [Course Name]
"""

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user,
)

from models import Recipe, MealPlan
from file_helpers import (
    get_user_by_id, get_user_by_username, register_user,
    load_favorites, add_favorite, remove_favorite,
    load_meal_plan, save_meal_plan, clear_meal_plan,
)

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION SETUP
# ─────────────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_ROOT, "templates"))
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

# ── Flask-Login setup ─────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view       = "login"          # redirect here if not logged in
login_manager.login_message    = "Please log in to access that page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login calls this to reload the user from the session cookie."""
    return get_user_by_id(user_id)


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
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    """Show registration form (GET) or create a new account (POST)."""
    # If already logged in, send straight to home
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        # Validate passwords match (if statement)
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        user, error = register_user(username, password)

        if error:
            flash(error, "danger")
            return render_template("register.html")

        # Auto-login after successful registration
        login_user(user)
        flash(f"Welcome, {user.username}! Your account has been created.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Show login form (GET) or authenticate the user (POST)."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = get_user_by_username(username)

        # If user not found or password wrong, show generic error (if statement)
        if user is None or not user.check_password(password):
            flash("Incorrect username or password.", "danger")
            return render_template("login.html")

        login_user(user, remember=True)
        flash(f"Welcome back, {user.username}!", "success")

        # Redirect to the page they were trying to visit, or home
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Log the user out and redirect to login page."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTES  (all protected with @login_required)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/search")
@login_required
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
@login_required
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
@login_required
def recipe_detail(meal_id):
    recipe = fetch_meal_by_id(meal_id)
    if recipe is None:
        flash("Recipe not found.", "warning")
        return redirect(url_for("index"))
    # Check against THIS user's favorites only
    favorites   = load_favorites(current_user.id)
    is_favorite = any(fav.id == meal_id for fav in favorites)
    return render_template("detail.html", recipe=recipe, is_favorite=is_favorite)


@app.route("/favorites")
@login_required
def favorites():
    # Load only the current user's favorites
    return render_template("favorites.html", favorites=load_favorites(current_user.id))


@app.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    meal_id = request.form.get("meal_id", "").strip()
    if not meal_id:
        flash("Invalid recipe ID.", "danger")
        return redirect(url_for("index"))
    recipe = fetch_meal_by_id(meal_id)
    if recipe is None:
        flash("Could not retrieve recipe details.", "danger")
        return redirect(url_for("index"))
    if add_favorite(current_user.id, recipe):
        flash(f'"{recipe.name}" saved to your favorites!', "success")
    else:
        flash(f'"{recipe.name}" is already in your favorites.', "info")
    return redirect(url_for("recipe_detail", meal_id=meal_id))


@app.route("/favorites/remove/<meal_id>", methods=["POST"])
@login_required
def favorites_remove(meal_id):
    remove_favorite(current_user.id, meal_id)
    flash("Recipe removed from favorites.", "info")
    return redirect(url_for("favorites"))


@app.route("/mealplan")
@login_required
def meal_plan():
    return render_template("mealplan.html",
                           plan=load_meal_plan(current_user.id),
                           favorites=load_favorites(current_user.id))


@app.route("/mealplan/assign", methods=["POST"])
@login_required
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
    plan = load_meal_plan(current_user.id)
    if plan.assign_meal(day_name, recipe):
        save_meal_plan(current_user.id, plan)
        flash(f'"{recipe.name}" assigned to {day_name}!', "success")
    else:
        flash(f'"{day_name}" is not a valid day.', "danger")
    return redirect(url_for("meal_plan"))


@app.route("/mealplan/remove/<day_name>", methods=["POST"])
@login_required
def meal_plan_remove(day_name):
    plan = load_meal_plan(current_user.id)
    plan.remove_meal(day_name)
    save_meal_plan(current_user.id, plan)
    flash(f"{day_name} cleared from your meal plan.", "info")
    return redirect(url_for("meal_plan"))


@app.route("/mealplan/clear", methods=["POST"])
@login_required
def meal_plan_clear():
    clear_meal_plan(current_user.id)
    flash("Meal plan cleared.", "info")
    return redirect(url_for("meal_plan"))


@app.route("/categories")
@login_required
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
@login_required
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
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
