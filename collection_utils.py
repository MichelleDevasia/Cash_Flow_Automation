import csv
import os
import math
from datetime import datetime

CSV_FILE = 'invoice_collection.csv'

def load_collection():
    """Load global collection period setting from CSV file."""
    if not os.path.exists(CSV_FILE):
        return None
    
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        if rows:
            return rows[0]  # Return first (and only) row
    return None

def save_collection(collection_days, notes=''):
    """
    Save global collection period setting to CSV file.
    
    Args:
        collection_days: Number of days for collection (0-365)
        notes: Optional notes about the collection period
    """
    fieldnames = ['Collection_Days', 'Collection_Months', 'Notes', 'Last Updated']
    
    collection_months = days_to_months(collection_days)
    
    data = {
        'Collection_Days': str(collection_days),
        'Collection_Months': str(collection_months),
        'Notes': notes,
        'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(data)

def days_to_months(days):
    """
    Convert days to months (always whole numbers).
    1-30 days = 1 month
    31-60 days = 2 months
    61-90 days = 3 months, etc.
    """
    if days <= 0:
        return 0
    # Formula: ceiling(days / 30)
    months = math.ceil(days / 30)
    return months

def get_collection_days():
    """Get the global collection days setting."""
    collection = load_collection()
    if collection:
        try:
            return int(collection.get('Collection_Days', 0) or 0)
        except ValueError:
            return 0
    return 0

def get_collection_months():
    """Get the global collection months setting."""
    collection = load_collection()
    if collection:
        try:
            return int(collection.get('Collection_Months', 0) or 0)
        except ValueError:
            return 0
    return 0

def set_collection(collection_days, notes=''):
    """
    Set the global collection period.
    
    Args:
        collection_days: Number of days for collection (0-365)
        notes: Optional notes about the collection period
    """
    save_collection(collection_days, notes)
    return days_to_months(collection_days)

def delete_collection():
    """Delete the collection period setting."""
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)

def get_all_collection():
    """Get all collection information."""
    return load_collection() or {}
