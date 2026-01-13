import os
import boto3
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from botocore.exceptions import ClientError

from .config import config
from .models import db, User, News


def create_app(config_name='default'):
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY') or 'dev-secret-key'
    
    # Initialize database
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # S3 client for Yandex Object Storage
    def get_s3_client():
        return boto3.client(
            's3',
            endpoint_url=app.config.get('YANDEX_ENDPOINT_URL'),
            aws_access_key_id=app.config.get('YANDEX_ACCESS_KEY_ID'),
            aws_secret_access_key=app.config.get('YANDEX_SECRET_ACCESS_KEY'),
            region_name=app.config.get('YANDEX_REGION')
        )
    
    # SQS client for Yandex Message Queue
    def get_sqs_client():
        return boto3.client(
            'sqs',
            endpoint_url=app.config.get('YANDEX_SQS_ENDPOINT_URL'),
            aws_access_key_id=app.config.get('YANDEX_SQS_ACCESS_KEY_ID'),
            aws_secret_access_key=app.config.get('YANDEX_SQS_SECRET_ACCESS_KEY'),
            region_name=app.config.get('YANDEX_REGION')
        )
    
    # Extract filename from full URL
    def extract_filename_from_url(url):
        """Extract filename from Yandex Object Storage URL."""
        if not url:
            return None
        try:
            # URL format: https://storage.yandexcloud.net/bucket-name/filename
            return url.split('/')[-1]
        except:
            return None
    
    # Send delete message to queue
    def send_delete_message(image_url):
        """Send image URL to delete queue."""
        try:
            queue_url = app.config.get('YANDEX_SQS_QUEUE_URL')
            if not queue_url:
                return False
            
            sqs = get_sqs_client()
            filename = extract_filename_from_url(image_url)
            if not filename:
                return False
            
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=filename
            )
            return True
        except Exception as e:
            app.logger.error(f'Error sending delete message: {e}')
            return False
    
    # Upload image to Yandex Object Storage
    def upload_image_to_storage(image_file):
        """Upload image to Yandex Object Storage and return URL."""
        if not image_file or not image_file.filename:
            return None
        
        try:
            s3 = get_s3_client()
            bucket_name = app.config.get('YANDEX_BUCKET_NAME')
            
            # Generate unique filename
            original_filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            
            # Upload
            s3.upload_fileobj(
                image_file,
                bucket_name,
                unique_filename,
                ExtraArgs={'ContentType': image_file.content_type}
            )
            
            # Return public URL
            endpoint = app.config.get('YANDEX_ENDPOINT_URL')
            return f"{endpoint}/{bucket_name}/{unique_filename}"
        except ClientError as e:
            app.logger.error(f'Error uploading image: {e}')
            return None
    
    # Delete image from Yandex Object Storage
    def delete_image_from_storage(image_url):
        """Delete image from Yandex Object Storage."""
        if not image_url:
            return False
        
        try:
            s3 = get_s3_client()
            bucket_name = app.config.get('YANDEX_BUCKET_NAME')
            filename = extract_filename_from_url(image_url)
            
            if not filename:
                return False
            
            s3.delete_object(Bucket=bucket_name, Key=filename)
            return True
        except ClientError as e:
            app.logger.error(f'Error deleting image: {e}')
            return False
    
    # Before request - set current user
    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
    
    # Home page - list all news
    @app.route('/')
    def index():
        all_news = News.query.order_by(News.created_at.desc()).all()
        return render_template('index.html', news_list=all_news)
    
    # ============ AUTH ROUTES ============
    
    # Register
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if g.user:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            
            if not username or not email or not password:
                flash('Все поля обязательны!', 'error')
                return redirect(url_for('register'))
            
            if password != password_confirm:
                flash('Пароли не совпадают!', 'error')
                return redirect(url_for('register'))
            
            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash('Пользователь с таким именем или email уже существует!', 'error')
                return redirect(url_for('register'))
            
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')
    
    # Login
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if g.user:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                flash(f'Добро пожаловать, {user.username}!', 'success')
                return redirect(url_for('index'))
            
            flash('Неверное имя пользователя или пароль!', 'error')
            return redirect(url_for('login'))
        
        return render_template('login.html')
    
    # Logout
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('Вы вышли из системы.', 'success')
        return redirect(url_for('index'))
    
    # ============ NEWS ROUTES ============
    
    # Create news (requires auth)
    @app.route('/news/create', methods=['GET', 'POST'])
    def create_news():
        if not g.user:
            flash('Для создания новости необходимо войти!', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            image = request.files.get('image')
            
            if not title or not content:
                flash('Заголовок и содержание обязательны!', 'error')
                return redirect(url_for('create_news'))
            
            # Upload image to Yandex Object Storage
            image_url = None
            if image and image.filename:
                image_url = upload_image_to_storage(image)
                if not image_url:
                    flash('Ошибка загрузки изображения', 'error')
                    return redirect(url_for('create_news'))
            
            new_news = News(title=title, content=content, user_id=g.user.id, image_url=image_url)
            db.session.add(new_news)
            db.session.commit()
            flash('Новость успешно создана!', 'success')
            return redirect(url_for('index'))
        
        return render_template('create.html')
    
    # View single news
    @app.route('/news/<int:news_id>')
    def view_news(news_id):
        news = News.query.get_or_404(news_id)
        return render_template('view.html', news=news)
    
    # Edit news (author only)
    @app.route('/news/<int:news_id>/edit', methods=['GET', 'POST'])
    def edit_news(news_id):
        if not g.user:
            flash('Для редактирования необходимо войти!', 'error')
            return redirect(url_for('login'))
        
        news = News.query.get_or_404(news_id)
        
        # Check authorship
        if news.user_id != g.user.id:
            flash('Вы можете редактировать только свои новости!', 'error')
            return redirect(url_for('view_news', news_id=news_id))
        
        if request.method == 'POST':
            news.title = request.form.get('title')
            news.content = request.form.get('content')
            image = request.files.get('image')
            
            if not news.title or not news.content:
                flash('Заголовок и содержание обязательны!', 'error')
                return redirect(url_for('edit_news', news_id=news_id))
            
            # Upload new image if provided
            if image and image.filename:
                # Delete old image
                old_image_url = news.image_url
                
                # Upload new image
                new_image_url = upload_image_to_storage(image)
                if new_image_url:
                    news.image_url = new_image_url
                    # Send delete message for old image (async via SQS)
                    send_delete_message(old_image_url)
                else:
                    flash('Ошибка загрузки изображения', 'error')
                    return redirect(url_for('edit_news', news_id=news_id))
            
            db.session.commit()
            flash('Новость успешно обновлена!', 'success')
            return redirect(url_for('view_news', news_id=news.id))
        
        return render_template('edit.html', news=news)
    
    # Delete news (author only)
    @app.route('/news/<int:news_id>/delete', methods=['POST'])
    def delete_news(news_id):
        if not g.user:
            flash('Для удаления необходимо войти!', 'error')
            return redirect(url_for('login'))
        
        news = News.query.get_or_404(news_id)
        
        # Check authorship
        if news.user_id != g.user.id:
            flash('Вы можете удалять только свои новости!', 'error')
            return redirect(url_for('view_news', news_id=news_id))
        
        # Get image URL before deleting
        image_url = news.image_url
        
        # Delete from database
        db.session.delete(news)
        db.session.commit()
        
        # Delete image from storage (or send to queue)
        if image_url:
            # Try to delete directly first
            if not delete_image_from_storage(image_url):
                # Fallback: send to SQS queue for async deletion
                send_delete_message(image_url)
        
        flash('Новость успешно удалена!', 'success')
        return redirect(url_for('index'))
    
    # My news
    @app.route('/my-news')
    def my_news():
        if not g.user:
            flash('Для просмотра своих новостей необходимо войти!', 'error')
            return redirect(url_for('login'))
        
        my_news_list = News.query.filter_by(user_id=g.user.id).order_by(News.created_at.desc()).all()
        return render_template('my_news.html', news_list=my_news_list)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    # Debug endpoint for checking configuration
    @app.route('/debug/config')
    def debug_config():
        """Debug endpoint to check configuration."""
        config_status = {
            'database_configured': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
            'database_host': app.config.get('DB_HOST'),
            'database_name': app.config.get('DB_NAME'),
            'bucket_name': app.config.get('YANDEX_BUCKET_NAME'),
            'endpoint_url': app.config.get('YANDEX_ENDPOINT_URL'),
            'access_key_configured': bool(app.config.get('YANDEX_ACCESS_KEY_ID')),
            'sqs_queue_url': app.config.get('YANDEX_SQS_QUEUE_URL'),
        }
        return {
            'status': 'ok',
            'config': config_status,
            'environment_vars': {k: v[:10] + '...' if len(v) > 10 else v for k, v in os.environ.items() if k.startswith('YANDEX') or k == 'SECRET_KEY'}
        }
    
    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)