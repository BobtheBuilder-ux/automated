import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Any
import json

class FirebaseService:
    def __init__(self):
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try different methods to get Firebase credentials
                service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
                
                if service_account_path and os.path.exists(service_account_path):
                    # Use service account file from environment variable
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase initialized from environment variable")
                elif os.path.exists("firebase-service-account.json"):
                    # Use service account file in current directory
                    with open("firebase-service-account.json", 'r') as f:
                        service_account_data = json.load(f)
                    
                    # Check if it's a placeholder file
                    if "placeholder" in service_account_data.get("private_key_id", ""):
                        print("⚠️  Firebase service account is a placeholder. Please replace with actual credentials.")
                        print("   Download the service account key from Firebase Console:")
                        print("   Project Settings > Service Accounts > Generate new private key")
                        self.db = None
                        return
                    
                    cred = credentials.Certificate("firebase-service-account.json")
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase initialized from service account file")
                else:
                    print("⚠️  Firebase service account key not found. Using mock data.")
                    print("   To fix this:")
                    print("   1. Go to Firebase Console > Project Settings > Service Accounts")
                    print("   2. Click 'Generate new private key'")
                    print("   3. Save as 'firebase-service-account.json' in backend folder")
                    self.db = None
                    return
            
            self.db = firestore.client()
            
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            print("   Using mock data instead.")
            self.db = None
    
    async def create_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application record in Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            # Add timestamp
            application_data["createdAt"] = datetime.utcnow()
            application_data["updatedAt"] = datetime.utcnow()
            
            # Ensure all required fields are present with defaults
            default_fields = {
                "company_name": application_data.get("company_name", "Unknown Company"),
                "company_email": application_data.get("company_email", ""),
                "job_description": application_data.get("job_description", ""),
                "job_board": application_data.get("job_board", "Manual Application"),
                "application_url": application_data.get("application_url", ""),
                "email_sent": application_data.get("email_sent", False),
                "email_sent_to": application_data.get("email_sent_to", ""),
                "email_subject": application_data.get("email_subject", ""),
                "email_body": application_data.get("email_body", ""),
                "email_sent_at": application_data.get("email_sent_at", None),
                "response_received": application_data.get("response_received", False),
                "response_date": application_data.get("response_date", None),
                "interview_scheduled": application_data.get("interview_scheduled", False),
                "interview_date": application_data.get("interview_date", None),
                "application_notes": application_data.get("application_notes", "")
            }
            
            # Merge with provided data
            application_data.update(default_fields)
            
            # Add to Firestore
            doc_ref = self.db.collection('applications').add(application_data)
            application_id = doc_ref[1].id
            
            return {
                "success": True, 
                "id": application_id,
                "message": "Application saved successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_all_applications(self) -> Dict[str, Any]:
        """Get all applications from Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            applications = []
            docs = self.db.collection('applications').order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
            
            for doc in docs:
                app_data = doc.to_dict()
                app_data['id'] = doc.id
                
                # Convert timestamps to ISO format - handle different data types
                if 'createdAt' in app_data and app_data['createdAt']:
                    if hasattr(app_data['createdAt'], 'isoformat'):
                        app_data['createdAt'] = app_data['createdAt'].isoformat()
                    elif isinstance(app_data['createdAt'], str):
                        # Already a string, keep as is
                        pass
                    else:
                        # Convert to string representation
                        app_data['createdAt'] = str(app_data['createdAt'])
                
                if 'updatedAt' in app_data and app_data['updatedAt']:
                    if hasattr(app_data['updatedAt'], 'isoformat'):
                        app_data['updatedAt'] = app_data['updatedAt'].isoformat()
                    elif isinstance(app_data['updatedAt'], str):
                        # Already a string, keep as is
                        pass
                    else:
                        # Convert to string representation
                        app_data['updatedAt'] = str(app_data['updatedAt'])
                
                # Handle other timestamp fields that might be present
                timestamp_fields = ['email_sent_at', 'response_date', 'interview_date']
                for field in timestamp_fields:
                    if field in app_data and app_data[field]:
                        if hasattr(app_data[field], 'isoformat'):
                            app_data[field] = app_data[field].isoformat()
                        elif isinstance(app_data[field], str):
                            # Already a string, keep as is
                            pass
                        else:
                            # Convert to string representation
                            app_data[field] = str(app_data[field])
                
                applications.append(app_data)
            
            return {"success": True, "data": applications}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_application_stats(self) -> Dict[str, Any]:
        """Get application statistics from Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            applications = self.db.collection('applications').stream()
            
            total = 0
            completed = 0
            pending = 0
            failed = 0
            
            for doc in applications:
                total += 1
                status = doc.to_dict().get('status', 'pending').lower()
                
                if status == 'completed':
                    completed += 1
                elif status == 'pending':
                    pending += 1
                elif status == 'failed':
                    failed += 1
            
            success_rate = (completed / total * 100) if total > 0 else 0
            
            stats = {
                "totalApplications": total,
                "completedApplications": completed,
                "pendingApplications": pending,
                "failedApplications": failed,
                "successRate": round(success_rate, 1)
            }
            
            return {"success": True, "data": stats}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_application(self, application_id: str) -> Dict[str, Any]:
        """Delete an application from Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            self.db.collection('applications').document(application_id).delete()
            return {"success": True, "message": "Application deleted successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_application(self, application_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an application in Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            update_data["updatedAt"] = datetime.utcnow()
            self.db.collection('applications').document(application_id).update(update_data)
            
            return {"success": True, "message": "Application updated successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_applications_by_email(self, email: str) -> Dict[str, Any]:
        """Get applications for a specific user email"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            applications = []
            docs = self.db.collection('applications').where('email', '==', email).stream()
            
            for doc in docs:
                app_data = doc.to_dict()
                app_data['id'] = doc.id
                
                # Convert timestamps to ISO format - handle different data types
                if 'createdAt' in app_data and app_data['createdAt']:
                    if hasattr(app_data['createdAt'], 'isoformat'):
                        app_data['createdAt'] = app_data['createdAt'].isoformat()
                    elif isinstance(app_data['createdAt'], str):
                        # Already a string, keep as is
                        pass
                    else:
                        # Convert to string representation
                        app_data['createdAt'] = str(app_data['createdAt'])
                
                if 'updatedAt' in app_data and app_data['updatedAt']:
                    if hasattr(app_data['updatedAt'], 'isoformat'):
                        app_data['updatedAt'] = app_data['updatedAt'].isoformat()
                    elif isinstance(app_data['updatedAt'], str):
                        # Already a string, keep as is
                        pass
                    else:
                        # Convert to string representation
                        app_data['updatedAt'] = str(app_data['updatedAt'])
                
                # Handle other timestamp fields that might be present
                timestamp_fields = ['email_sent_at', 'response_date', 'interview_date']
                for field in timestamp_fields:
                    if field in app_data and app_data[field]:
                        if hasattr(app_data[field], 'isoformat'):
                            app_data[field] = app_data[field].isoformat()
                        elif isinstance(app_data[field], str):
                            # Already a string, keep as is
                            pass
                        else:
                            # Convert to string representation
                            app_data[field] = str(app_data[field])
                
                applications.append(app_data)
            
            return {"success": True, "data": applications}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def store_discovered_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store discovered jobs in Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            batch = self.db.batch()
            
            for job in jobs:
                # Add timestamp
                job["stored_at"] = datetime.utcnow()
                
                # Create document reference
                doc_ref = self.db.collection('discovered_jobs').document()
                batch.set(doc_ref, job)
            
            # Commit batch
            batch.commit()
            
            return {
                "success": True, 
                "message": f"Stored {len(jobs)} discovered jobs successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_discovered_jobs(self, limit: int = 100) -> Dict[str, Any]:
        """Get discovered jobs from Firestore"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            jobs = []
            docs = self.db.collection('discovered_jobs').order_by('discovered_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                
                # Convert timestamps to ISO format
                if 'stored_at' in job_data:
                    job_data['stored_at'] = job_data['stored_at'].isoformat()
                
                jobs.append(job_data)
            
            return {"success": True, "data": jobs}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_old_discovered_jobs(self, days_old: int = 7) -> Dict[str, Any]:
        """Delete discovered jobs older than specified days"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Query old jobs
            old_jobs = self.db.collection('discovered_jobs').where('stored_at', '<', cutoff_date).stream()
            
            # Delete in batches
            batch = self.db.batch()
            count = 0
            
            for doc in old_jobs:
                batch.delete(doc.reference)
                count += 1
                
                # Commit batch every 500 operations (Firestore limit)
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining operations
            if count % 500 != 0:
                batch.commit()
            
            return {
                "success": True, 
                "message": f"Deleted {count} old discovered jobs"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup_old_jobs(self, jobs_to_keep: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace all discovered jobs with only the jobs to keep (72-hour cleanup)"""
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            # Delete all existing discovered jobs
            docs = self.db.collection('discovered_jobs').stream()
            batch = self.db.batch()
            count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                
                # Commit batch every 500 operations (Firestore limit)
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining deletions
            if count % 500 != 0:
                batch.commit()
            
            # Re-add only the jobs to keep
            if jobs_to_keep:
                batch = self.db.batch()
                for job in jobs_to_keep:
                    doc_ref = self.db.collection('discovered_jobs').document()
                    batch.set(doc_ref, job)
                
                batch.commit()
            
            return {
                "success": True, 
                "message": f"Cleanup completed: kept {len(jobs_to_keep)} recent jobs, removed {count - len(jobs_to_keep)} old jobs"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def store_cover_letter(self, cover_letter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store cover letter content and metadata in Firestore
        
        Args:
            cover_letter_data: Dictionary containing cover letter content and metadata
            
        Returns:
            Dict: Success status and message
        """
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            # Add timestamp if not present
            if "timestamp" not in cover_letter_data:
                cover_letter_data["timestamp"] = datetime.utcnow()
                
            # Store relative file path for easier retrieval
            if "file_path" in cover_letter_data:
                # Convert absolute path to relative path for storage
                file_path = cover_letter_data["file_path"]
                if "/" in file_path:
                    file_name = file_path.split("/")[-1]
                    cover_letter_data["download_path"] = f"static/uploads/{file_name}"
                
            # Add document to cover_letters collection
            doc_ref = self.db.collection('cover_letters').add(cover_letter_data)
            cover_letter_id = doc_ref[1].id
            
            return {
                "success": True, 
                "id": cover_letter_id,
                "message": "Cover letter saved successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_cover_letters(self, user_name: Optional[str] = None) -> Dict[str, Any]:
        """Get cover letters from Firestore
        
        Args:
            user_name: Optional filter by user name
            
        Returns:
            Dict: Success status and cover letter data
        """
        if not self.db:
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            query = self.db.collection('cover_letters')
            
            # Filter by user name if provided
            if user_name:
                query = query.where('user_name', '==', user_name)
                
            # Order by timestamp descending
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            cover_letters = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Convert timestamp to ISO format if needed
                if 'timestamp' in data and data['timestamp'] and hasattr(data['timestamp'], 'isoformat'):
                    data['timestamp'] = data['timestamp'].isoformat()
                
                cover_letters.append(data)
            
            return {"success": True, "data": cover_letters}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Create a global instance
firebase_service = FirebaseService()