"""
Detailed Analysis Generator - Invoice Report Calculation Breakdown
This script analyzes each milestone/submilestone calculation step-by-step
"""

import pandas as pd
from invoice_utils import load_invoices
from matching_utils import load_matches
from activity_utils import load_activities
from cost_sales import load_cost_sales
from calculation_utils import get_calculation_months
from milestone_calculator import calculate_milestone_value_with_details


def generate_detailed_analysis():
    """Generate complete analysis of invoice calculations"""
    
    # Load all data
    invoices = load_invoices()
    matches = load_matches()
    activities = load_activities()
    cost_sales_list = load_cost_sales()
    calc_months = get_calculation_months()
    
    print("=" * 100)
    print("DETAILED INVOICE CALCULATION ANALYSIS")
    print("=" * 100)
    
    # Build lookup tables
    invoice_lookup = {}
    for inv in invoices:
        key = (inv.get('Milestone', ''), inv.get('Sub-Milestone', ''))
        sales_from_str = inv.get('Sales_From_Activities', '')
        sales_from = [a.strip() for a in sales_from_str.split(',')] if sales_from_str and sales_from_str.strip() else []
        invoice_lookup[key] = {
            'pct': float(inv.get('Percentage', 0) or 0),
            'sales_from': sales_from,
            'description': inv.get('Description', '')
        }
    
    act_pct_lookup = {}
    for act in activities:
        key = (act.get('Activity', ''), act.get('Sub-Activity', ''))
        act_pct_lookup[key] = {m: float(act.get(m, 0) or 0) for m in calc_months}
    
    act_sales_lookup = {}
    for item in cost_sales_list:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        sales = float(item.get('Sales', 0) or 0)
        act_sales_lookup[(main_act, sub_act)] = sales
    
    # Group matches by submilestone
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
    
    # Generate report for each milestone
    report = []
    report.append("# DETAILED INVOICE CALCULATION ANALYSIS\n")
    report.append("## Overview\n")
    report.append(f"- Total Milestones in System: {len(set((m, s) for m, s in invoice_lookup.keys()))}\n")
    report.append(f"- Calculation Months: {', '.join(calc_months[:3])}... ({len(calc_months)} total)\n")
    report.append(f"- Calculation Periods: August 2026 - March 2028\n")
    report.append("\n---\n\n")
    
    # Analyze each milestone
    for milestone_key in sorted(activities_by_submilestone.keys()):
        data = activities_by_submilestone[milestone_key]
        milestone = data['milestone']
        sub_milestone = data['sub_milestone']
        matched_activities = data['activities']
        
        inv_info = invoice_lookup.get((milestone, sub_milestone), {})
        milestone_pct = inv_info.get('pct', 0)
        sales_from_list = inv_info.get('sales_from', [])
        description = inv_info.get('description', 'N/A')
        
        report.append(f"## Milestone: {milestone} > {sub_milestone}\n")
        report.append(f"**Milestone %:** {milestone_pct}%\n")
        if description:
            report.append(f"**Description:** {description}\n")
        report.append("\n")
        
        # Section 1: Invoice Formation (Sales Sources)
        report.append("### Stage 1: Milestone Formation - Sales Sources\n")
        report.append(f"Activities selected for sales values: `{sales_from_list}`\n\n")
        report.append("| Activity Name | Sales Value | Found? |\n")
        report.append("|---|---|---|\n")
        
        sales_values = []
        for activity_name in sales_from_list:
            sales_value = 0
            found = False
            for act_key, sale_val in act_sales_lookup.items():
                if act_key[0] == activity_name.strip():
                    sales_value = sale_val
                    found = True
                    break
            sales_values.append(sales_value)
            status = "[YES]" if found else "[NO]"
            report.append(f"| {activity_name.strip()} | ${sales_value:.2f}M | {status} |\n")
        
        report.append("\n")
        
        # Section 2: Invoice Matching (Work Distribution Sources)
        report.append("### Stage 2: Invoice Matching - Work Distribution Sources\n")
        report.append(f"Total matched activities: {len(matched_activities)}\n\n")
        report.append("| Activity | Sub-Activity |\n")
        report.append("|---|---|\n")
        for ma in matched_activities:
            report.append(f"| {ma['activity']} | {ma['sub_activity']} |\n")
        
        report.append("\n")
        
        # Section 3: Sample Month Calculation
        report.append("### Stage 3: Calculation Example (August 2026)\n")
        
        sample_month = calc_months[0] if calc_months else 'August 2026'
        report.append(f"**Month:** {sample_month}\n\n")
        
        # Collect work distribution percentages for sample month
        work_dist_percentages = []
        for matched_activity in matched_activities:
            activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
            activity_pct = act_pct_lookup.get(activity_key, {}).get(sample_month, 0)
            work_dist_percentages.append(activity_pct)
        
        report.append("#### Work Distribution % for Matched Activities\n\n")
        report.append("| Position | Activity | Sub-Activity | Work Distribution % |\n")
        report.append("|---|---|---|---|\n")
        for i, ma in enumerate(matched_activities):
            activity_key = (ma['activity'], ma['sub_activity'])
            activity_pct = act_pct_lookup.get(activity_key, {}).get(sample_month, 0)
            report.append(f"| {i+1} | {ma['activity']} | {ma['sub_activity']} | {activity_pct}% |\n")
        
        report.append("\n")
        
        # Section 4: Pairing and Calculation
        report.append("#### 1-to-1 Pairing & Calculation\n\n")
        report.append("| Pair # | Sales Source (Activity) | Sales Value | × | Work Distribution (Matched Activity) | Work % | = | Contribution |\n")
        report.append("|---|---|---|---|---|---|---|---|\n")
        
        total_contribution = 0
        for i in range(min(len(sales_values), len(matched_activities))):
            sales_val = sales_values[i]
            work_pct = work_dist_percentages[i]
            contribution = sales_val * (work_pct / 100)
            total_contribution += contribution
            
            sales_activity = sales_from_list[i] if i < len(sales_from_list) else "N/A"
            matched_activity = matched_activities[i]
            
            report.append(f"| {i+1} | {sales_activity.strip()} | ${sales_val:.2f}M | × | {matched_activity['activity']} | {work_pct}% | = | ${contribution:.4f}M |\n")
        
        report.append("\n")
        report.append(f"**Sum of Contributions:** ${total_contribution:.4f}M\n\n")
        
        # Section 5: Final Calculation
        report.append("#### Final Calculation\n\n")
        final_value = (milestone_pct / 100) * total_contribution
        report.append(f"**Formula:** Milestone % × (Sum of Contributions)\n")
        report.append(f"**Calculation:** ({milestone_pct}% / 100) × ${total_contribution:.4f}M = **${final_value:.4f}M**\n\n")
        
        # Section 6: Full Year Breakdown (All months)
        report.append("#### Full Year Values (All Calculation Months)\n\n")
        report.append("| Month | Contributions | Sum | Milestone% | Result |\n")
        report.append("|---|---|---|---|---|\n")
        
        for month in calc_months[:6]:  # Show first 6 months
            work_dist_percentages_month = []
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                activity_pct = act_pct_lookup.get(activity_key, {}).get(month, 0)
                work_dist_percentages_month.append(activity_pct)
            
            total_contribution_month = 0
            contributions_str = ""
            for i in range(min(len(sales_values), len(matched_activities))):
                sales_val = sales_values[i]
                work_pct = work_dist_percentages_month[i]
                contribution = sales_val * (work_pct / 100)
                total_contribution_month += contribution
                if contributions_str:
                    contributions_str += " + "
                contributions_str += f"${contribution:.2f}"
            
            final_value_month = (milestone_pct / 100) * total_contribution_month
            report.append(f"| {month} | {contributions_str} | ${total_contribution_month:.4f}M | {milestone_pct}% | **${final_value_month:.4f}M** |\n")
        
        report.append("\n---\n\n")
    
    return "\n".join(report)


if __name__ == "__main__":
    analysis = generate_detailed_analysis()
    
    # Write to file
    with open("INVOICE_CALCULATION_ANALYSIS.md", "w") as f:
        f.write(analysis)
    
    print(analysis)
    print("\n✅ Analysis saved to INVOICE_CALCULATION_ANALYSIS.md")
