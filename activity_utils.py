import csv
import os
from datetime import datetime

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 
          'July', 'August', 'September', 'October', 'November', 'December']
CSV_FILE = 'activities.csv'

def load_activities():
    """Load activities from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    activities = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        activities = list(reader)
    return activities

def save_activities(activities):
    """Save activities to CSV file."""
    if not activities:
        return
    
    from calculation_utils import get_calculation_months
    calc_months = get_calculation_months()
    fieldnames = ['Activity', 'Sub-Activity', 'Start Month', 'End Month', 'Cost', 'Sales'] + calc_months
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(activities)

def add_activity(activity_name, sub_activities, start_month, end_month, percentages, cost=None, sales=None):
    """Add new activity or sub-activities to CSV."""
    from calculation_utils import get_calculation_months
    calc_months = get_calculation_months()
    
    activities = load_activities()
    
    if not sub_activities:
        # Single activity without sub-activities
        activity = {
            'Activity': activity_name,
            'Sub-Activity': '',
            'Start Month': start_month,
            'End Month': end_month,
            'Cost': cost if cost else '',
            'Sales': sales if sales else ''
        }
        for month in calc_months:
            activity[month] = str(percentages.get(month, 0))
        activities.append(activity)
    else:
        # Activity with sub-activities
        for sub in sub_activities:
            activity = {
                'Activity': activity_name,
                'Sub-Activity': sub,
                'Start Month': start_month,
                'End Month': end_month,
                'Cost': cost if cost else '',
                'Sales': sales if sales else ''
            }
            for month in calc_months:
                activity[month] = str(percentages.get(month, 0))
            activities.append(activity)
    
    save_activities(activities)
    return True

def get_activity_months(start_month, end_month):
    """Get list of months in the range."""
    from calculation_utils import get_calculation_months
    calc_months = get_calculation_months()
    
    if start_month not in calc_months or end_month not in calc_months:
        return []
        
    start_idx = calc_months.index(start_month)
    end_idx = calc_months.index(end_month)
    
    if start_idx <= end_idx:
        return calc_months[start_idx:end_idx + 1]
    else:
        return []

def delete_activity(activity_name, sub_activity_name=None):
    """Delete an activity or sub-activity from CSV.
    
    Args:
        activity_name: Name of the activity to delete
        sub_activity_name: Name of the sub-activity to delete (if None, deletes all entries for activity)
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    activities = load_activities()
    
    if not activities:
        return False
    
    original_count = len(activities)
    
    if sub_activity_name:
        # Delete specific sub-activity
        activities = [a for a in activities if not (a.get('Activity') == activity_name and a.get('Sub-Activity') == sub_activity_name)]
    else:
        # Delete all entries for this activity
        activities = [a for a in activities if a.get('Activity') != activity_name]
    
    if len(activities) < original_count:
        save_activities(activities)
        return True
    return False
