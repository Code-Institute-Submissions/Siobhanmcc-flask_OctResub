import os
from flask import (
    Flask, flash, render_template, abort,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    recipes = list(mongo.db.recipes.find())
    return render_template("recipes.html", recipes=recipes)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipes=recipes)


@app.route("/register", methods=["GET", "POST"])
def register():

    if is_authenticated():
        return redirect(url_for("profile", username=session["user"])) 
        
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if is_authenticated():
        return redirect(url_for("profile", username=session["user"])) 

    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")))
                return redirect(url_for(
                    "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if is_authenticated():
        username = mongo.db.users.find_one_or_404(
            {"username": session["user"]})["username"]
        return render_template("profile.html", username=username)
    else:
        flash('You are currently not logged in')
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # If not user in session Redirect to home page
    if not is_authenticated():
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    # remove user from session cookies
    flash("You have been logged out")
    session.pop('user')

    return redirect(url_for('login'))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_task():

    if not is_authenticated():
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if request.method == "POST":
        is_urgent = "on" if request.form.get("is_urgent") else "off"
        recipe = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "is_urgent": is_urgent,
            "due_date": request.form.get("due_date"),
            "created_by": session["user"]
        }
        mongo.db.tasks.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):

    if not is_authenticated():
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if not is_object_id_valid(recipe_id):
        abort(404)

    task = mongo.db.recipes.find_one_or_404({"_id": ObjectId(recipe_id)})

    if request.method == "POST":
        is_urgent = "on" if request.form.get("is_urgent") else "off"
        submit = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "is_urgent": is_urgent,
            "due_date": request.form.get("due_date"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Successfully Updated")
        return render_template(url_for("get_recipe"))
        
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("edit_recipe.html", recipe=recipe, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):

    if not is_authenticated():
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if not is_object_id_valid(task_id):
        abort(404)

    mongo.db.recipes.find_one_or_404({"_id": ObjectId(recipe_id)})
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


@app.route("/get_categories")
def get_categories():

    if not is_authenticated() or session['user'] != 'admin':
        flash("You are currently not logged in")
        return redirect(url_for('login'))
    
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route("/add_category", methods=["GET", "POST"])
def add_category():

    if not is_authenticated() or session['user'] != 'admin':
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New Category Added")
        return redirect(url_for("get_categories"))

    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):

    if not is_authenticated() or session['user'] != 'admin':
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if not is_object_id_valid(category_id):
        abort(404)

    category = mongo.db.categories.find_one_or_404({"_id": ObjectId(category_id)})

    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name")
        }
        
        mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
        flash("Category Successfully Updated")
        return redirect(url_for("get_categories"))

    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):

    if not is_authenticated() or session['user'] != 'admin':
        flash("You are currently not logged in")
        return redirect(url_for('login'))

    if not is_object_id_valid(category_id):
        abort(404)

    mongo.db.categories.find_one_or_404({"_id": ObjectId(category_id)})
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully Deleted")
    return redirect(url_for("get_categories"))


def is_authenticated():
    """ Ensure that user is authenticated
    """
    return 'user' in session


def is_admin():
    return is_authenticated() and session['user'] == 'admin'


def is_object_id_valid(id_value):
    """ Validate is the id_value is a valid ObjectId
    """
    return id_value != "" and ObjectId.is_valid(id_value)


#Custom Error Handling
# 404 Error Page not found
@app.errorhandler(404)
def page_not_found(error):
  return render_template('404.html'), 404


# # 500 Error Server Error
@app.errorhandler(500)
def internal_server(error):
 return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)

