import csv
import os
from datetime import datetime

CSV_FILE = 'invoice_advance.csv'

def load_advances():
    """Load advance payments from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    advances = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        advances = list(reader)
    return advances

def save_advances(advances):
    """Save advance payments to CSV file."""
    if not advances:
        # Create empty file with headers
        fieldnames = ['Milestone', 'Sub-Milestone', 'Advance_Percentage', 'Month', 'Notes', 'Last Updated']
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        return
    
    fieldnames = ['Milestone', 'Sub-Milestone', 'Advance_Percentage', 'Month', 'Notes', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(advances)

def add_advance(milestone_name, sub_milestone_name, advance_percentage, month, notes=''):
    """
    Add advance payment for a milestone.
    
    Args:
        milestone_name: Name of the main milestone
        sub_milestone_name: Name of the sub-milestone
        advance_percentage: Advance percentage (0-100)
        month: Month when advance applies
        notes: Optional notes about the advance
    """
    advances = load_advances()
    
    # Check if advance already exists for this milestone/submilestone/month
    for advance in advances:
        if (advance.get('Milestone') == milestone_name and 
            advance.get('Sub-Milestone') == sub_milestone_name and 
            advance.get('Month') == month):
            # Update existing advance
            advance['Advance_Percentage'] = str(advance_percentage)
            advance['Notes'] = notes
            advance['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_advances(advances)
            return
    
    # Add new advance
    new_advance = {
        'Milestone': milestone_name,
        'Sub-Milestone': sub_milestone_name,
        'Advance_Percentage': str(advance_percentage),
        'Month': month,
        'Notes': notes,
        'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    advances.append(new_advance)
    save_advances(advances)

def delete_advance(milestone_name, sub_milestone_name, month):
    """Delete an advance payment."""
    advances = load_advances()
    advances = [a for a in advances if not (
        a.get('Milestone') == milestone_name and 
        a.get('Sub-Milestone') == sub_milestone_name and 
        a.get('Month') == month
    )]
    save_advances(advances)

def delete_advances_by_milestone(milestone_name, sub_milestone_name=None):
    """
    Delete all advances for a milestone or sub-milestone.
    Used for cascading deletion when a milestone is deleted.
    
    Args:
        milestone_name: Name of the milestone to delete advances for
        sub_milestone_name: Name of the sub-milestone (if None, deletes all for this milestone)
    
    Returns:
        bool: True if any advances were deleted, False otherwise
    """
    advances = load_advances()
    original_count = len(advances)
    
    if sub_milestone_name:
        # Delete advances for specific sub-milestone
        advances = [a for a in advances if not (
            a.get('Milestone') == milestone_name and 
            a.get('Sub-Milestone') == sub_milestone_name
        )]
    else:
        # Delete all advances for this milestone
        advances = [a for a in advances if a.get('Milestone') != milestone_name]
    
    if len(advances) < original_count:
        save_advances(advances)
        return True
    return False

def get_period_months(all_months, period_type, config=None):
    """
    Get months for a specific period (Project / DLP / O&M).
    
    Args:
        all_months: List of all months with years (full timeline)
        period_type: 'project', 'dlp', or 'om'
        config: Project configuration dict
    
    Returns:
        List of months for the specified period
    """
    from timeline_utils import get_project_config
    
    if config is None:
        config = get_project_config()
    
    if not config:
        return all_months
    
    try:
        project_months = int(config.get('Duration_Months', 0))
        dlp_months = int(config.get('DLP_Months', 0))
        om_months = int(config.get('OM_Months', 0))
    except:
        return all_months
    
    if period_type == 'project':
        return all_months[:project_months]
    elif period_type == 'dlp':
        start = project_months
        end = project_months + dlp_months
        return all_months[start:end]
    elif period_type == 'om':
        start = project_months + dlp_months
        return all_months[start:]
    else:
        return all_months

def calculate_advance_months(strategy, period_months, frequency_interval=None, custom_months=None):
    """
    Calculate which months should receive the advance based on strategy.
    
    Args:
        strategy: 'first_month', 'all_months', 'custom', or 'duration'
        period_months: List of months in the selected period
        frequency_interval: For duration strategy: 2, 3, etc. (every N months)
        custom_months: For custom strategy: list of selected months
    
    Returns:
        List of months where advance applies
    """
    if not period_months:
        return []
    
    if strategy == 'first_month':
        return [period_months[0]]
    
    elif strategy == 'all_months':
        return period_months
    
    elif strategy == 'custom':
        # Return only months that are in both custom_months and period_months
        return [m for m in custom_months if m in period_months]
    
    elif strategy == 'duration':
        # Every N months, starting from first month of period
        applicable = []
        for i in range(0, len(period_months), frequency_interval):
            applicable.append(period_months[i])
        return applicable
    
    return [period_months[0]]

def add_advance_with_strategy(milestone_name, sub_milestone_name, advance_percentage, 
                               strategy, period_type, all_months, notes='',
                               frequency_interval=None, custom_months=None):
    """
    Add advance payment with strategy for multiple months.
    Creates individual advance records for each applicable month.
    
    Args:
        milestone_name: Name of the main milestone
        sub_milestone_name: Name of the sub-milestone
        advance_percentage: Advance percentage (0-100)
        strategy: 'first_month', 'all_months', 'custom', or 'duration'
        period_type: 'project', 'dlp', or 'om'
        all_months: List of all months with years (full timeline)
        notes: Optional notes about the advance
        frequency_interval: For duration strategy: 2, 3, etc.
        custom_months: For custom strategy: list of selected months
    
    Returns:
        Number of advance records added
    """
    from timeline_utils import get_project_config
    
    # Get months for the selected period
    period_months = get_period_months(all_months, period_type)
    
    # Calculate which months get the advance
    advance_months = calculate_advance_months(strategy, period_months, frequency_interval, custom_months)
    
    # Add an advance record for each applicable month
    count = 0
    for month in advance_months:
        add_advance(milestone_name, sub_milestone_name, advance_percentage, month, notes)
        count += 1
    
    return count

def get_advance(milestone_name, sub_milestone_name, month):
    """Get advance percentage for a specific milestone/month."""
    advances = load_advances()
    for advance in advances:
        if (advance.get('Milestone') == milestone_name and 
            advance.get('Sub-Milestone') == sub_milestone_name and 
            advance.get('Month') == month):
            try:
                return float(advance.get('Advance_Percentage', 0) or 0)
            except ValueError:
                return 0
    return 0

def get_advances_by_submilestone(milestone_name, sub_milestone_name):
    """Get all advances for a specific sub-milestone."""
    advances = load_advances()
    return [a for a in advances if a.get('Milestone') == milestone_name and a.get('Sub-Milestone') == sub_milestone_name]

def get_all_advances():
    """Get all advance payments."""
    return load_advances()
