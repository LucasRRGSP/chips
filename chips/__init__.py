from flask import Blueprint


chips_bp = Blueprint('chips', __name__, template_folder='templates')
from . import routes
