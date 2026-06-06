import csv
import os
from datetime import datetime

CSV_FILE = 'invoice.csv'

def load_invoices():
    """Load invoice milestones from CSV file."""
    if not os.path.exists(CSV_FILE):
        return []
    
    invoices = []
    with open(CSV_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        invoices = list(reader)
    return invoices

def save_invoices(invoices):
    """Save invoice milestones to CSV file."""
    if not invoices:
        return
    
    fieldnames = ['Milestone', 'Sub-Milestone', 'Percentage', 'Sales_From_Activities', 'Description', 'Last Updated']
    
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(invoices)

def add_invoice_milestone(milestone_name, sub_milestones_dict, description='', sub_milestones_activities_dict=None):
    """
    Add new invoice milestone with sub-milestones.
    
    Args:
        milestone_name: Name of the main milestone
        sub_milestones_dict: Dictionary with sub-milestone names as keys and percentages as values
        description: Optional description
        sub_milestones_activities_dict: Dictionary mapping sub-milestone names to comma-separated activity strings
    """
    if sub_milestones_activities_dict is None:
        sub_milestones_activities_dict = {}
    
    invoices = load_invoices()
    
    if not sub_milestones_dict or len(sub_milestones_dict) == 0:
        # Single milestone without sub-milestones
        invoice = {
            'Milestone': milestone_name,
            'Sub-Milestone': '',
            'Percentage': '100',
            'Sales_From_Activities': '',
            'Description': description,
            'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        invoices.append(invoice)
    else:
        # Milestone with sub-milestones
        for sub_name, percentage in sub_milestones_dict.items():
            invoice = {
                'Milestone': milestone_name,
                'Sub-Milestone': sub_name,
                'Percentage': str(percentage),
                'Sales_From_Activities': sub_milestones_activities_dict.get(sub_name, ''),
                'Description': description,
                'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            invoices.append(invoice)
    
    save_invoices(invoices)

def delete_milestone(milestone_name, sub_milestone=''):
    """Delete a milestone or sub-milestone."""
    invoices = load_invoices()
    
    if sub_milestone:
        # Delete specific sub-milestone
        invoices = [i for i in invoices if not (i.get('Milestone') == milestone_name and i.get('Sub-Milestone') == sub_milestone)]
    else:
        # Delete entire milestone and all sub-milestones
        invoices = [i for i in invoices if i.get('Milestone') != milestone_name]
    
    save_invoices(invoices)

def get_milestone_total(milestone_name):
    """Get the total percentage for a milestone's sub-milestones."""
    invoices = load_invoices()
    total = 0
    for invoice in invoices:
        if invoice.get('Milestone') == milestone_name:
            try:
                total += float(invoice.get('Percentage', 0))
            except ValueError:
                pass
    return total

def get_all_milestones():
    """Get list of all unique milestone names."""
    invoices = load_invoices()
    milestones = sorted(set([i.get('Milestone', '') for i in invoices if i.get('Milestone', '')]))
    return milestones

def get_submilestones(milestone_name):
    """Get all sub-milestones for a specific milestone."""
    invoices = load_invoices()
    subs = []
    for invoice in invoices:
        if invoice.get('Milestone') == milestone_name:
            sub = invoice.get('Sub-Milestone', '')
            if sub:
                subs.append({
                    'name': sub,
                    'percentage': float(invoice.get('Percentage', 0)),
                    'description': invoice.get('Description', '')
                })
    return subs

def update_invoice_milestone(old_milestone_name, old_sub_milestone, new_milestone_name, new_sub_milestone, percentage, description='', sales_from_activities=''):
    """Update an existing invoice milestone."""
    invoices = load_invoices()
    
    # Find and update
    for invoice in invoices:
        if invoice.get('Milestone') == old_milestone_name and invoice.get('Sub-Milestone') == old_sub_milestone:
            invoice['Milestone'] = new_milestone_name
            invoice['Sub-Milestone'] = new_sub_milestone
            invoice['Percentage'] = str(percentage)
            invoice['Sales_From_Activities'] = sales_from_activities
            invoice['Description'] = description
            invoice['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            break
    
    save_invoices(invoices)
