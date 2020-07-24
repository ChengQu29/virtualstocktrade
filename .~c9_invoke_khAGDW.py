import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # making a query in the database and saving it in a python variable
    rows = db.execute("SELECT * FROM registrants")

    if len(rows) !=1:
        return apology("no stocks picked", 403)

    return render_template("index.html", rows=rows)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # look up stock name
        stock = lookup(request.form.get("symbol"))
        if stock == None:
            return apology("invalid stock abbreviation",403)
        # get number of shares user wants to b
        shares = int(request.form.get("shares"))

        if shares <= 0:
            return apology("please provide the number of shares to buy (minimum is 1 share)")


        rows = db.execute("SELECT cash FROM users WHERE username = :username", username = session["user_id"])
        cash_available = rows[0]["cash"]

        if cash_available < (stock["price"] * shares):
            return apology("Not enough cash to purchase stock")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        stock = lookup(request.form.get("symbol"))

        if stock == None:
            return apology("invalid stock abbreviation",403)
        else:
            return render_template("quoted.html", symbol=stock['symbol'], price=usd(stock['price']))

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        # if no name is provided
        if not request.form.get("username"):
            return apology("must provide username")
        # if no password is provided
        elif not request.form.get("password"):
            return apology("must provide a password", 403)
        elif not request.form.get("password_confirmation"):
            return apology("must provide password again", 403)
        # Query database for username
        elif request.form.get("password_confirmation") != request.form.get("password"):
            return apology("password didn't match",403)
        # check if username is already in use
        rows = db.execute("SELECT * FROM users WHERE username= :username", username=request.form.get("username"))
        if len(rows) != 0:
                return apology("username already in use",403)
        # insert username and password into database
        hash = generate_password_hash(request.form.get("password"))
        new_id = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = request.form.get("username"), hash = hash)
        # check if the username already exist
        session["user_id"] = new_id

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
