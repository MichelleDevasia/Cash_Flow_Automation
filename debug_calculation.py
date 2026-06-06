"""
Debug script to check calculation data loading
"""
from invoice_utils import load_invoices
from cost_sales import load_cost_sales
from activity_utils import load_activities
from matching_utils import load_matches
import pandas as pd

print("=" * 80)
print("INVOICE DATA")
print("=" * 80)
invoices = load_invoices()
for i, inv in enumerate(invoices[:3]):
    print(f"\nInvoice {i}:")
    print(f"  Milestone: {inv.get('Milestone')}")
    print(f"  Sub-Milestone: {inv.get('Sub-Milestone')}")
    print(f"  Percentage: {inv.get('Percentage')}")
    print(f"  Sales_From_Activities: {inv.get('Sales_From_Activities')}")

print("\n" + "=" * 80)
print("COST SALES DATA")
print("=" * 80)
cost_sales = load_cost_sales()
for i, cs in enumerate(cost_sales[:5]):
    print(f"\nActivity {i}:")
    print(f"  Activity: '{cs.get('Activity')}'")
    print(f"  Sub-Activity: '{cs.get('Sub-Activity')}'")
    print(f"  Sales: {cs.get('Sales')}")

print("\n" + "=" * 80)
print("ACTIVITIES DATA (Sample)")
print("=" * 80)
activities = load_activities()
for i, act in enumerate(activities[:5]):
    print(f"\nActivity {i}:")
    print(f"  Activity: '{act.get('Activity')}'")
    print(f"  Sub-Activity: '{act.get('Sub-Activity')}'")
    print(f"  August 2026: {act.get('August 2026')}")

print("\n" + "=" * 80)
print("MATCHING DATA (Sample)")
print("=" * 80)
matches = load_matches()
for i, match in enumerate(matches[:5]):
    print(f"\nMatch {i}:")
    print(f"  Milestone: {match.get('Milestone')}")
    print(f"  Sub-Milestone: {match.get('Sub-Milestone')}")
    print(f"  Activity: '{match.get('Activity')}'")
    print(f"  Sub-Activity: '{match.get('Sub-Activity')}'")

print("\n" + "=" * 80)
print("TESTING NAME MATCHING")
print("=" * 80)

# Get first invoice and its sales_from list
first_invoice = invoices[0]
sales_from_str = first_invoice.get('Sales_From_Activities', '')
import re
sales_from_list = [a.strip() for a in re.split(r',(?![^(]*\))', sales_from_str)] if sales_from_str and sales_from_str.strip() else []

print(f"\nInvoice: {first_invoice.get('Milestone')} > {first_invoice.get('Sub-Milestone')}")
print(f"Sales_From_Activities: {sales_from_list}")

# Try to find sales values for each
act_sales_lookup = {}
for item in cost_sales:
    main_act = item.get('Activity', '')
    sub_act = item.get('Sub-Activity', '')
    sales = float(item.get('Sales', 0) or 0)
    act_sales_lookup[(main_act, sub_act)] = sales

print("\nLooking for sales values:")
for activity_name in sales_from_list:
    print(f"\n  Searching for: '{activity_name}'")
    found = False
    for act_key, sale_val in act_sales_lookup.items():
        if act_key[0] == activity_name.strip():
            print(f"    ✓ FOUND in '{act_key[0]}' = ${sale_val}")
            found = True
            break
    if not found:
        print(f"    ✗ NOT FOUND")
        # Show similar names
        print(f"    Available names in cost_sales:")
        for act_key in act_sales_lookup.keys():
            print(f"      - '{act_key[0]}'")

print("\n" + "=" * 80)
print("TESTING MATCHED ACTIVITIES LOOKUP")
print("=" * 80)

# Get first matching record
first_match = matches[0]
print(f"\nFirst match:")
print(f"  Milestone: {first_match.get('Milestone')}")
print(f"  Sub-Milestone: {first_match.get('Sub-Milestone')}")
print(f"  Activity: '{first_match.get('Activity')}'")
print(f"  Sub-Activity: '{first_match.get('Sub-Activity')}'")

act_pct_lookup = {}
for act in activities:
    key = (act.get('Activity', ''), act.get('Sub-Activity', ''))
    act_pct_lookup[key] = {
        'August 2026': float(act.get('August 2026', 0) or 0)
    }

activity_key = (first_match.get('Activity', ''), first_match.get('Sub-Activity', ''))
print(f"\nLooking up activity key: {activity_key}")
if activity_key in act_pct_lookup:
    print(f"✓ FOUND: {act_pct_lookup[activity_key]}")
else:
    print(f"✗ NOT FOUND")
    print(f"Available keys in act_pct_lookup:")
    for key in list(act_pct_lookup.keys())[:10]:
        print(f"  - {key}")
