"""
Detailed Invoice Report Analysis
Traces through each milestone/submilestone calculation step-by-step
"""

import pandas as pd
from invoice_utils import load_invoices
from matching_utils import load_matches
from cost_sales import load_cost_sales
from activity_utils import load_activities
from calculation_utils import get_calculation_months
from milestone_calculator import calculate_milestone_value_with_details


def analyze_invoice_calculations():
    """
    Complete analysis of invoice calculations with detailed tracing
    """
    
    # Load all data
    invoices = load_invoices()
    matches = load_matches()
    cost_sales = load_cost_sales()
    activities = load_activities()
    calc_months = get_calculation_months()
    
    print("=" * 100)
    print("DETAILED INVOICE REPORT ANALYSIS")
    print("=" * 100)
    
    # Create lookup tables
    print("\n" + "=" * 100)
    print("1. DATA LOADING VERIFICATION")
    print("=" * 100)
    print(f"✓ Loaded {len(invoices)} invoices")
    print(f"✓ Loaded {len(matches)} activity matches")
    print(f"✓ Loaded {len(cost_sales)} cost_sales entries")
    print(f"✓ Loaded {len(activities)} activities")
    print(f"✓ Calculation months: {calc_months[:3]}... (total: {len(calc_months)})")
    
    # Create cost_sales lookup
    act_sales_lookup = {}
    for item in cost_sales:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        sales = float(item.get('Sales', 0) or 0)
        act_sales_lookup[(main_act, sub_act)] = sales
    
    # Create activities lookup for percentages
    act_pct_lookup = {}
    for act in activities:
        key = (act.get('Activity', ''), act.get('Sub-Activity', ''))
        act_pct_lookup[key] = {m: float(act.get(m, 0) or 0) for m in calc_months}
    
    print(f"\n✓ Created sales lookup with {len(act_sales_lookup)} entries")
    print(f"✓ Created activity percentage lookup with {len(act_pct_lookup)} entries")
    
    # Organize matches by milestone/submilestone
    activities_by_submilestone = {}
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        sub_milestone = match.get('Sub-Milestone', '')
        milestone = match.get('Milestone', '')
        
        if not all([activity, sub_milestone, milestone]):
            continue
            
        key = f"{milestone} > {sub_milestone}"
        if key not in activities_by_submilestone:
            activities_by_submilestone[key] = {
                'milestone': milestone,
                'sub_milestone': sub_milestone,
                'activities': []
            }
        activities_by_submilestone[key]['activities'].append({
            'activity': activity,
            'sub_activity': sub_activity
        })
    
    print(f"✓ Organized matches into {len(activities_by_submilestone)} milestone/submilestone combinations")
    
    # Process each milestone
    print("\n" + "=" * 100)
    print("2. INVOICE CONFIGURATION - MILESTONES & SALES SOURCES")
    print("=" * 100)
    
    invoice_lookup = {}
    for inv in invoices:
        key = (inv.get('Milestone', ''), inv.get('Sub-Milestone', ''))
        sales_from_str = inv.get('Sales_From_Activities', '')
        import re
        sales_from = [a.strip() for a in re.split(r',(?![^(]*\))', sales_from_str)] if sales_from_str and sales_from_str.strip() else []
        invoice_lookup[key] = {
            'pct': float(inv.get('Percentage', 0) or 0),
            'sales_from': sales_from,
            'description': inv.get('Description', '')
        }
        
        print(f"\n📋 MILESTONE: {inv.get('Milestone', '')} | SUB-MILESTONE: {inv.get('Sub-Milestone', '')}")
        print(f"   Percentage: {inv.get('Percentage', 0)}%")
        print(f"   Sales Sources (from Sales_From_Activities):")
        for i, activity in enumerate(sales_from, 1):
            print(f"      {i}. {activity}")
    
    # Detailed analysis for each milestone
    print("\n" + "=" * 100)
    print("3. DETAILED CALCULATION FOR EACH MILESTONE")
    print("=" * 100)
    
    for key_idx, (key, data) in enumerate(activities_by_submilestone.items(), 1):
        milestone = data['milestone']
        sub_milestone = data['sub_milestone']
        
        print(f"\n{'='*100}")
        print(f"MILESTONE {key_idx}: {milestone} > {sub_milestone}")
        print(f"{'='*100}")
        
        # Get invoice info
        inv_info = invoice_lookup.get((milestone, sub_milestone), {'pct': 0, 'sales_from': []})
        milestone_pct = inv_info['pct']
        sales_from_list = inv_info['sales_from']
        
        print(f"\n📊 MILESTONE CONFIGURATION:")
        print(f"   Milestone %: {milestone_pct}%")
        print(f"   Sales Sources (Sales_From_Activities):")
        for i, act_name in enumerate(sales_from_list, 1):
            print(f"      {i}. {act_name}")
        
        # Get matched activities
        matched_activities = data['activities']
        print(f"\n🔗 MATCHED ACTIVITIES (from Matching File):")
        for i, act in enumerate(matched_activities, 1):
            print(f"      {i}. {act['activity']} | {act['sub_activity']}")
        
        # Collect sales values
        print(f"\n💰 COLLECTING SALES VALUES FROM COST_SALES:")
        sales_values = []
        for i, activity_name in enumerate(sales_from_list, 1):
            sales_value = 0
            found_in = None
            for act_key, sale_val in act_sales_lookup.items():
                if act_key[0] == activity_name.strip():
                    sales_value = sale_val
                    found_in = act_key
                    break
            sales_values.append(sales_value)
            status = "✓ FOUND" if found_in else "✗ NOT FOUND"
            print(f"      {i}. Sales from '{activity_name}': ${sales_value:.2f} ({status})")
            if found_in:
                print(f"         Matched: {found_in[0]} | {found_in[1]}")
        
        # Show calculation for first month only (sample)
        first_month = calc_months[0] if calc_months else None
        if first_month:
            print(f"\n📈 SAMPLE CALCULATION FOR {first_month}:")
            
            # Collect work distribution percentages
            work_dist_percentages = []
            print(f"   Collecting Work Distribution % from Matched Activities:")
            for i, matched_activity in enumerate(matched_activities, 1):
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                activity_pct = act_pct_lookup.get(activity_key, {}).get(first_month, 0)
                work_dist_percentages.append(activity_pct)
                print(f"      {i}. {matched_activity['activity']} > {matched_activity['sub_activity']}: {activity_pct}%")
            
            # Calculate
            print(f"\n   FORMULA APPLICATION:")
            print(f"   {milestone_pct}% × [(Sales₁ × Work%₁) + (Sales₂ × Work%₂) + ...]")
            print(f"\n   STEP-BY-STEP:")
            
            contribution_sum = 0
            for i in range(min(len(sales_values), len(work_dist_percentages))):
                sales = sales_values[i]
                work_pct = work_dist_percentages[i]
                contribution = sales * (work_pct / 100)
                contribution_sum += contribution
                print(f"      Pair {i+1}: ${sales:.2f} × {work_pct}% = ${contribution:.2f}")
            
            final_value = (milestone_pct / 100) * contribution_sum
            print(f"\n   Sum of contributions: ${contribution_sum:.2f}")
            print(f"   ({milestone_pct}/100) × ${contribution_sum:.2f} = ${final_value:.2f}")
            print(f"\n   ✓ FINAL CALCULATED VALUE FOR {first_month}: ${final_value:.2f}")
        
        # Show all months calculation
        print(f"\n📅 CALCULATIONS FOR ALL MONTHS:")
        print(f"{'Month':<20} | {'Sales1×Work%1':<15} | {'Sales2×Work%2':<15} | {'Sum':<15} | {'Milestone %':<15} | {'Final Value':<15}")
        print(f"{'-'*100}")
        
        for month in calc_months[:6]:  # Show first 6 months
            work_dist_percentages = []
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                activity_pct = act_pct_lookup.get(activity_key, {}).get(month, 0)
                work_dist_percentages.append(activity_pct)
            
            contributions = []
            for i in range(min(len(sales_values), len(work_dist_percentages))):
                sales = sales_values[i]
                work_pct = work_dist_percentages[i]
                contribution = sales * (work_pct / 100)
                contributions.append(contribution)
            
            contribution_sum = sum(contributions)
            final_value = (milestone_pct / 100) * contribution_sum
            
            contrib_str = " + ".join([f"${c:.2f}" for c in contributions])
            print(f"{month:<20} | {contrib_str:<15} | {'':<15} | ${contribution_sum:<14.2f} | {milestone_pct}%{'':<10} | ${final_value:<14.2f}")


if __name__ == "__main__":
    analyze_invoice_calculations()
