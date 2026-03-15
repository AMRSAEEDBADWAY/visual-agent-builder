import os
import shutil
import datetime
import time

def backup_database():
    """
    Creates a backup of the main SQLite database.
    """
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "projects.db")
    backup_dir = os.path.join(base_dir, "backups")
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Check if DB exists
    if not os.path.exists(db_path):
        print(f"[{datetime.datetime.now()}] ERROR: No database found at {db_path} to backup.")
        return False
        
    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"projects_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"[{datetime.datetime.now()}] SUCCESS: Database backed up successfully to {backup_path}")
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ERROR: Failed to backup database. Reason: {e}")
        return False

if __name__ == "__main__":
    print("Starting automated database backup script...")
    print("Press Ctrl+C to stop.")
    try:
        # Run infinitely, backing up every 12 hours (43200 seconds)
        # You can adjust this to run via Cron job instead of a Python while loop 
        # for production environments.
        while True:
            backup_database()
            time.sleep(43200) 
    except KeyboardInterrupt:
        print("Backup script stopped by user.")
