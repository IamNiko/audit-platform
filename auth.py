import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, redirect, url_for, g, current_app, make_response
from models import User

SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('JWT_SECRET')
if not SECRET_KEY:
    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError('SECRET_KEY or JWT_SECRET must be configured in production')
    SECRET_KEY = 'dev-only-change-me'

def encode_token(user_id, role):
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),  # Token valid for 24h
            'iat': datetime.utcnow(),
            'sub': user_id,
            'role': role
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    except Exception as e:
        return None

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        
        payload = decode_token(token)
        if isinstance(payload, str):
            # Error message returned
            resp = make_response(redirect(url_for('login')))
            resp.delete_cookie('token')
            return resp
        
        # Load user
        user = User.query.get(payload['sub'])
        if not user:
            resp = make_response(redirect(url_for('login')))
            resp.delete_cookie('token')
            return resp
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or g.current_user is None:
                return redirect(url_for('login'))
            if g.current_user.role not in roles:
                # Return Forbidden or redirect to a safe page
                return "Acceso denegado: permisos insuficientes.", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
