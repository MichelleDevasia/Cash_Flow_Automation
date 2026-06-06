import csv
import os
from datetime import datetime

CSV_FILE = 'activity_milestone_matching.csv'

def load_matches():
    """Load activity-milestone matches from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    matches = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        matches = list(reader)
    return matches

def save_matches(matches):
    """Save activity-milestone matches to CSV file."""
    if not matches:
        # Create empty file with headers
        fieldnames = ['Activity', 'Sub-Activity', 'Sub-Milestone', 'Milestone', 'Link Strength', 'Notes', 'Last Updated']
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        return
    
    fieldnames = ['Activity', 'Sub-Activity', 'Sub-Milestone', 'Milestone', 'Link Strength', 'Notes', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

def add_match(activity, sub_activity, sub_milestone, milestone, link_strength='Medium', notes=''):
    """
    Add a match between an activity/sub-activity and a sub-milestone.
    
    Args:
        activity: Activity name
        sub_activity: Sub-activity name (empty string if linking main activity)
        sub_milestone: Sub-milestone name
        milestone: Parent milestone name
        link_strength: 'Strong', 'Medium', or 'Weak' (default: 'Medium')
        notes: Optional notes about the match
    """
    matches = load_matches()
    
    # Check if match already exists
    for match in matches:
        if (match.get('Activity') == activity and 
            match.get('Sub-Activity') == sub_activity and 
            match.get('Sub-Milestone') == sub_milestone):
            # Update existing match
            match['Link Strength'] = link_strength
            match['Notes'] = notes
            match['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_matches(matches)
            return
    
    # Add new match
    new_match = {
        'Activity': activity,
        'Sub-Activity': sub_activity,
        'Sub-Milestone': sub_milestone,
        'Milestone': milestone,
        'Link Strength': link_strength,
        'Notes': notes,
        'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    matches.append(new_match)
    save_matches(matches)

def delete_match(activity, sub_activity, sub_milestone):
    """
    Delete a specific match.
    
    Args:
        activity: Activity name
        sub_activity: Sub-activity name
        sub_milestone: Sub-milestone name
    """
    matches = load_matches()
    matches = [m for m in matches if not (
        m.get('Activity') == activity and 
        m.get('Sub-Activity') == sub_activity and 
        m.get('Sub-Milestone') == sub_milestone
    )]
    save_matches(matches)

def delete_matches_by_activity(activity_name, sub_activity_name=None):
    """
    Delete all matches for an activity or sub-activity.
    Used for cascading deletion when an activity is deleted.
    
    Args:
        activity_name: Name of the activity to delete matches for
        sub_activity_name: Name of the sub-activity to delete matches for (if None, deletes all matches for the activity)
    
    Returns:
        bool: True if any matches were deleted, False otherwise
    """
    matches = load_matches()
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
        save_matches(matches)
        return True
    return False

def delete_matches_by_milestone(milestone_name, sub_milestone_name=None):
    """
    Delete all matches for a milestone or sub-milestone.
    Used for cascading deletion when a milestone is deleted.
    
    Args:
        milestone_name: Name of the milestone to delete matches for
        sub_milestone_name: Name of the sub-milestone to delete matches for (if None, deletes all matches for this milestone)
    
    Returns:
        bool: True if any matches were deleted, False otherwise
    """
    matches = load_matches()
    original_count = len(matches)
    
    if sub_milestone_name:
        # Delete matches for specific sub-milestone
        matches = [m for m in matches if not (
            m.get('Milestone') == milestone_name and 
            m.get('Sub-Milestone') == sub_milestone_name
        )]
    else:
        # Delete all matches for this milestone
        matches = [m for m in matches if m.get('Milestone') != milestone_name]
    
    if len(matches) < original_count:
        save_matches(matches)
        return True
    return False

def get_matches_by_activity(activity, sub_activity=''):
    """Get all matches for a specific activity/sub-activity."""
    matches = load_matches()
    return [m for m in matches if m.get('Activity') == activity and m.get('Sub-Activity') == sub_activity]

def get_matches_by_submilestone(sub_milestone):
    """Get all matches for a specific sub-milestone."""
    matches = load_matches()
    return [m for m in matches if m.get('Sub-Milestone') == sub_milestone]

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

def get_all_submilestones(invoices_list):
    """
    Extract all sub-milestones from invoices list.
    
    Args:
        invoices_list: List of invoice dictionaries from invoice_utils
    
    Returns:
        List of tuples (milestone_name, sub_milestone_name, percentage)
    """
    submilestones = []
    
    for invoice in invoices_list:
        milestone_name = invoice.get('Milestone', '')
        sub_milestone = invoice.get('Sub-Milestone', '')
        percentage = invoice.get('Percentage', '0')
        
        if sub_milestone:  # Only include actual sub-milestones
            submilestones.append((milestone_name, sub_milestone, percentage))
    
    return sorted(submilestones, key=lambda x: (x[0], x[1]))
