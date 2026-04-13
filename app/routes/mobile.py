from flask import Blueprint, render_template
from flask_login import login_required

mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')


@mobile_bp.route('/field')
@login_required
def field_capture():
    """Mobile-lite field capture view — GPS-first, offline-capable."""
    return render_template('mobile/field_capture.html')
