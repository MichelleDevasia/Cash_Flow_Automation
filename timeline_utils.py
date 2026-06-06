import csv
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

CONFIG_FILE = 'project_config.csv'

def get_month_list(start_month, start_year, duration_months, om_months=0, dlp_months=0):
    """
    Generate a list of months based on project timeline.
    
    Args:
        start_month: Month name (e.g., 'June')
        start_year: Year as integer (e.g., 2025)
        duration_months: Project duration in months (e.g., 24)
        om_months: O&M period in months (e.g., 60)
        dlp_months: DLP (Data Lifecycle Period) in months (e.g., 24)
    
    Returns:
        List of month strings in format "January 2025", "February 2025", etc.
    """
    MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    
    # Find starting month index
    start_month_idx = MONTHS.index(start_month)
    
    # Calculate total months: project + O&M + DLP
    total_months = duration_months + om_months + dlp_months
    
    month_list = []
    current_date = datetime(start_year, start_month_idx + 1, 1)
    
    for i in range(total_months):
        month_name = current_date.strftime('%B')  # Full month name
        year = current_date.year
        month_list.append(f"{month_name} {year}")
        current_date += relativedelta(months=1)
    
    return month_list

def get_project_config():
    """Load project configuration from session state or file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r', newline='') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if rows:
                return rows[0]
    except:
        pass
    
    return None

def save_project_config(duration_months, start_month, start_year, om_months=0, dlp_months=0, notes=''):
    """Save project configuration to CSV."""
    config = {
        'Duration_Months': duration_months,
        'Start_Month': start_month,
        'Start_Year': start_year,
        'OM_Months': om_months,
        'DLP_Months': dlp_months,
        'Notes': notes,
        'Last_Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    fieldnames = ['Duration_Months', 'Start_Month', 'Start_Year', 'OM_Months', 'DLP_Months', 'Notes', 'Last_Updated']
    
    with open(CONFIG_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(config)

def get_total_months(config=None):
    """Get total number of months (project + O&M + DLP)."""
    if config is None:
        config = get_project_config()
    
    if config:
        try:
            project_months = int(config.get('Duration_Months', 0))
            om_months = int(config.get('OM_Months', 0))
            dlp_months = int(config.get('DLP_Months', 0))
            return project_months + om_months + dlp_months
        except:
            pass
    
    return 12  # Default to 12 months if no config

def get_project_months_only(config=None):
    """Get number of project months only (excluding O&M)."""
    if config is None:
        config = get_project_config()
    
    if config:
        try:
            return int(config.get('Duration_Months', 0))
        except:
            pass
    
    return 12

def get_extended_months(config=None):
    """
    Get extended month list including DLP and O&M periods for calculations with years.
    
    Returns: [Project Months] + [DLP Months] + [O&M Months]
    Example: If project is June 2025-May 2027 (24 months), DLP is 12 months, O&M is 60 months:
    Returns: June 2025, July 2025, ..., May 2027, June 2027, ..., May 2028, June 2028, ..., etc.
    
    Args:
        config: Project configuration dict (if None, loads from file)
    
    Returns:
        List of month names with years in format "Month Year" for full duration (Project + DLP + O&M)
    """
    if config is None:
        config = get_project_config()
    
    if not config:
        # Fallback to 12 months starting from January 2025
        return get_month_list('January', 2025, 12, 0, 0)
    
    try:
        start_month = config.get('Start_Month', 'January')
        start_year = int(config.get('Start_Year', 2025))
        duration_months = int(config.get('Duration_Months', 12))
        dlp_months = int(config.get('DLP_Months', 0))
        om_months = int(config.get('OM_Months', 0))
        
        # Calculate dynamic buffer for credit/collections
        buffer_months = 0
        try:
            from collection_utils import get_collection_months
            buffer_months = max(buffer_months, get_collection_months())
        except:
            pass
            
        try:
            from vendor_payment_utils import load_vendors
            vendors = load_vendors()
            max_vendor_days = 0
            for v in vendors:
                try:
                    days = int(v.get('Credit_Days', 0))
                    if days > max_vendor_days:
                        max_vendor_days = days
                except: pass
            if max_vendor_days > 0:
                buffer_months = max(buffer_months, max(1, max_vendor_days // 30))
        except:
            pass
        
        # Use get_month_list which properly handles years
        # Order: Project -> DLP -> O&M -> Buffer
        return get_month_list(start_month, start_year, duration_months, dlp_months, om_months + buffer_months)
    except:
        return get_month_list('January', 2025, 12, 0, 0)
