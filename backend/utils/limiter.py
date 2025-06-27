import os
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

class RateLimiter:
    def __init__(self):
        # Use in-memory storage instead of Redis for simplicity
        self.daily_counts = defaultdict(int)
        self.weekly_counts = defaultdict(int)
        self.daily_timestamps = {}
        self.weekly_timestamps = {}
        self.daily_limit = int(os.getenv("DAILY_LIMIT", 10))
        self.weekly_limit = int(os.getenv("WEEKLY_LIMIT", 50))
    
    def _get_daily_key(self, email):
        """Generate daily rate limit key for a user."""
        today = datetime.now().strftime('%Y-%m-%d')
        return f"{email}:daily:{today}"
    
    def _get_weekly_key(self, email):
        """Generate weekly rate limit key for a user."""
        # Get the start of the current week (Monday)
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        week_id = start_of_week.strftime('%Y-%m-%d')
        return f"{email}:weekly:{week_id}"
    
    def _cleanup_old_entries(self):
        """Clean up old entries from memory."""
        now = datetime.now()
        
        # Clean up daily entries older than 2 days
        keys_to_remove = []
        for key, timestamp in self.daily_timestamps.items():
            if now - timestamp > timedelta(days=2):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.daily_counts.pop(key, None)
            self.daily_timestamps.pop(key, None)
        
        # Clean up weekly entries older than 8 days
        keys_to_remove = []
        for key, timestamp in self.weekly_timestamps.items():
            if now - timestamp > timedelta(days=8):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.weekly_counts.pop(key, None)
            self.weekly_timestamps.pop(key, None)
    
    def check_rate_limit(self, email):
        """
        Check if the user has exceeded their daily or weekly limit.
        
        Returns:
            dict: {"allowed": bool, "message": str}
        """
        try:
            self._cleanup_old_entries()
            
            daily_key = self._get_daily_key(email)
            weekly_key = self._get_weekly_key(email)
            
            daily_count = self.daily_counts.get(daily_key, 0)
            weekly_count = self.weekly_counts.get(weekly_key, 0)
            
            if daily_count >= self.daily_limit:
                return {
                    "allowed": False,
                    "message": f"Daily application limit of {self.daily_limit} exceeded. Try again tomorrow."
                }
            
            if weekly_count >= self.weekly_limit:
                return {
                    "allowed": False,
                    "message": f"Weekly application limit of {self.weekly_limit} exceeded. Try again next week."
                }
            
            return {"allowed": True, "message": "Application allowed"}
        
        except Exception as e:
            # If rate limiting fails, allow the request but log the error
            print(f"Rate limiting error: {e}")
            return {"allowed": True, "message": "Rate limiting temporarily disabled"}
    
    def increment_counters(self, email):
        """Increment the daily and weekly counters for a user."""
        try:
            daily_key = self._get_daily_key(email)
            weekly_key = self._get_weekly_key(email)
            now = datetime.now()
            
            # Increment daily counter
            self.daily_counts[daily_key] += 1
            self.daily_timestamps[daily_key] = now
            
            # Increment weekly counter
            self.weekly_counts[weekly_key] += 1
            self.weekly_timestamps[weekly_key] = now
            
            return {
                "daily": self.daily_counts[daily_key], 
                "weekly": self.weekly_counts[weekly_key]
            }
        
        except Exception as e:
            print(f"Error incrementing counters: {e}")
            return {"daily": 0, "weekly": 0}