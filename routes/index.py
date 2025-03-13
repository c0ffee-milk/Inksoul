from flask import render_template,Blueprint

bp = Blueprint('index', __name__,url_prefix="/")

@bp.route('/')
def index_page():
    return render_template('index.html')