"""
backlog.py — Backlog de proyectos con clustering y ruta optima
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.core import Project
from app.models.workflow import WorkflowTask, create_workflow_for_project
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict

backlog_bp = Blueprint('backlog', __name__, url_prefix='/backlog')


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos GPS."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))


def auto_cluster(projects, radius_km=5):
    """Clustering simple por proximidad geografica."""
    clusters = {}
    cluster_id = 0
    assigned = set()

    geo_projects = [p for p in projects if p.latitude and p.longitude]

    for p in geo_projects:
        if p.id in assigned:
            continue
        cluster_id += 1
        cluster_name = f"Cluster-{p.municipality or p.department or cluster_id}"
        members = [p]
        assigned.add(p.id)

        for other in geo_projects:
            if other.id in assigned:
                continue
            dist = haversine(p.latitude, p.longitude, other.latitude, other.longitude)
            if dist <= radius_km:
                members.append(other)
                assigned.add(other.id)

        cid = f"CL-{cluster_id:03d}"
        clusters[cid] = {
            'name': cluster_name,
            'projects': members,
            'center_lat': sum(m.latitude for m in members) / len(members),
            'center_lng': sum(m.longitude for m in members) / len(members),
            'total_clients': sum(m.potential_clients or 0 for m in members),
            'total_meters': sum(m.estimated_meters or 0 for m in members),
        }

        for m in members:
            m.cluster_id = cid
            m.cluster_name = cluster_name

    db.session.commit()
    return clusters


def optimal_route(projects):
    """Nearest-neighbor para ruta optima entre proyectos."""
    if len(projects) < 2:
        return projects

    geo = [p for p in projects if p.latitude and p.longitude]
    if len(geo) < 2:
        return projects

    remaining = list(geo)
    route = [remaining.pop(0)]

    while remaining:
        last = route[-1]
        nearest = min(remaining, key=lambda p: haversine(
            last.latitude, last.longitude, p.latitude, p.longitude))
        route.append(nearest)
        remaining.remove(nearest)

    return route


@backlog_bp.route('/')
@login_required
def index():
    """Vista principal del backlog."""
    # Filtros
    dept_filter = request.args.get('department', '')
    muni_filter = request.args.get('municipality', '')
    phase_filter = request.args.get('phase', '')
    priority_filter = request.args.get('priority', '')

    query = Project.query

    if dept_filter:
        query = query.filter(Project.department == dept_filter)
    if muni_filter:
        query = query.filter(Project.municipality == muni_filter)
    if phase_filter:
        query = query.filter(Project.phase == phase_filter)
    if priority_filter:
        query = query.filter(Project.priority == int(priority_filter))

    projects = query.order_by(Project.priority.asc(), Project.created_at.desc()).all()

    # Stats
    stats = {
        'total': len(projects),
        'total_clients': sum(p.potential_clients or 0 for p in projects),
        'total_meters': sum(p.estimated_meters or 0 for p in projects),
        'by_phase': defaultdict(int),
        'by_dept': defaultdict(int),
    }
    for p in projects:
        stats['by_phase'][p.phase or 'sin_fase'] += 1
        stats['by_dept'][p.department or 'Sin depto'] += 1

    # Get unique values for filters
    departments = db.session.query(Project.department).filter(
        Project.department.isnot(None)).distinct().all()
    municipalities = db.session.query(Project.municipality).filter(
        Project.municipality.isnot(None)).distinct().all()

    return render_template('backlog/index.html',
                           projects=projects,
                           stats=stats,
                           departments=[d[0] for d in departments],
                           municipalities=[m[0] for m in municipalities],
                           dept_filter=dept_filter,
                           muni_filter=muni_filter,
                           phase_filter=phase_filter,
                           priority_filter=priority_filter)


@backlog_bp.route('/cluster', methods=['POST'])
@login_required
def run_clustering():
    """Ejecutar clustering automatico."""
    radius = float(request.form.get('radius', 5))
    projects = Project.query.all()
    clusters = auto_cluster(projects, radius_km=radius)
    flash(f'Clustering completado: {len(clusters)} clusters identificados.', 'success')
    return redirect(url_for('backlog.index'))


@backlog_bp.route('/route')
@login_required
def optimal_route_view():
    """Ver ruta optima entre proyectos."""
    projects = Project.query.filter(
        Project.latitude.isnot(None),
        Project.longitude.isnot(None)
    ).all()
    route = optimal_route(projects)

    route_data = [{
        'id': p.id, 'name': p.name, 'lat': p.latitude, 'lng': p.longitude,
        'clients': p.potential_clients or 0, 'phase': p.phase,
        'department': p.department or '', 'municipality': p.municipality or ''
    } for p in route]

    total_km = 0
    for i in range(1, len(route)):
        total_km += haversine(
            route[i-1].latitude, route[i-1].longitude,
            route[i].latitude, route[i].longitude)

    return render_template('backlog/route.html',
                           route=route, route_data=route_data,
                           total_km=round(total_km, 2))


@backlog_bp.route('/project/<int:project_id>/update', methods=['POST'])
@login_required
def update_project(project_id):
    """Actualizar campos de backlog de un proyecto."""
    project = Project.query.get_or_404(project_id)
    data = request.form

    project.department = data.get('department', project.department)
    project.municipality = data.get('municipality', project.municipality)
    project.potential_clients = int(data.get('potential_clients', 0)) if data.get('potential_clients') else project.potential_clients
    project.estimated_meters = float(data.get('estimated_meters', 0)) if data.get('estimated_meters') else project.estimated_meters
    project.priority = int(data.get('priority', 3)) if data.get('priority') else project.priority
    project.start_lat = float(data.get('start_lat')) if data.get('start_lat') else project.start_lat
    project.start_lng = float(data.get('start_lng')) if data.get('start_lng') else project.start_lng
    project.end_lat = float(data.get('end_lat')) if data.get('end_lat') else project.end_lat
    project.end_lng = float(data.get('end_lng')) if data.get('end_lng') else project.end_lng
    project.backlog_notes = data.get('backlog_notes', project.backlog_notes)

    db.session.commit()
    flash('Proyecto actualizado.', 'success')
    return redirect(url_for('backlog.index'))
