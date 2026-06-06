"""
Simple test to verify calculations are working
"""
from calculation_utils import calculate_invoicing_table, calculate_vendor_payment_table

print("Testing Invoice Calculation...")
invoice_results = calculate_invoicing_table()

print(f"\nTotal invoice calculations: {len(invoice_results)}")
for key in list(invoice_results.keys())[:3]:
    values = invoice_results[key]
    non_zero_months = [m for m, v in values.items() if v and (isinstance(v, (int, float)) and v != 0)]
    print(f"\n{key}:")
    print(f"  Total months with data: {len(non_zero_months)}")
    if non_zero_months:
        sample_month = non_zero_months[0]
        val = values[sample_month]
        print(f"  Sample ({sample_month}): {val} (type: {type(val).__name__})")

print("\n" + "="*80)
print("Testing Vendor Payment Calculation...")
vendor_results = calculate_vendor_payment_table()

print(f"\nTotal vendor calculations: {len(vendor_results)}")
for key in list(vendor_results.keys())[:3]:
    values = vendor_results[key]
    non_zero_months = [m for m, v in values.items() if v and (isinstance(v, (int, float)) and v != 0)]
    print(f"\n{key}:")
    print(f"  Total months with data: {len(non_zero_months)}")
    if non_zero_months:
        sample_month = non_zero_months[0]
        val = values[sample_month]
        print(f"  Sample ({sample_month}): {val} (type: {type(val).__name__})")
