import sys
import os

# Add the current directory to sys.path to allow imports
sys.path.append(os.getcwd())

from app import create_app, db
from app.models.core import ProjectDocument, Project

app = create_app()

with app.app_context():
    print("Checking DB for documents...")
    docs = ProjectDocument.query.all()
    print(f"Total documents in DB: {len(docs)}")
    
    for d in docs:
        print(f"Doc ID: {d.id}, Project ID: {d.project_id}, Name: {d.filename}")

    print("-" * 20)
    # Check specific project from verify script (usually the last one)
    last_project = Project.query.order_by(Project.id.desc()).first()
    if last_project:
        print(f"Last Project ID: {last_project.id}")
        p_docs = ProjectDocument.query.filter_by(project_id=last_project.id).all()
        print(f"Docs for Project {last_project.id}: {len(p_docs)}")
    else:
        print("No projects found.")
