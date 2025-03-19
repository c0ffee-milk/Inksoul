from flask import render_template,Blueprint,redirect,url_for
from flask_login import current_user
bp = Blueprint('index', __name__,url_prefix="/")

@bp.route('/')
def index_page():
    if current_user.is_authenticated:
        return redirect(url_for('diary.mine'))
    return render_template('index.html')