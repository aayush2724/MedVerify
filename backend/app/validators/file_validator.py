import os
import uuid
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
import pypdfium2 as pdfium
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app
from ..errors import FileValidationError, INVALID_FILE_FORMAT, FILE_TOO_LARGE, FILE_CORRUPTED

class FileValidator:
    @staticmethod
    def validate(file_storage):
        # 1. Check extension
        filename = file_storage.filename
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if ext not in current_app.config['ALLOWED_EXTENSIONS']:
            raise FileValidationError(
                INVALID_FILE_FORMAT, 
                f"Extension .{ext} is not allowed",
                details={"allowed": list(current_app.config['ALLOWED_EXTENSIONS'])}
            )

        # 2. Check MIME type via magic bytes (if available) or extension mapping
        header = file_storage.read(2048)
        file_storage.seek(0)
        if HAS_MAGIC:
            mime_type = magic.from_buffer(header, mime=True)
        else:
            # Fallback: infer MIME from extension
            ext_to_mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'pdf': 'application/pdf'}
            mime_type = ext_to_mime.get(ext, 'application/octet-stream')
        if mime_type not in current_app.config['ALLOWED_MIME_TYPES']:
            raise FileValidationError(
                INVALID_FILE_FORMAT,
                f"MIME type {mime_type} is not allowed",
                details={"detected": mime_type, "allowed": list(current_app.config['ALLOWED_MIME_TYPES'])}
            )

        # 3. Check File Size
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
        if size > current_app.config['MAX_CONTENT_LENGTH']:
            raise FileValidationError(
                FILE_TOO_LARGE,
                f"File size {size} exceeds limit",
                details={"size": size, "limit": current_app.config['MAX_CONTENT_LENGTH']}
            )

        # 4. Content Specific Validation
        if mime_type == 'application/pdf':
            try:
                pdf = pdfium.PdfDocument(file_storage)
                if len(pdf) < 1:
                    raise FileValidationError(FILE_CORRUPTED, "PDF has no pages")
                file_storage.seek(0)
            except Exception as e:
                raise FileValidationError(FILE_CORRUPTED, f"Invalid or corrupted PDF: {str(e)}")
        
        elif mime_type.startswith('image/'):
            try:
                img = Image.open(file_storage)
                img.verify() # Verify image integrity
                
                # Re-open for dimension checks (verify() closes the file pointer)
                file_storage.seek(0)
                img = Image.open(file_storage)
                width, height = img.size
                
                if width < 100 or height < 100:
                    raise FileValidationError(INVALID_FILE_FORMAT, "Image is too small to be a certificate")
                if width > 10000 or height > 10000:
                    raise FileValidationError(INVALID_FILE_FORMAT, "Image dimensions are too large")
                
                file_storage.seek(0)
            except Exception as e:
                raise FileValidationError(FILE_CORRUPTED, f"Invalid or corrupted image: {str(e)}")

        return True

    @staticmethod
    def sanitise_filename(filename):
        base_name = secure_filename(filename)
        # Prepend UUID to prevent collisions and path traversal
        return f"{uuid.uuid4().hex}_{base_name}"

    @staticmethod
    def save_temp(file_storage, upload_folder):
        FileValidator.validate(file_storage)
        filename = FileValidator.sanitise_filename(file_storage.filename)
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file_storage.save(filepath)
        return filepath
