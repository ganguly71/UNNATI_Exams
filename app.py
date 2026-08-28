import os
from flask import Flask
from models import db, User, Student, SystemSetting
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here_for_exams'
    
    # DB Config (Sharing the same DB as UNNATI)
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        # Default fallback, construct absolute path to UNNATI's database
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'UNNATI'))
        db_path = os.path.join(base_dir, 'instance', 'database.db')
        db_url = 'sqlite:///' + db_path.replace('\\', '/')
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if "sqlite" in db_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
        }
    else:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 10,
            'max_overflow': 15,
        }

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'main.index'
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

    def run_migrations():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        required_columns = [
            ("questions", "exam_id", "INTEGER REFERENCES exams(id)"),
            ("questions", "text", "TEXT"),
            ("questions", "marks_awarded", "FLOAT NOT NULL DEFAULT 1.0"),
            ("questions", "marks_deducted", "FLOAT NOT NULL DEFAULT 0.0"),
            ("questions", "image_url", "VARCHAR(500)"),
            ("options", "text", "TEXT"),
            ("options", "is_correct", "BOOLEAN DEFAULT FALSE"),
            ("assignment_groups", "threshold_percent", "FLOAT NOT NULL DEFAULT 50.0"),
            ("remedial_schedules", "assignment_group_id", "INTEGER REFERENCES assignment_groups(id)"),
            ("students", "password_hash", "VARCHAR(255)"),
            ("students", "enrolled_next_sem", "BOOLEAN DEFAULT FALSE"),
            ("students", "last_sem_upgrade_date", "TIMESTAMP"),
            ("exam_submissions", "question_order", "TEXT"),
            ("exam_submissions", "question_states", "TEXT")
        ]
        
        for table_name, col_name, col_def in required_columns:
            if not inspector.has_table(table_name):
                continue
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            if col_name not in columns:
                try:
                    db.session.execute(db.text(
                        f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
                    ))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        # Legacy columns cleanup to prevent NOT NULL constraint failures
        legacy_cleanup = [
            ("questions", "online_test_id"),
            ("questions", "question_text"),
            ("questions", "positive_marks"),
            ("questions", "negative_marks"),
            ("options", "option_text")
        ]
        for table_name, col_name in legacy_cleanup:
            if inspector.has_table(table_name):
                columns = [c['name'] for c in inspector.get_columns(table_name)]
                if col_name in columns:
                    try:
                        cascade = " CASCADE" if "postgresql" in str(db.engine.url) else ""
                        db.session.execute(db.text(
                            f"ALTER TABLE {table_name} DROP COLUMN {col_name}{cascade}"
                        ))
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

    with app.app_context():
        db.create_all()
        run_migrations()

        # Seed/Reset default admin user
        try:
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                # Convert user with ID 1 if exists, otherwise create new
                admin = User.query.get(1)
                if admin:
                    admin.email = 'admin@example.com'
                    admin.set_password("asdfghjkl;'")
                    admin.role = 'admin'
                else:
                    admin = User(name="System Admin", email="admin@example.com", role="admin")
                    admin.set_password("asdfghjkl;'")
                    db.session.add(admin)
            else:
                admin.set_password("asdfghjkl;'")
                admin.role = 'admin'
            db.session.commit()
        except Exception:
            db.session.rollback()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(port=5001, debug=True)
