import csv
import os
from datetime import datetime

CSV_FILE = 'activity_vendor_bill_matching.csv'

def load_vendor_matches():
    """Load activity-vendor bill matches from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    matches = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        matches = list(reader)
    return matches

def save_vendor_matches(matches):
    """Save activity-vendor bill matches to CSV file."""
    if not matches:
        # Create empty file with headers
        fieldnames = ['Activity', 'Sub-Activity', 'Bill', 'Vendor', 'Link Strength', 'Notes', 'Last Updated']
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        return
    
    fieldnames = ['Activity', 'Sub-Activity', 'Bill', 'Vendor', 'Link Strength', 'Notes', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

def add_vendor_match(activity, sub_activity, bill, vendor, link_strength='Medium', notes=''):
    """
    Add a match between an activity/sub-activity and a vendor bill.
    
    Args:
        activity: Activity name
        sub_activity: Sub-activity name (empty string if linking main activity)
        bill: Bill name
        vendor: Vendor name
        link_strength: 'Strong', 'Medium', or 'Weak' (default: 'Medium')
        notes: Optional notes about the match
    """
    matches = load_vendor_matches()
    
    # Check if match already exists
    for match in matches:
        if (match.get('Activity') == activity and 
            match.get('Sub-Activity') == sub_activity and 
            match.get('Bill') == bill):
            # Update existing match
            match['Link Strength'] = link_strength
            match['Notes'] = notes
            match['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_vendor_matches(matches)
            return
    
    # Add new match
    new_match = {
        'Activity': activity,
        'Sub-Activity': sub_activity,
        'Bill': bill,
        'Vendor': vendor,
        'Link Strength': link_strength,
        'Notes': notes,
        'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    matches.append(new_match)
    save_vendor_matches(matches)

def delete_vendor_match(activity, sub_activity, bill, vendor):
    """
    Delete a specific match.
    
    Args:
        activity: Activity name
        sub_activity: Sub-activity name
        bill: Bill name
        vendor: Vendor name
    """
    matches = load_vendor_matches()
    matches = [m for m in matches if not (
        m.get('Activity') == activity and 
        m.get('Sub-Activity') == sub_activity and 
        m.get('Bill') == bill and
        m.get('Vendor') == vendor
    )]
    save_vendor_matches(matches)

def delete_vendor_matches_by_activity(activity_name, sub_activity_name=None):
    """
    Delete all matches for an activity or sub-activity.
    Used for cascading deletion when an activity is deleted.
    
    Args:
        activity_name: Name of the activity to delete matches for
        sub_activity_name: Name of the sub-activity to delete matches for (if None, deletes all matches for the activity)
    
    Returns:
        bool: True if any matches were deleted, False otherwise
    """
    matches = load_vendor_matches()
    original_count = len(matches)
    
    if sub_activity_name:
        # Delete matches for specific sub-activity
        matches = [m for m in matches if not (
            m.get('Activity') == activity_name and 
            m.get('Sub-Activity') == sub_activity_name
        )]
    else:
        # Delete all matches for this activity
        matches = [m for m in matches if m.get('Activity') != activity_name]
    
    if len(matches) < original_count:
        save_vendor_matches(matches)
        return True
    return False

def delete_vendor_matches_by_bill(vendor_name, bill_name=None):
    """
    Delete all matches for a vendor or bill.
    Used for cascading deletion when a bill is deleted.
    
    Args:
        vendor_name: Name of the vendor to delete matches for
        bill_name: Name of the bill to delete matches for (if None, deletes all matches for this vendor)
    
    Returns:
        bool: True if any matches were deleted, False otherwise
    """
    matches = load_vendor_matches()
    original_count = len(matches)
    
    if bill_name:
        # Delete matches for specific bill
        matches = [m for m in matches if not (
            m.get('Vendor') == vendor_name and 
            m.get('Bill') == bill_name
        )]
    else:
        # Delete all matches for this vendor
        matches = [m for m in matches if m.get('Vendor') != vendor_name]
    
    if len(matches) < original_count:
        save_vendor_matches(matches)
        return True
    return False

def get_matches_by_activity(activity, sub_activity=''):
    """Get all matches for a specific activity/sub-activity."""
    matches = load_vendor_matches()
    return [m for m in matches if m.get('Activity') == activity and m.get('Sub-Activity') == sub_activity]

def get_matches_by_bill(bill):
    """Get all matches for a specific bill."""
    matches = load_vendor_matches()
    return [m for m in matches if m.get('Bill') == bill]

def get_all_activities_and_subs(activities_list):
    """
    Extract all activities and their sub-activities from activities list.
    
    Args:
        activities_list: List of activity dictionaries from activity_utils
    
    Returns:
        List of tuples (activity_name, sub_activity_name) where sub_activity_name is empty for main activities
    """
    activities_and_subs = []
    unique_combos = set()
    
    for activity in activities_list:
        activity_name = activity.get('Activity', '')
        sub_activity = activity.get('Sub-Activity', '')
        
        combo = (activity_name, sub_activity)
        if combo not in unique_combos:
            activities_and_subs.append(combo)
            unique_combos.add(combo)
    
    return sorted(activities_and_subs, key=lambda x: (x[0], x[1]))

def get_all_bills(vendors_list):
    """
    Extract all bills from vendors list.
    
    Args:
        vendors_list: List of vendor dictionaries from vendor_payment_utils
    
    Returns:
        List of tuples (vendor_name, bill_name, percentage, credit_days)
    """
    bills = []
    
    for vendor in vendors_list:
        vendor_name = vendor.get('Vendor', '')
        bill_name = vendor.get('Bill', '')
        percentage = vendor.get('Percentage', '0')
        credit_days = vendor.get('Credit_Days', '0')
        
        if bill_name:  # Only include actual bills
            bills.append((vendor_name, bill_name, percentage, credit_days))
    
    return sorted(bills, key=lambda x: (x[0], x[1]))
