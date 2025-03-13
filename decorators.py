from functools import wraps
from flask import g, redirect, url_for


def login_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if hasattr(g, "user"):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('auth.login'))
    return inner