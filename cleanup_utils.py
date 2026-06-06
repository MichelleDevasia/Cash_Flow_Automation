"""
Cleanup Utilities for Data Integrity

Scans for and removes orphaned records that reference deleted activities, milestones, or bills.
Used when cascading deletion may have missed records or when data files are edited directly.
"""

from activity_utils import load_activities
from invoice_utils import load_invoices, get_all_milestones, get_submilestones
from vendor_payment_utils import load_vendors, get_all_vendors, get_bills
from matching_utils import load_matches, save_matches
from advance_utils import load_advances, save_advances
from vendor_payment_matching_utils import load_vendor_matches, save_vendor_matches


def get_all_activities_and_subs():
    """Get all activities and sub-activities."""
    activities = load_activities()
    all_items = set()
    
    for activity in activities:
        activity_name = activity.get('Activity', '')
        if activity_name:
            all_items.add((activity_name, ''))  # Parent activity
        
        sub_activity = activity.get('Sub-Activity', '')
        if sub_activity:
            all_items.add((activity_name, sub_activity))  # Sub-activity
    
    return all_items


def cleanup_activity_milestone_matches():
    """
    Remove orphaned records from activity_milestone_matching.csv
    (records where Activity, Sub-Activity, Milestone, or Sub-Milestone no longer exist)
    """
    matches = load_matches()
    all_activities = get_all_activities_and_subs()
    all_milestones = get_all_milestones()
    
    # Build set of valid milestone/sub-milestone pairs
    valid_milestones = set()
    for milestone in all_milestones:
        valid_milestones.add((milestone, ''))
        submilestones = get_submilestones(milestone)
        for sub in submilestones:
            valid_milestones.add((milestone, sub.get('name', '')))
    
    # Filter out orphaned records
    original_count = len(matches)
    cleaned_matches = []
    
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        milestone = match.get('Milestone', '')
        sub_milestone = match.get('Sub-Milestone', '')
        
        # Check if both activity and milestone exist
        activity_exists = (activity, sub_activity) in all_activities
        milestone_exists = (milestone, sub_milestone) in valid_milestones
        
        if activity_exists and milestone_exists:
            cleaned_matches.append(match)
    
    if len(cleaned_matches) < original_count:
        save_matches(cleaned_matches)
        removed = original_count - len(cleaned_matches)
        return True, removed, f"Removed {removed} orphaned activity-milestone matches"
    
    return False, 0, "No orphaned activity-milestone matches found"


def cleanup_advances():
    """
    Remove orphaned records from invoice_advance.csv
    (records where Milestone or Sub-Milestone no longer exist)
    """
    advances = load_advances()
    all_milestones = get_all_milestones()
    
    # Build set of valid milestone/sub-milestone pairs
    valid_milestones = set()
    for milestone in all_milestones:
        valid_milestones.add((milestone, ''))
        submilestones = get_submilestones(milestone)
        for sub in submilestones:
            valid_milestones.add((milestone, sub.get('name', '')))
    
    # Filter out orphaned records
    original_count = len(advances)
    cleaned_advances = []
    
    for advance in advances:
        milestone = advance.get('Milestone', '')
        sub_milestone = advance.get('Sub-Milestone', '')
        
        # Check if milestone exists
        if (milestone, sub_milestone) in valid_milestones:
            cleaned_advances.append(advance)
    
    if len(cleaned_advances) < original_count:
        save_advances(cleaned_advances)
        removed = original_count - len(cleaned_advances)
        return True, removed, f"Removed {removed} orphaned advance records"
    
    return False, 0, "No orphaned advance records found"


def cleanup_vendor_matches():
    """
    Remove orphaned records from activity_vendor_bill_matching.csv
    (records where Activity, Sub-Activity, or Bill no longer exist)
    """
    matches = load_vendor_matches()
    all_activities = get_all_activities_and_subs()
    all_vendors = get_all_vendors()
    
    # Build set of valid vendor/bill pairs
    valid_bills = set()
    for vendor in all_vendors:
        bills = get_bills(vendor)
        valid_bills.add((vendor, ''))  # Vendor itself as parent
        for bill_info in bills:
            valid_bills.add((vendor, bill_info.get('name', '')))
    
    # Filter out orphaned records
    original_count = len(matches)
    cleaned_matches = []
    
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        vendor = match.get('Vendor', '')
        bill = match.get('Bill', '')
        
        # Check if both activity and bill exist
        activity_exists = (activity, sub_activity) in all_activities
        bill_exists = (vendor, bill) in valid_bills
        
        if activity_exists and bill_exists:
            cleaned_matches.append(match)
    
    if len(cleaned_matches) < original_count:
        save_vendor_matches(cleaned_matches)
        removed = original_count - len(cleaned_matches)
        return True, removed, f"Removed {removed} orphaned vendor-activity matches"
    
    return False, 0, "No orphaned vendor-activity matches found"


def cleanup_all_orphaned_records():
    """
    Run all cleanup operations and return summary.
    
    Returns:
        tuple: (has_orphans: bool, total_removed: int, results: list of tuples (found, removed, message))
    """
    results = []
    total_removed = 0
    has_orphans = False
    
    # Cleanup activity-milestone matches
    found, removed, msg = cleanup_activity_milestone_matches()
    results.append((found, removed, msg))
    if found:
        has_orphans = True
        total_removed += removed
    
    # Cleanup advances
    found, removed, msg = cleanup_advances()
    results.append((found, removed, msg))
    if found:
        has_orphans = True
        total_removed += removed
    
    # Cleanup vendor matches
    found, removed, msg = cleanup_vendor_matches()
    results.append((found, removed, msg))
    if found:
        has_orphans = True
        total_removed += removed
    
    return has_orphans, total_removed, results
