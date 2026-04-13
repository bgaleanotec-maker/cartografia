from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime

docs_bp = Blueprint('docs', __name__, url_prefix='/docs')


@docs_bp.route('/workflow')
@login_required
def workflow():
    """Complete workflow documentation page."""
    return render_template('docs/workflow.html', now=datetime.utcnow().strftime('%Y-%m-%d'))
