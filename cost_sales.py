import csv
import os
from datetime import datetime

COST_SALES_FILE = 'cost_sales.csv'

def load_cost_sales():
    """Load cost and sales data from CSV file."""
    if not os.path.exists(COST_SALES_FILE):
        return []
    
    data = []
    with open(COST_SALES_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        data = list(reader)
    return data

def save_cost_sales(data):
    """Save cost and sales data to CSV file."""
    if not data:
        return
    
    fieldnames = ['Activity', 'Sub-Activity', 'Cost', 'Sales', 'Notes', 'Last Updated']
    
    with open(COST_SALES_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def add_or_update_cost_sales(activity_name, sub_activity, cost=None, sales=None, notes=None):
    """Add or update cost/sales for an activity."""
    data = load_cost_sales()
    
    # Find existing entry
    existing = None
    for entry in data:
        if entry['Activity'] == activity_name and entry['Sub-Activity'] == sub_activity:
            existing = entry
            break
    
    if existing:
        # Update existing
        if cost is not None:
            existing['Cost'] = str(cost)
        if sales is not None:
            existing['Sales'] = str(sales)
        if notes is not None:
            existing['Notes'] = notes
        existing['Last Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Create new
        new_entry = {
            'Activity': activity_name,
            'Sub-Activity': sub_activity,
            'Cost': str(cost) if cost is not None else '',
            'Sales': str(sales) if sales is not None else '',
            'Notes': notes if notes else '',
            'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data.append(new_entry)
    
    save_cost_sales(data)
    return True

def get_cost_sales(activity_name, sub_activity=''):
    """Get cost/sales for a specific activity."""
    data = load_cost_sales()
    for entry in data:
        if entry['Activity'] == activity_name and entry['Sub-Activity'] == sub_activity:
            return entry
    return None

def delete_cost_sales(activity_name, sub_activity_name=None):
    """Delete cost/sales entries for an activity.
    
    Args:
        activity_name: Name of the activity to delete
        sub_activity_name: Name of the sub-activity to delete (if None, deletes all entries for activity)
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    data = load_cost_sales()
    
    if not data:
        return False
    
    original_count = len(data)
    
    if sub_activity_name:
        # Delete specific sub-activity entry
        data = [entry for entry in data if not (entry['Activity'] == activity_name and entry['Sub-Activity'] == sub_activity_name)]
    else:
        # Delete all entries for this activity
        data = [entry for entry in data if entry['Activity'] != activity_name]
    
    if len(data) < original_count:
        save_cost_sales(data)
        return True
    return False

def cleanup_orphaned_cost_sales(activities_list):
    """
    Remove cost/sales records that don't have matching activities.
    This cleans up records from deleted activities.
    
    Args:
        activities_list: List of active activities from activity_utils
    
    Returns:
        int: Number of orphaned records deleted
    """
    data = load_cost_sales()
    
    if not data:
        return 0
    
    # Build set of valid (activity, sub-activity) pairs
    valid_pairs = set()
    for activity in activities_list:
        activity_name = activity.get('Activity', '')
        sub_activity = activity.get('Sub-Activity', '')
        valid_pairs.add((activity_name, sub_activity))
    
    original_count = len(data)
    
    # Keep only records with valid activity/sub-activity pairs
    data = [entry for entry in data if (entry.get('Activity', ''), entry.get('Sub-Activity', '')) in valid_pairs]
    
    deleted_count = original_count - len(data)
    
    if deleted_count > 0:
        save_cost_sales(data)
    
    return deleted_count

def get_summary():
    """Get summary statistics for cost and sales."""
    data = load_cost_sales()
    
    total_cost = 0
    total_sales = 0
    count = 0
    
    for entry in data:
        if entry.get('Cost') and entry['Cost'].strip():
            try:
                total_cost += float(entry['Cost'])
            except ValueError:
                pass
        
        if entry.get('Sales') and entry['Sales'].strip():
            try:
                total_sales += float(entry['Sales'])
            except ValueError:
                pass
        
        if entry.get('Cost') or entry.get('Sales'):
            count += 1
    
    profit = total_sales - total_cost if total_sales and total_cost else 0
    
    return {
        'total_cost': total_cost,
        'total_sales': total_sales,
        'profit': profit,
        'count': count
    }
