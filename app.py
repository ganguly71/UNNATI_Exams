import os
from flask import Flask
from models import db, User, Student
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here_for_exams'
    
    # DB Config (Sharing the same DB as UNNATI)
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        # Default fallback, should ideally be the absolute path to UNNATI's database if local
        db_url = 'sqlite:///../UNNATI/instance/database.db' 
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('faculty_'):
            return User.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('student_'):
            return Student.query.get(int(user_id.split('_')[1]))
        return None

    from routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=5001, debug=True)
