import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
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
#db = SQL("sqlite:///finance.db")
db = SQL("postgres://mnrnqmemyohmdx:17f49cbc1785cffe01be5b6b22abc3b7dbb2491c702b66e22c7b3265f81a3804@ec2-35-175-155-248.compute-1.amazonaws.com:5432/devicaoccbv6cj")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # making a query in the database and saving it in a python variable
    # get the cash available for the current user
    users = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id = session["user_id"])
    # query the database for stock symbol, total shares and price per share from transaction table for the current user
    summary = db.execute("SELECT symbol, SUM(shares) as total_shares, price_per_share FROM transactions WHERE user_id = :user_id GROUP BY symbol", user_id = session["user_id"])

    quotes = {}
    total_value = 0

    for stock in summary:
        quotes[stock["symbol"]] = lookup(stock["symbol"])
        total_value += lookup(stock["symbol"])["price"] * stock["total_shares"]

    cash_remaining = users[0]["cash"]

    return render_template("index.html", quotes=quotes, summary=summary, total_value=total_value, cash_remaining=cash_remaining)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # look up stock name
        stock = lookup(request.form.get("symbol"))
        if stock == None:
            return apology("invalid stock abbreviation", 403)
        # get number of shares user wants to buy
        shares = int(request.form.get("shares"))
        # check if shares is a positive integer
        if shares <= 0:
            return apology("please provide the number of shares to buy (minimum is 1 share)")
        # get cash available for the current user
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
        cash_available = rows[0]["cash"]
        price_per_share = stock["price"]
        total_price = (price_per_share * shares)
        # check if the user has enough cash to complete the purchase
        if cash_available < total_price:
            return apology("Not enough cash to purchase stock", 403)
        else:
            # update the cash for the current user
            db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id", price = total_price, user_id = session["user_id"])

            db.execute("INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES(:user_id, :stock_bought, :shares, :price)",
                   user_id=session["user_id"],
                   stock_bought=request.form.get("symbol"),
                   shares=shares,
                   price=price_per_share)

            flash("Bought!")

            return redirect(url_for("index"))
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT symbol, shares, price_per_share, created_at FROM transactions WHERE user_id = :user_id ORDER BY created_at ASC", user_id=session["user_id"])

    return render_template("history.html", transactions=transactions)


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
        # Check if password matches
        elif request.form.get("password_confirmation") != request.form.get("password"):
            return apology("password didn't match",403)
        # Query database to check if username is already in use
        rows = db.execute("SELECT * FROM users WHERE username= :username", username=request.form.get("username"))
        if len(rows) != 0:
                return apology("username already in use",403)
        # insert username and password into database
        hash = generate_password_hash(request.form.get("password"))
        new_id = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = request.form.get("username"), hash = hash)
        # check if the username already exist
        session["user_id"] = new_id

        return redirect("/")

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "GET":
        return render_template("change_password.html")
    else:
        if not request.form.get("old_password"):
            return apology("please provide the old password",403)
        # if no password is provided
        elif not request.form.get("new_password"):
            return apology("please provide a new password", 403)
        elif not request.form.get("new_password_confirmation"):
            return apology("must provide password again", 403)
        # check if password entered matches
        elif request.form.get("new_password_confirmation") != request.form.get("new_password"):
            return apology("New password didn't match",403)
        # Query database to check if old password is entered correctly
        rows = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("old_password")):
            return apology("Wrong old password entered")
        # Update old password with new one
        else:
            hash = generate_password_hash(request.form.get("new_password"))
            db.execute("UPDATE users SET hash = :hash WHERE id = :user_id", hash = hash, user_id=session["user_id"])

        # Prompt user update is successful
            flash("Password Updated!")
            return redirect(url_for("index"))

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # if user fails to select a stock to sell
        if not request.form.get("symbol"):
            return apology("Please select a stock")
        # if user fails to select the number of shares to sell
        if not request.form.get("shares"):
            return apology("Please select how many shares to sell")

        shares = int(request.form.get("shares"))
        if shares <= 0:
            return apology("Cannot sell less than or 0 shares")
        # Query database for the number of shares the users owns
        stock = db.execute("SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id AND symbol = :symbol GROUP BY symbol",
                           user_id=session["user_id"], symbol=request.form.get("symbol"))
        if stock[0]["total_shares"] <= 0 or stock[0]["total_shares"] < shares:
            return apology("not enough shares to sell")

        stock = lookup(request.form.get("symbol"))
        # query database for the current user
        rows = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id = session["user_id"])
        # get the cash remaining and pass it into index.html for calculation , the problem is the cash remaining is not kept as record in the database, fix it??
        cash_remaining = rows[0]["cash"]
        price_per_share = stock["price"]
        # Calculate the price of requested shares
        total_price = price_per_share * shares

        # Book keeping (TODO: should be wrapped with a transaction)
        db.execute("UPDATE users SET cash = cash + :price WHERE id = :user_id", price=total_price, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price_per_share) VALUES(:user_id, :symbol, :shares, :price)",
                   user_id=session["user_id"],
                   symbol=request.form.get("symbol"),
                   shares= (-shares),
                   price=price_per_share)

        flash("Sold!")

        return redirect(url_for("index"))

    else:
        summary = db.execute("SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = :user_id GROUP BY symbol HAVING total_shares > 0", user_id=session["user_id"])

        return render_template("sell.html", summary=summary)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
