import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, redirect, url_for, g, current_app, make_response
from models import User


def _get_secret_key():
    """Resuelve SECRET_KEY desde el contexto de la app en runtime.
    Evita depender del orden de importación respecto a load_dotenv().
    """
    return current_app.config['SECRET_KEY']

def encode_token(user_id, role):
    try:
        now = datetime.utcnow()
        payload = {
            'exp': now + timedelta(days=1),  # Token válido 24h
            'iat': now,
            'sub': user_id,
            'role': role
        }
        return jwt.encode(payload, _get_secret_key(), algorithm='HS256')
    except Exception:
        return None

def decode_token(token):
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=['HS256'])
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
