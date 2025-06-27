import os
from fastapi import UploadFile
import shutil
from datetime import datetime
import uuid
from typing import Optional, Tuple


class FileHandler:
    def __init__(self, upload_dir: str = "backend/static/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing special characters.
        
        Args:
            filename: The original filename
            
        Returns:
            str: Sanitized filename
        """
        # Replace spaces with underscores
        sanitized = filename.replace(" ", "_")
        # Keep only alphanumeric characters, dots, and underscores
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '._-')
        return sanitized
    
    def _generate_unique_filename(self, original_filename: str, user_name: str) -> str:
        """
        Generate a unique filename for an uploaded file.
        
        Args:
            original_filename: The original filename
            user_name: The user's name for better organization
            
        Returns:
            str: A unique filename
        """
        # Get file extension
        _, file_ext = os.path.splitext(original_filename)
        
        # Sanitize user name
        sanitized_name = self._sanitize_filename(user_name)
        
        # Generate unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]  # Short UUID
        
        return f"{sanitized_name}_{timestamp}_{unique_id}{file_ext}"
    
    async def save_uploaded_file(self, 
                                file: UploadFile, 
                                user_name: str, 
                                file_type: str = "document") -> Tuple[bool, str]:
        """
        Save an uploaded file to the uploads directory.
        
        Args:
            file: UploadFile object from FastAPI
            user_name: The user's name
            file_type: Type of file (cv, certificate, etc.)
            
        Returns:
            Tuple[bool, str]: (success, filepath or error message)
        """
        try:
            if not file:
                return False, "No file provided"
            
            # Generate a unique filename
            unique_filename = self._generate_unique_filename(file.filename, user_name)
            
            # Create full filepath
            filename_with_type = f"{file_type}_{unique_filename}"
            file_path = os.path.join(self.upload_dir, filename_with_type)
            
            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Reset the file pointer after reading
            await file.seek(0)
            
            return True, file_path
        
        except Exception as e:
            return False, f"Error saving file: {str(e)}"
            
    def save_generated_file(self, 
                          content: str, 
                          user_name: str, 
                          file_type: str = "cover_letter",
                          file_ext: str = ".txt") -> Tuple[bool, str]:
        """
        Save generated content to a file.
        
        Args:
            content: String content to save
            user_name: The user's name
            file_type: Type of file (cover_letter, etc.)
            file_ext: File extension
            
        Returns:
            Tuple[bool, str]: (success, filepath or error message)
        """
        try:
            # Generate a unique filename
            sanitized_name = self._sanitize_filename(user_name)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            
            # Create filename and path
            filename = f"{file_type}_{sanitized_name}_{timestamp}_{unique_id}{file_ext}"
            file_path = os.path.join(self.upload_dir, filename)
            
            # Save the content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            return True, file_path
            
        except Exception as e:
            return False, f"Error saving file: {str(e)}"