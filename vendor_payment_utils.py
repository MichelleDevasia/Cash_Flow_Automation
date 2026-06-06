import csv
import os
from datetime import datetime

CSV_FILE = 'vendor_payment.csv'

def load_vendors():
    """Load vendor bills from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    vendors = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        vendors = list(reader)
    return vendors

def save_vendors(vendors):
    """Save vendor bills to CSV file."""
    if not vendors:
        return
    
    fieldnames = ['Vendor', 'Bill', 'Percentage', 'Credit_Days', 'Cost_From_Activities', 'Description', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(vendors)

def add_vendor_bill(vendor_name, bills_dict, description=''):
    """
    Add new vendor with bills.
    
    Args:
        vendor_name: Name of the vendor
        bills_dict: Dictionary with bill names as keys and dict of {percentage, credit_days, cost_from_activities} as values
        description: Optional description
    """
    vendors = load_vendors()
    
    if not bills_dict or len(bills_dict) == 0:
        # Single vendor without bills
        vendor = {
            'Vendor': vendor_name,
            'Bill': '',
            'Percentage': '100',
            'Credit_Days': '0',
            'Cost_From_Activities': '',
            'Description': description,
            'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        vendors.append(vendor)
    else:
        # Vendor with bills
        for bill_name, bill_data in bills_dict.items():
            vendor = {
                'Vendor': vendor_name,
                'Bill': bill_name,
                'Percentage': str(bill_data.get('percentage', 0)),
                'Credit_Days': str(bill_data.get('credit_days', 0)),
                'Cost_From_Activities': str(bill_data.get('cost_from_activities', '')),
                'Description': description,
                'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            vendors.append(vendor)
    
    save_vendors(vendors)

def delete_vendor(vendor_name, bill_name=''):
    """Delete a vendor or bill."""
    vendors = load_vendors()
    
    if bill_name:
        # Delete specific bill
        vendors = [v for v in vendors if not (v.get('Vendor') == vendor_name and v.get('Bill') == bill_name)]
    else:
        # Delete entire vendor and all bills
        vendors = [v for v in vendors if v.get('Vendor') != vendor_name]
    
    save_vendors(vendors)

def get_vendor_total(vendor_name):
    """Get the total percentage for a vendor's bills."""
    vendors = load_vendors()
    total = 0
    for vendor in vendors:
        if vendor.get('Vendor') == vendor_name:
            try:
                total += float(vendor.get('Percentage', 0))
            except:
                pass
    return total

def get_all_vendors():
    """Get list of all unique vendors."""
    vendors = load_vendors()
    unique_vendors = set()
    for vendor in vendors:
        vendor_name = vendor.get('Vendor', '')
        if vendor_name:
            unique_vendors.add(vendor_name)
    return sorted(list(unique_vendors))

def get_bills(vendor_name):
    """Get all bills for a specific vendor."""
    vendors = load_vendors()
    bills = []
    for vendor in vendors:
        if vendor.get('Vendor') == vendor_name:
            bills.append({
                'name': vendor.get('Bill', ''),
                'percentage': float(vendor.get('Percentage', 0)),
                'credit_days': int(vendor.get('Credit_Days', 0)),
                'cost_from_activities': vendor.get('Cost_From_Activities', ''),
                'description': vendor.get('Description', '')
            })
    return bills

def get_all_bills(vendors_list):
    """
    Extract all bills from vendors list.
    
    Args:
        vendors_list: List of vendor dictionaries from vendor_utils
    
    Returns:
        List of tuples (vendor_name, bill_name, percentage, credit_days, cost_from_activities)
    """
    bills = []
    
    for vendor in vendors_list:
        vendor_name = vendor.get('Vendor', '')
        bill_name = vendor.get('Bill', '')
        percentage = vendor.get('Percentage', '0')
        credit_days = vendor.get('Credit_Days', '0')
        cost_from = vendor.get('Cost_From_Activities', '')
        
        if bill_name:  # Only include actual bills
            bills.append((vendor_name, bill_name, percentage, credit_days, cost_from))
    
    return sorted(bills, key=lambda x: (x[0], x[1]))
