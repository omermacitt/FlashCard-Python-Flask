## Libraries
import random
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from Forms import LoginForm, RegisterForm, InsertWord
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()
# Flask application and db connections
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

db = SQLAlchemy(app=app)
app.secret_key = os.getenv("SECRET_KEY")


# User Login Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.", "danger")
            return redirect(url_for("sign_in"))
    
    return decorated_function


# English Word DB Class
class EnglishWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    english_word = db.Column(db.String(80), nullable=False)
    turkish_word = db.Column(db.String(80), nullable=False)


# User Class
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    surname = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(255), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=False)
    analysis = db.relationship("Analysis", backref="user", lazy=True)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    process = db.Column(db.String(100), nullable=False)
    main_language = db.Column(db.String(30), nullable=False)
    target_language = db.Column(db.String(30), nullable=False)
    words = db.Column(db.String(255), nullable=False)
    correct_options_count = db.Column(db.Numeric, nullable=False)
    wrong_options_count = db.Column(db.Numeric, nullable=False)
    correct_options = db.Column(db.String(255), nullable=False)
    selected_options = db.Column(db.String(255), nullable=False)
    passing_time = db.Column(db.String(255), nullable=False)
    success_rate = db.Column(db.Float, nullable=False)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=False)
    words_count = db.Column(db.Integer, nullable=False)


def get_random_choices(correct_word, language="English"):
    all_choices = list()
    if language == "English":
        incorrect_words = (
            EnglishWord.query.filter(EnglishWord.turkish_word != correct_word).order_by(db.func.random()).limit(
                3).all()
        )
        all_choices.extend([correct_word] + [word.turkish_word for word in incorrect_words])
        random.shuffle(all_choices)
    elif language == "Turkish":
        incorrect_words = (
            EnglishWord.query.filter(EnglishWord.english_word != correct_word).order_by(db.func.random()).limit(
                3).all()
        )
        all_choices.extend([correct_word] + [word.english_word for word in incorrect_words])
        random.shuffle(all_choices)
    return all_choices


def get_all_data_list(words, language="English"):
    options = []
    correct_words = []
    word_to_guess = []
    if language == "English":
        for word in words:
            choices = get_random_choices(word.turkish_word)
            options.append(choices)
            correct_words.append(word.turkish_word)
            word_to_guess.append(word.english_word)
    elif language == "Turkish":
        for word in words:
            choices = get_random_choices(word.english_word)
            options.append(choices)
            correct_words.append(word.english_word)
            word_to_guess.append(word.turkish_word)
    return options, correct_words, word_to_guess


def clear_session_data():
    session.pop("options", None)
    session.pop("correct_words", None)
    session.pop("word_to_guess", None)
    session.pop("selected_words", None)
    session.pop("counter", None)
    session.pop("predictions", None)
    session.pop("start_flashcard_time", None)
    session.pop("end_flashcard_time", None)
    session["start"] = False

# Function to start a new session. Example, used at the start of the first session or word practice.
def initialize_session_data(language="English"):
    if "options" not in session:
        words = EnglishWord.query.all()
        options, correct_words, word_to_guess = get_all_data_list(words=words, language=language)
        random_number = random.randint(1, 1000000000)
        random.seed(random_number)
        random.shuffle(options)
        random.seed(random_number)
        random.shuffle(correct_words)
        random.seed(random_number)
        random.shuffle(word_to_guess)
        session["options"] = options
        session["correct_words"] = correct_words
        session["word_to_guess"] = word_to_guess
        session["words"] = word_to_guess
        session["counter"] = len(options)
        session["predictions"] = list()
        session["start"] = True
        session["start_flashcard_time"] = datetime.now()
        if language == "English":
            session["target_language"] = "Turkish"
            session["main_language"] = "English"
        elif language == "Turkish":
            session["target_language"] = "English"
            session["main_language"] = "Turkish"


# main page
@app.route("/")
def index():
    return render_template("hello.html")

