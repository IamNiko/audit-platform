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


def encode_token(user_id, role, state='authenticated'):
    """
    state puede ser: 'change_password', '2fa_setup', '2fa_verify', 'authenticated'
    Los tokens parciales tienen max_age de 1 hora; los completos, 24h.
    """
    try:
        now = datetime.utcnow()
        payload = {
            'exp': now + timedelta(days=1),
            'iat': now,
            'sub': user_id,
            'role': role,
            'state': state,
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
    """Requiere token con state='authenticated' y usuario activo."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))

        payload = decode_token(token)
        if isinstance(payload, str):
            resp = make_response(redirect(url_for('login')))
            resp.delete_cookie('token')
            return resp

        state = payload.get('state', '')
        if state != 'authenticated':
            # Redirigir al paso correcto del flujo
            _state_map = {
                'change_password': 'auth_change_password',
                '2fa_setup':       'auth_2fa_setup',
                '2fa_verify':      'auth_2fa_verify',
            }
            target = _state_map.get(state, 'login')
            return redirect(url_for(target))

        user = User.query.get(payload['sub'])
        if not user or not user.is_active:
            resp = make_response(redirect(url_for('login')))
            resp.delete_cookie('token')
            return resp

        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def partial_token_required(expected_state):
    """Protege rutas intermedias del flujo de autenticación (cambio de password, setup 2FA, verify 2FA)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.cookies.get('token')
            if not token:
                return redirect(url_for('login'))

            payload = decode_token(token)
            if isinstance(payload, str):
                resp = make_response(redirect(url_for('login')))
                resp.delete_cookie('token')
                return resp

            current_state = payload.get('state', '')

            # Si ya está fully authenticated, va al dashboard
            if current_state == 'authenticated':
                return redirect(url_for('dashboard'))

            if current_state != expected_state:
                return redirect(url_for('login'))

            user = User.query.get(payload['sub'])
            if not user or not user.is_active:
                resp = make_response(redirect(url_for('login')))
                resp.delete_cookie('token')
                return resp

            g.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or g.current_user is None:
                return redirect(url_for('login'))
            if g.current_user.role not in roles:
                return "Acceso denegado: permisos insuficientes.", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
