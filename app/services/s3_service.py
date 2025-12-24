"""
VPS-based file storage service for file uploads and storage
Uses local filesystem instead of AWS S3
"""
import os
import shutil
from pathlib import Path
from typing import Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class FileStorageService:
    """Service for file storage on VPS using local filesystem"""
    
    def __init__(self):
        """Initialize file storage service"""
        # Base directory for file storage
        # Default to 'uploads' directory in backend root, or use env var
        self.base_dir = os.getenv('UPLOAD_BASE_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads'))
        self.static_url_prefix = os.getenv('STATIC_URL_PREFIX', '/static')
        
        # Create base directory structure
        self._ensure_directories()
        
        logger.info(f"File storage initialized at: {self.base_dir}")
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.base_dir,
            os.path.join(self.base_dir, 'gallery'),
            os.path.join(self.base_dir, 'downloads'),
            os.path.join(self.base_dir, 'documents'),
            os.path.join(self.base_dir, 'avatars'),
            os.path.join(self.base_dir, 'blog'),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def upload_file(
        self,
        file_content: bytes,
        file_path: str,
        subdirectory: str = 'uploads'
    ) -> Optional[str]:
        """
        Upload file to local storage
        
        Args:
            file_content: File content as bytes
            file_path: Relative file path (e.g., 'gallery/image.jpg')
            subdirectory: Subdirectory within base_dir (default: 'uploads')
            
        Returns:
            Public URL of uploaded file or None if failed
        """
        try:
            # Ensure file_path doesn't have leading slash
            file_path = file_path.lstrip('/')
            
            # Full path on filesystem
            full_path = os.path.join(self.base_dir, subdirectory, file_path)
            
            # Create parent directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(file_content)
            
            # Generate public URL
            # Format: /static/{subdirectory}/{file_path}
            url = f"{self.static_url_prefix}/{subdirectory}/{file_path}"
            logger.info(f"File uploaded successfully: {full_path} -> {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    def upload_file_from_path(
        self,
        source_path: str,
        file_path: str,
        subdirectory: str = 'uploads'
    ) -> Optional[str]:
        """
        Copy file from source path to storage
        
        Args:
            source_path: Source file path
            file_path: Destination relative file path
            subdirectory: Subdirectory within base_dir
            
        Returns:
            Public URL of uploaded file or None if failed
        """
        try:
            if not os.path.exists(source_path):
                logger.error(f"Source file not found: {source_path}")
                return None
            
            # Read source file
            with open(source_path, 'rb') as f:
                file_content = f.read()
            
            return self.upload_file(file_content, file_path, subdirectory)
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return None
    
    def delete_file(self, file_path: str, subdirectory: str = 'uploads') -> bool:
        """
        Delete file from storage
        
        Args:
            file_path: Relative file path
            subdirectory: Subdirectory within base_dir
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = file_path.lstrip('/')
            full_path = os.path.join(self.base_dir, subdirectory, file_path)
            
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"File deleted successfully: {full_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {full_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def file_exists(self, file_path: str, subdirectory: str = 'uploads') -> bool:
        """
        Check if file exists
        
        Args:
            file_path: Relative file path
            subdirectory: Subdirectory within base_dir
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = file_path.lstrip('/')
        full_path = os.path.join(self.base_dir, subdirectory, file_path)
        return os.path.exists(full_path)
    
    def get_file_path(self, file_path: str, subdirectory: str = 'uploads') -> Optional[str]:
        """
        Get full filesystem path for a file
        
        Args:
            file_path: Relative file path
            subdirectory: Subdirectory within base_dir
            
        Returns:
            Full filesystem path or None if not found
        """
        file_path = file_path.lstrip('/')
        full_path = os.path.join(self.base_dir, subdirectory, file_path)
        
        if os.path.exists(full_path):
            return full_path
        return None


# Create singleton instance
file_storage = FileStorageService()