# where the words are in English and the meaning is in Turkish
@app.route("/english")
@login_required
def english():
    if session["start"] == False:
        clear_session_data()
        initialize_session_data()
    if len(session["options"]) == 0:
        session["end_flashcard_time"] = datetime.now()
        return redirect(url_for("analysis"))
    return render_template("index.html", session=session)


# where the words are in Turkish and the meaning is in English
@app.route("/turkish")
@login_required
def turkish():
    if session["start"] == False:
        clear_session_data()
        initialize_session_data("Turkish")
    if len(session["options"]) == 0:
        session["end_flashcard_time"] = datetime.now()
        return redirect(url_for("analysis"))
    return render_template("index.html", session=session)


# when the words run out, url where form data is sent and where it's recorded in the database
@app.route("/analysis")
def analysis():
    TF_LIST = []
    for predict, correct in zip(session["predictions"], session["correct_words"]):
        if predict == correct:
            TF_LIST.append(True)
        else:
            TF_LIST.append(False)
    session["start"] = False
    analysis_object = Analysis(user_id=session["user_id"], main_language=session["main_language"],
                               target_language=session["target_language"], words=session["words"],
                               correct_options_count=TF_LIST.count(True),
                               wrong_options_count=TF_LIST.count(False), selected_options=session["predictions"],
                               correct_options=session["correct_words"],
                               passing_time=session["end_flashcard_time"] - session["start_flashcard_time"],
                               success_rate=TF_LIST.count(True) / len(TF_LIST),
                               process="{}-{}".format(session["main_language"], session["target_language"]),
                               words_count=len(session["words"]))
    
    db.session.add(analysis_object)
    db.session.commit()
    return render_template("analysis.html", correct_words=session["correct_words"], predictions=session["predictions"],
                           words=session["words"])


@app.route("/compare", methods=["POST"])
def compare():
    if request.method == "POST":
        session["options"].pop(0)
        session["word_to_guess"].pop(0)
        session["counter"] -= 1
        session["predictions"].append(request.form.get("user_choice"))
        session.modified = True
    return redirect(url_for("{}".format(session["main_language"].lower())))

# the url where users' performance was shown in the past
@app.route("/past_work")
def past_work():
    clear_session_data()
    data = db.session.query(User, Analysis).join(Analysis).all()
    
    return render_template("past_work.html", data=data)

#url enabling performance review
@app.route("/past_work/<int:id>")
def past_work_analysis(id):
    data = Analysis.query.filter_by(id=id).first()
    correct_words = data.correct_options.replace("{", "").replace("}", "").split(",")
    predictions = data.selected_options.replace("{", "").replace("}", "").split(",")
    words = data.words.replace("{", "").replace("}", "").split(",")
    clear_session_data()
    return render_template("analysis.html", correct_words=correct_words, predictions=predictions,
                           words=words)

#url for filtering past performances
@app.route("/past_work_filter", methods=["POST"])
def past_work_filter():
    filter_criteria = {
        "nickname":              request.form.getlist("nickname"),
        "process":               request.form.getlist("process"),
        "words_count":           request.form.get("word_count"),
        "correct_options_count": request.form.get("correct_count"),
        "wrong_options_count":   request.form.get("wrong_count"),
        "success_rate":          request.form.get("success_rate"),
        "passing_time":          request.form.get("time"),
    }
    query = db.session.query(User, Analysis).join(Analysis)
    for key, value in filter_criteria.items():
        if value is not None:
            if key in ["correct_options_count", "words_count", "wrong_options_count", "success_rate", "passing_time"]:
                if value == "Çoktan Aza":
                    query = query.order_by(getattr(Analysis, key).desc())
                else:
                    query = query.order_by(getattr(Analysis, key).asc())
            elif key == "nickname":
                # Filter if the user has selected a nickname
                if value:
                    if isinstance(value, list):
                        query = query.filter(getattr(User, key).in_(value))
                    else:
                        query = query.filter(getattr(User, key) == value)
            elif key == "process":
                # Filter if the user has selected a process
                if value:
                    if isinstance(value, list):
                        query = query.filter(getattr(Analysis, key).in_(value))
                    else:
                        query = query.filter(getattr(Analysis, key) == value)
    
    data = db.session.query(User, Analysis).join(Analysis).all()
    
    return render_template("past_work_filter.html", data2=query.all(), data=data, filter_criteria=filter_criteria)

