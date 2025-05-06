from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import random

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SECRET_KEY'] = 'secret-key'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= Models =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    option1 = db.Column(db.String(100), nullable=False)
    option2 = db.Column(db.String(100), nullable=False)
    option3 = db.Column(db.String(100), nullable=False)
    option4 = db.Column(db.String(100), nullable=False)
    answer = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)

class QuizScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    score = db.Column(db.Integer, nullable=False)

# ============ Login Manager =============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============ Routes =============

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing_user = User.query.filter_by(username=request.form['username']).first()
        if existing_user:
            flash('Username already taken.', 'danger')
            return redirect(url_for('register'))

        user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form['username'], 
            password=request.form['password']
        ).first()
        if user:
            login_user(user)
            return redirect(url_for('categories'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/categories')
@login_required
def categories():
    all_categories = db.session.query(Question.category).distinct().all()
    return render_template('categories.html', categories=[c[0] for c in all_categories])

@app.route('/quiz/<category>', methods=['GET', 'POST'])
@login_required
def quiz(category):
    if request.method == 'POST':
        selected_answers = request.form
        score = 0
        for qid, ans in selected_answers.items():
            question = Question.query.get(int(qid))
            if question and question.answer == ans:
                score += 1

        new_score = QuizScore(username=current_user.username, score=score)
        db.session.add(new_score)
        db.session.commit()

        # Instead of redirecting to leaderboard, render a result page
        return render_template('result.html', score=score)

    questions = Question.query.filter_by(category=category).all()
    random.shuffle(questions)
    return render_template('quiz.html', questions=questions, category=category)

@app.route('/leaderboard')
def leaderboard():
    scores = QuizScore.query.order_by(QuizScore.score.desc()).all()
    return render_template('leaderboard.html', scores=scores)

# =========== Admin Routes ===========

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' in session:
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'password':
            session['admin'] = username
            return redirect(url_for('admin_panel'))
        else:
            flash('Invalid admin credentials!', 'danger')

    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    questions = Question.query.all()
    return render_template('admin_panel.html', questions=questions)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_question():
    if 'admin' not in session:
        return redirect(url_for('admin'))

    if request.method == 'POST':
        new_question = Question(
            question=request.form['question'],
            option1=request.form['option1'],
            option2=request.form['option2'],
            option3=request.form['option3'],
            option4=request.form['option4'],
            answer=request.form['answer'],
            category=request.form['category']
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('add_question.html')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_question(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    question = Question.query.get(id)
    if request.method == 'POST':
        question.question = request.form['question']
        question.option1 = request.form['option1']
        question.option2 = request.form['option2']
        question.option3 = request.form['option3']
        question.option4 = request.form['option4']
        question.answer = request.form['answer']
        question.category = request.form['category']

        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('edit_question.html', question=question)

@app.route('/admin/delete/<int:id>')
def delete_question(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    question = Question.query.get(id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

# ========== Run App and Init DB ==========

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add some sample questions if DB is empty
        if Question.query.count() == 0:
            sample_questions = [
                Question(
                    question="What is the capital of France?",
                    option1="Berlin", option2="Madrid", option3="Paris", option4="Rome",
                    answer="Paris", category="Geography"
                ),
                Question(
                    question="2 + 2 = ?", 
                    option1="3", option2="4", option3="5", option4="6",
                    answer="4", category="Math"
                ),
                Question(
                    question="H2O is the chemical formula for?", 
                    option1="Salt", option2="Hydrogen", option3="Water", option4="Oxygen",
                    answer="Water", category="Science"
                )
            ]
            db.session.add_all(sample_questions)
            db.session.commit()

    app.run(debug=True)
