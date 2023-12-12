import random
import time

from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from Forms import LoginForm, RegisterForm,InsertWord
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://omer:123456@localhost:5432/orm_trailer"
db = SQLAlchemy(app=app)
app.secret_key = "secret_key"


# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.", "danger")
            return redirect(url_for("sign_in"))
    
    return decorated_function


class EnglishWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    english_word = db.Column(db.String(80), nullable=False)
    turkish_word = db.Column(db.String(80), nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    surname = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(255), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow( ), nullable=False)
    analysis = db.relationship("Analysis", backref="user", lazy=True)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    main_language = db.Column(db.String(30), nullable=False)
    target_language = db.Column(db.String(30), nullable=False)
    words = db.Column(db.String(255), nullable=False)
    correct_options_count = db.Column(db.Numeric, nullable=False)
    wrong_options_count = db.Column(db.Numeric, nullable=False)
    correct_options = db.Column(db.String(255), nullable=False)
    selected_options = db.Column(db.String(255), nullable=False)
    passing_time = db.Column(db.String(255), nullable=False)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow( ), nullable=False)


def get_random_choices(correct_word):
    incorrect_words = (
        EnglishWord.query.filter(EnglishWord.turkish_word != correct_word).order_by(db.func.random( )).limit(3).all( )
    )
    all_choices = [correct_word] + [word.turkish_word for word in incorrect_words]
    random.shuffle(all_choices)
    return all_choices


def get_all_data_list(words):
    options = []
    correct_words = []
    word_to_guess = []
    for word in words:
        choices = get_random_choices(word.turkish_word)
        options.append(choices)
        correct_words.append(word.turkish_word)
        word_to_guess.append(word.english_word)
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


def initialize_session_data():
    if "options" not in session:
        words = EnglishWord.query.all( )
        options, correct_words, word_to_guess = get_all_data_list(words=words)
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
        session["predictions"] = list( )
        session["start"] = True
        session["start_flashcard_time"] = datetime.now( )


@app.route("/")
def index():
    return render_template("hello.html", session=session)


@app.route("/english")
@login_required
def english():
    if session["start"] == False:
        clear_session_data( )
        initialize_session_data( )
    
    if len(session["options"]) == 0:
        session["target_language"] = "Turkish"
        session["main_language"] = "English"
        session["end_flashcard_time"] = datetime.now( )
        return redirect(url_for("analysis"))
    return render_template("index.html", session=session)


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
                               passing_time=session["end_flashcard_time"] - session["start_flashcard_time"])
    
    db.session.add(analysis_object)
    db.session.commit( )
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
    return redirect(url_for("english"))


@app.route("/past_work")
def past_work():
    clear_session_data( )
    data = db.session.query(User, Analysis).join(Analysis).all( )
    
    return render_template("past_work.html", data=data)


@app.route("/past_work/<int:id>")
def past_work_analysis(id):
    data = Analysis.query.filter_by(id=id).first( )
    correct_words = data.correct_options.replace("{", "").replace("}", "").split(",")
    predictions = data.selected_options.replace("{", "").replace("}", "").split(",")
    words = data.words.replace("{", "").replace("}", "").split(",")
    clear_session_data( )
    return render_template("analysis.html", correct_words=correct_words, predictions=predictions,
                           words=words)


@app.route("/sign_in", methods=["POST", "GET"])
def sign_in():
    form = LoginForm(request.form)
    if request.method == "POST":
        nickname = form.nickname.data
        password = form.password.data
        users = User.query.filter_by(nickname=nickname).all( )
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


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST":
        isim = form.name.data
        soyisim = form.surname.data
        nickname = form.nickname.data
        password = sha256_crypt.hash(form.password.data)
        if len(User.query.filter_by(nickname=nickname).all( )) > 0:
            flash("Already nickname registered", category="danger")
            redirect(url_for("register"))
        else:
            user = User(name=isim, surname=soyisim, nickname=nickname, password=password)
            db.session.add(user)
            db.session.commit( )
            flash("Successfully registered", category="success")
            return redirect(url_for("sign_in"))
    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    session.clear( )
    flash("Successfully logout", category="success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    data = db.session.query(User, Analysis).join(Analysis).filter_by(user_id=session["user_id"]).all( )
    clear_session_data( )
    return render_template("dashboard.html", data=data)


@app.route("/insert_word", methods=["POST","GET"])
@login_required
def insert_word():
    form = InsertWord(request.form)
    if request.method == "POST":
        pass
    return render_template("insertWord.html",form=form)


if __name__ == '__main__':
    with app.app_context( ):
        db.create_all( )
    app.run(debug=True)
