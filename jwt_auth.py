import os
import jwt
import streamlit as st

from datetime import datetime, timedelta

# Pakai SECRET_KEY yang sama dengan auth.py — baca dari env/secrets
_secret = os.environ.get("FNB_JWT_SECRET", "")
if not _secret:
    try:
        _secret = st.secrets.get("FNB_JWT_SECRET", "")
    except Exception:
        pass
SECRET_KEY = _secret or "dev-only-secret-not-for-production-use-min32!"

ALGORITHM = "HS256"

COOKIE_NAME = "fnb_token"

EXPIRE_DAYS = 7


# ─────────────────────────────
# CREATE JWT
# ─────────────────────────────

def create_token(user_id, username, role):

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=EXPIRE_DAYS),
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return token


# ─────────────────────────────
# VERIFY JWT
# ─────────────────────────────

def verify_token(token):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None