import csv
import os
from datetime import datetime

CSV_FILE = 'vendor_payment_advance.csv'

def load_vendor_advances():
    """Load vendor payment advances from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    advances = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        advances = list(reader)
    return advances

def save_vendor_advances(advances):
    """Save vendor payment advances to CSV file."""
    if not advances:
        # Create empty file with headers
        fieldnames = ['Vendor', 'Bill', 'Advance_Percentage', 'Application_Strategy', 'Period', 'Months', 'Notes', 'Last Updated']
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        return
    
    fieldnames = ['Vendor', 'Bill', 'Advance_Percentage', 'Application_Strategy', 'Period', 'Months', 'Notes', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(advances)

def add_or_update_vendor_advance(vendor_name, bill_name, advance_percentage, strategy, period, months, notes=''):
    """
    Add or update vendor payment advance.
    
    Args:
        vendor_name: Name of vendor
        bill_name: Name of bill
        advance_percentage: Advance percentage (0-100)
        strategy: Strategy used ('first_month', 'all_months', 'duration_pattern', 'custom')
        period: Period applied ('project', 'dlp', 'oam')
        months: Comma-separated list of months or pattern (e.g., "1,2,3" or "every_2_months")
        notes: Optional notes
    """
    advances = load_vendor_advances()
    
    # Check if advance already exists
    existing = None
    for advance in advances:
        if advance.get('Vendor') == vendor_name and advance.get('Bill') == bill_name:
            existing = advance
            break
    
    if existing:
        # Update existing
        existing['Advance_Percentage'] = str(advance_percentage)
        existing['Application_Strategy'] = strategy
        existing['Period'] = period
        existing['Months'] = months
        existing['Notes'] = notes
        existing['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        # Create new
        new_advance = {
            'Vendor': vendor_name,
            'Bill': bill_name,
            'Advance_Percentage': str(advance_percentage),
            'Application_Strategy': strategy,
            'Period': period,
            'Months': months,
            'Notes': notes,
            'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        advances.append(new_advance)
    
    save_vendor_advances(advances)
    return True

def get_vendor_advance(vendor_name, bill_name):
    """Get advance for specific vendor/bill."""
    advances = load_vendor_advances()
    for advance in advances:
        if advance.get('Vendor') == vendor_name and advance.get('Bill') == bill_name:
            return advance
    return None

def delete_vendor_advance(vendor_name, bill_name):
    """Delete vendor payment advance."""
    advances = load_vendor_advances()
    advances = [a for a in advances if not (
        a.get('Vendor') == vendor_name and 
        a.get('Bill') == bill_name
    )]
    save_vendor_advances(advances)

def delete_vendor_advances_by_vendor(vendor_name, bill_name=None):
    """
    Delete all advances for a vendor or specific bill.
    Used for cascading deletion when a vendor/bill is deleted.
    
    Args:
        vendor_name: Name of the vendor
        bill_name: Name of the bill (if None, deletes all for vendor)
    
    Returns:
        bool: True if any advances were deleted
    """
    advances = load_vendor_advances()
    original_count = len(advances)
    
    if bill_name:
        advances = [a for a in advances if not (
            a.get('Vendor') == vendor_name and 
            a.get('Bill') == bill_name
        )]
    else:
        advances = [a for a in advances if a.get('Vendor') != vendor_name]
    
    if len(advances) < original_count:
        save_vendor_advances(advances)
        return True
    return False

def get_all_vendor_advances():
    """Get all vendor payment advances."""
    return load_vendor_advances()
