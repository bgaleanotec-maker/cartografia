import os
import uuid
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from app import db
from app.models.core import ProjectDocument

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentService:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def allowed_file(self, filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def save_project_document(self, file, project_id, category='general'):
        """
        Saves a file for a specific project.
        :param file: The file object from request.files
        :param project_id: ID of the project
        :param category: Optional category tag (e.g., 'viability', 'evidence')
        :return: ProjectDocument object or raises Exception
        """
        if not file or file.filename == '':
            raise ValueError("No valid file provided.")

        # Enforce 20 files limit
        current_count = ProjectDocument.query.filter_by(project_id=project_id).count()
        if current_count >= 20:
             raise ValueError("Límite de 20 archivos por proyecto alcanzado.")

        if not self.allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}")

        try:
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
            
            # Generate Unique Filename: <project_id>_[CATEGORY]_<timestamp>_<uuid>.<ext>
            unique_id = str(uuid.uuid4())[:8]
            timestamp = int(datetime.now().timestamp())
            
            # Sanitize category
            safe_category = secure_filename(category).upper() if category else 'GENERAL'
            
            saved_filename = f"{project_id}_{safe_category}_{timestamp}_{unique_id}.{file_ext}"
            
            file_path = os.path.join(self.upload_folder, saved_filename)
            
            logger.info(f"Saving file to: {file_path}")
            file.save(file_path)

            # Create Database Record
            doc = ProjectDocument(
                project_id=project_id,
                filename=saved_filename,
                file_type=file_ext,
                # We could add category if the model supported it, for now we stick to schema
            )
            
            db.session.add(doc)
            db.session.commit()
            
            logger.info(f"Document saved successfully: ID {doc.id}")
            return doc

        except Exception as e:
            logger.error(f"Failed to save document: {str(e)}")
            db.session.rollback()
            raise e

    def delete_document(self, doc_id):
        try:
            doc = ProjectDocument.query.get(doc_id)
            if not doc:
                raise ValueError("Document not found.")

            file_path = os.path.join(self.upload_folder, doc.filename)
            
            # Delete from Disk
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted from disk: {file_path}")
            else:
                logger.warning(f"File not found on disk during delete: {file_path}")

            # Delete from DB
            db.session.delete(doc)
            db.session.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            db.session.rollback()
            raise e

# Helper instantiation (singleton-like)
# UPLOAD_FOLDER should be passed from config, but for now we derive it
upload_path = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
document_service = DocumentService(upload_path)