# sign in page
@app.route("/sign_in", methods=["POST", "GET"])
def sign_in():
    form = LoginForm(request.form)
    if request.method == "POST":
        nickname = form.nickname.data
        password = form.password.data
        users = User.query.filter_by(nickname=nickname).all()
        if len(users) == 0:
            flash("Invalid username or password", category="danger")
            return redirect(url_for("sign_in"))
        elif sha256_crypt.verify(password, users[0].password):
            flash("Successful Entry", category="success")
            session["logged_in"] = True
            session["start"] = False
            
            session["user_id"] = users[0].id
            session["user_nickname"] = users[0].nickname
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", category="danger")
            return redirect(url_for("sign_in"))
    return render_template("sign_in.html", form=form)

# register page
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST":
        name = form.name.data
        surname = form.surname.data
        nickname = form.nickname.data
        password = sha256_crypt.hash(form.password.data)
        if len(User.query.filter_by(nickname=nickname).all()) > 0:
            flash("Already nickname registered", category="danger")
            redirect(url_for("register"))
        else:
            user = User(name=name, surname=surname, nickname=nickname, password=password)
            db.session.add(user)
            db.session.commit()
            flash("Successfully registered", category="success")
            return redirect(url_for("sign_in"))
    return render_template("register.html", form=form)

# logout page
@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully logout", category="success")
    return redirect(url_for("index"))

#dashboard page
@app.route("/dashboard")
@login_required
def dashboard():
    data = db.session.query(User, Analysis).join(Analysis).filter_by(user_id=session["user_id"]).all()
    clear_session_data()
    return render_template("dashboard.html", data=data)

#dashboard filter page
@app.route("/dashboard_filter", methods=["POST"])
def dashboard_filter():
    filter_criteria = {
        "nickname":              session["user_nickname"],
        "process":               request.form.getlist("process"),
        "words_count":           request.form.get("word_count"),
        "correct_options_count": request.form.get("correct_count"),
        "wrong_options_count":   request.form.get("wrong_count"),
        "success_rate":          request.form.get("success_rate"),
        "passing_time":          request.form.get("time"),
    }
    query = db.session.query(User, Analysis).join(Analysis)
    for key, value in filter_criteria.items():
        if value is not None:
            if key in ["correct_options_count", "words_count", "wrong_options_count", "success_rate", "passing_time"]:
                if value == "Çoktan Aza":
                    query = query.order_by(getattr(Analysis, key).desc())
                else:
                    query = query.order_by(getattr(Analysis, key).asc())
            elif key == "process":
                # Filter if the user has selected a process
                if value:
                    if isinstance(value, list):
                        query = query.filter(getattr(Analysis, key).in_(value))
                    else:
                        query = query.filter(getattr(Analysis, key) == value)
            else:
                query = query.filter(getattr(User, key) == value)
    
    data = db.session.query(User, Analysis).join(Analysis).all()
    
    return render_template("dashboard_filter.html", data2=query.all(), data=data, filter_criteria=filter_criteria)


#page where new words can be added
@app.route("/insert_word", methods=["POST", "GET"])
@login_required
def insert_word():
    form = InsertWord(request.form)
    if request.method == "POST":
        word = form.word.data
        opposite = form.opposite.data
        new_word = EnglishWord(english_word=word, turkish_word=opposite)
        db.session.add(new_word)
        db.session.commit()
        flash("New word insertion successful!", "success")
        return redirect(url_for("insert_word"))
    return render_template("insertWord.html", form=form)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
