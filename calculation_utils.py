import pandas as pd
from activity_utils import load_activities, MONTHS
from invoice_utils import load_invoices
from matching_utils import load_matches
from cost_sales import load_cost_sales
from vendor_payment_utils import load_vendors
from vendor_payment_matching_utils import load_vendor_matches
from timeline_utils import get_extended_months, get_project_config
from milestone_calculator import calculate_milestone_value

def extract_month_name(month_with_year):
    """
    Extract month name from 'Month Year' format.
    
    Args:
        month_with_year: String in format "June 2025"
    
    Returns:
        Just the month name part (e.g., "June")
    """
    if not month_with_year:
        return month_with_year
    
    parts = str(month_with_year).split()
    return parts[0] if parts else month_with_year

def get_calculation_months():
    """
    Get the list of months for calculations (including O&M period).
    Uses extended months if project config exists, otherwise defaults to 12 months.
    """
    try:
        config = get_project_config()
        if config:
            extended = get_extended_months(config)
            if extended:
                return extended
    except:
        pass
    
    return MONTHS  # Fallback to 12 months

def parse_sales_activities(sales_from_str, cost_sales_list):
    """
    Parse Sales_From_Activities string into a list of activity names,
    handling commas inside activity names by matching against known activity names.
    """
    if not sales_from_str or not sales_from_str.strip():
        return []
        
    all_known_activities = sorted(list(set([item.get('Activity', '').strip() for item in cost_sales_list if item.get('Activity', '')])), key=len, reverse=True)
    
    found_matches = []
    temp_str = sales_from_str
    for act in all_known_activities:
        if act in temp_str:
            pos = sales_from_str.find(act)
            found_matches.append((pos, act))
            temp_str = temp_str.replace(act, " " * len(act))
            
    found_matches.sort()
    return [name for pos, name in found_matches]

def add_total_and_cumulative(df):
    """
    Add Row Total column and Total/Cumulative rows to a DataFrame with month columns.
    
    - Row Total column: Sum of all months for each row
    - Total row: Sum of all rows for each month, and sum of all row totals
    - Cumulative row (last): Running total across months (month totals only)
      - January = January's total
      - February = January's cumulative + February's total
      - March = February's cumulative + March's total, etc.
      - Row Total column is left empty for cumulative row
    
    Args:
        df: DataFrame with months as columns
    
    Returns:
        DataFrame with Row Total column and Total/Cumulative rows at the bottom
    """
    if df.empty:
        return df
    
    # Get calculation months (including O&M period with years like "June 2025")
    calc_months = get_calculation_months()
    
    # Reset index if the index has a name and is not a RangeIndex
    result_df = df.copy()
    index_col = None
    
    if result_df.index.name and not isinstance(result_df.index, pd.RangeIndex):
        index_col = result_df.index.name
        result_df = result_df.reset_index()
    
    # Find the index/name column if not already set
    if not index_col:
        # Pick the first non-month, non-Row Total column as the row label column
        for col in result_df.columns:
            if col not in calc_months and col != 'Row Total':
                index_col = col
                break
    
    # Remove any existing TOTAL, CUMULATIVE, and Row Total rows/columns to avoid double-counting
    if index_col and index_col in result_df.columns:
        result_df = result_df[~result_df[index_col].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Remove Row Total column if it already exists
    if 'Row Total' in result_df.columns:
        result_df = result_df.drop('Row Total', axis=1)
    
    if result_df.empty:
        return result_df
    
    # Ensure numeric types for all month columns (use calc_months directly, not extracted names)
    for month in calc_months:
        if month in result_df.columns:
            result_df[month] = pd.to_numeric(result_df[month], errors='coerce').fillna(0)
    
    # Move index_col to first position
    if index_col and index_col in result_df.columns:
        cols = result_df.columns.tolist()
        cols.remove(index_col)
        result_df = result_df[[index_col] + cols]
    
    # Add Row Total column (sum of all months for each row)
    result_df.insert(1, 'Row Total', 0.0)
    
    for idx, row in result_df.iterrows():
        row_sum = 0
        for month in calc_months:
            if month in result_df.columns:
                row_sum += float(row[month]) if pd.notna(row[month]) else 0
        result_df.at[idx, 'Row Total'] = row_sum
    
    # Calculate TOTAL row (sum of all rows for each month)
    total_row = {}
    if index_col:
        total_row[index_col] = 'TOTAL'
    
    total_row['Row Total'] = result_df['Row Total'].sum()  # Sum of all row totals
    
    for month in calc_months:
        if month in result_df.columns:
            total_row[month] = result_df[month].sum()
        else:
            total_row[month] = 0
    
    # Create TOTAL row DataFrame
    total_df = pd.DataFrame([total_row])
    result_df = pd.concat([result_df, total_df], ignore_index=True)
    
    # Calculate CUMULATIVE row (running sum across months, no row total)
    cumulative_row = {}
    if index_col:
        cumulative_row[index_col] = 'CUMULATIVE'
    
    cumulative_row['Row Total'] = None  # Use None instead of empty string for PyArrow compatibility
    
    running_total = 0
    for month in calc_months:
        if month in result_df.columns:
            # Get the month total from TOTAL row
            if index_col:
                total_mask = result_df[index_col] == 'TOTAL'
                month_total_rows = result_df[total_mask]
                
                if len(month_total_rows) > 0:
                    month_total = month_total_rows[month].values[0]
                    running_total += float(month_total) if pd.notna(month_total) else 0
            
            cumulative_row[month] = running_total
        else:
            cumulative_row[month] = 0
    
    # Create CUMULATIVE row DataFrame
    cumulative_df = pd.DataFrame([cumulative_row])
    result_df = pd.concat([result_df, cumulative_df], ignore_index=True)
    
    return result_df

def get_activity_sales(activity_name, sub_activity_name=''):
    """Get sales value for an activity/sub-activity."""
    cost_sales = load_cost_sales()
    
    for item in cost_sales:
        if item.get('Activity', '') == activity_name:
            if sub_activity_name:
                if item.get('Sub-Activity', '') == sub_activity_name:
                    try:
                        return float(item.get('Sales', 0) or 0)
                    except:
                        return 0
            else:
                if item.get('Sub-Activity', '') == '':
                    try:
                        return float(item.get('Sales', 0) or 0)
                    except:
                        return 0
    return 0

def get_activity_percentages(activity_name, sub_activity_name=''):
    """Get monthly percentages for an activity/sub-activity.
    
    Returns a dictionary where keys are month names with years (e.g., "June 2025")
    to match the calc_months format.
    """
    activities = load_activities()
    calc_months = get_calculation_months()
    
    for activity in activities:
        if activity.get('Activity', '') == activity_name:
            if sub_activity_name:
                if activity.get('Sub-Activity', '') == sub_activity_name:
                    result = {}
                    for month_with_year in calc_months:
                        result[month_with_year] = float(activity.get(month_with_year, 0) or 0)
                    return result
            else:
                if activity.get('Sub-Activity', '') == '':
                    result = {}
                    for month_with_year in calc_months:
                        result[month_with_year] = float(activity.get(month_with_year, 0) or 0)
                    return result
    
    # Return zero percentages if not found (with full "Month Year" keys)
    return {month: 0 for month in calc_months}

def get_submilestone_percentage(milestone_name, sub_milestone_name):
    """Get percentage for a sub-milestone."""
    invoices = load_invoices()
    
    for invoice in invoices:
        if invoice.get('Milestone', '') == milestone_name:
            if invoice.get('Sub-Milestone', '') == sub_milestone_name:
                try:
                    return float(invoice.get('Percentage', 0) or 0)
                except:
                    return 0
    return 0

def get_sales_from_activities(milestone_name, sub_milestone_name):
    """
    Get the comma-separated list of activities to use for sales calculation.
    
    Returns:
        List of activity names to use for sales, or empty list if none specified
    """
    invoices = load_invoices()
    cost_sales_list = load_cost_sales()
    
    for invoice in invoices:
        if invoice.get('Milestone', '') == milestone_name:
            if invoice.get('Sub-Milestone', '') == sub_milestone_name:
                sales_from_str = invoice.get('Sales_From_Activities', '')
                return parse_sales_activities(sales_from_str, cost_sales_list)
    return []

def get_total_sales_from_activities(activity_list):
    """
    Calculate total sales from multiple activities.
    
    Args:
        activity_list: List of activity names
    
    Returns:
        Sum of sales values from all activities in the list
    """
    total_sales = 0
    for activity in activity_list:
        # Try to get sales for activity without sub-activity
        sales = get_activity_sales(activity, '')
        total_sales += sales
    return total_sales

def calculate_invoicing_table():
    """
    Calculate the invoicing table based on matches and formulas.
    """
    calc_months = get_calculation_months()
    matches = load_matches()
    invoices = load_invoices()
    activities_list = load_activities()
    cost_sales_list = load_cost_sales()
    
    invoice_lookup = {}
    for inv in invoices:
        key = (inv.get('Milestone', ''), inv.get('Sub-Milestone', ''))
        sales_from_str = inv.get('Sales_From_Activities', '')
        sales_from = parse_sales_activities(sales_from_str, cost_sales_list)
        invoice_lookup[key] = {
            'pct': float(inv.get('Percentage', 0) or 0),
            'sales_from': sales_from
        }
        
    act_pct_lookup = {}
    for act in activities_list:
        key = (act.get('Activity', ''), act.get('Sub-Activity', ''))
        act_pct_lookup[key] = {m: float(act.get(m, 0) or 0) for m in calc_months}
        
    act_sales_lookup = {}
    for item in cost_sales_list:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        sales = float(item.get('Sales', 0) or 0)
        act_sales_lookup[(main_act, sub_act)] = sales

    activities_by_submilestone = {}
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        sub_milestone = match.get('Sub-Milestone', '')
        milestone = match.get('Milestone', '')
        if not all([activity, sub_milestone, milestone]): continue
        key = f"{milestone} > {sub_milestone}"
        if key not in activities_by_submilestone:
            activities_by_submilestone[key] = {'milestone': milestone, 'sub_milestone': sub_milestone, 'activities': []}
        activities_by_submilestone[key]['activities'].append({'activity': activity, 'sub_activity': sub_activity})
        
    results = {}
    for key, data in activities_by_submilestone.items():
        milestone = data['milestone']
        sub_milestone = data['sub_milestone']
        inv_info = invoice_lookup.get((milestone, sub_milestone), {'pct': 0, 'sales_from': []})
        submilestone_pct = inv_info['pct']
        sales_from_list = inv_info.get('sales_from', [])
        matched_activities = data['activities']  # Activities from matching file
        
        # Get sales values from Sales_From_Activities
        sales_values = []
        if sales_from_list:
            for activity_name in sales_from_list:
                activity_name_stripped = activity_name.strip()
                sales_value = 0
                for (main_act, sub_act), sale_val in act_sales_lookup.items():
                    if main_act == activity_name_stripped:
                        sales_value = sale_val
                        break
                else:
                    for (main_act, sub_act), sale_val in act_sales_lookup.items():
                        full_name = f"{main_act} {sub_act}".strip() if sub_act else main_act
                        if full_name == activity_name_stripped:
                            sales_value = sale_val
                            break
                sales_values.append(sales_value)
        else:
            # Fallback to matched activities (same set as matched activities)
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                sales_value = act_sales_lookup.get(activity_key, 0)
                sales_values.append(sales_value)
        
        results[key] = {month: 0 for month in calc_months}
        for month in calc_months:
            # Collect work distribution percentages from matched activities
            work_dist_percentages = []
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                activity_pct = act_pct_lookup.get(activity_key, {}).get(month, 0)
                work_dist_percentages.append(activity_pct)
            
            # Calculate using milestone calculator: Milestone% × [(Sales₁ × Work%₁) + (Sales₂ × Work%₂) + ...]
            results[key][month] = calculate_milestone_value(
                submilestone_pct,
                sales_values,
                work_dist_percentages
            )
                
    if not results: return pd.DataFrame()
    data = [{'Sub-Milestone': key, **months_data} for key, months_data in results.items()]
    return add_total_and_cumulative(pd.DataFrame(data))
def calculate_by_milestone():
    """
    Calculate totals grouped by milestone.
    
    Uses the invoicing table calculation and sums by milestone.
    
    Returns: DataFrame with milestones as rows and months as columns, showing total values per milestone
    """
    calc_months = get_calculation_months()
    
    # Use the invoicing table which already has correct calculation
    invoicing_df = calculate_invoicing_table()
    
    if invoicing_df.empty:
        return pd.DataFrame()
    
    # Filter out TOTAL row if it exists
    invoicing_df = invoicing_df[invoicing_df['Sub-Milestone'] != 'TOTAL'].copy()
    
    # Parse milestone from 'Sub-Milestone' column (format: "Milestone > Sub-Milestone")
    results = {}
    
    for _, row in invoicing_df.iterrows():
        sub_milestone_key = row['Sub-Milestone']
        milestone_name = sub_milestone_key.split(' > ')[0]
        
        if milestone_name not in results:
            results[milestone_name] = {month: 0 for month in calc_months}
        
        # Add this sub-milestone's values to the milestone total
        for month in calc_months:
            if month in row:
                results[milestone_name][month] += row[month]
    
    # Convert to DataFrame
    data = []
    for milestone, months_data in results.items():
        row = {'Milestone': milestone}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_by_activity():
    """
    Calculate totals grouped by activity.
    """
    calc_months = get_calculation_months()
    matches = load_matches()
    invoices = load_invoices()
    activities_list = load_activities()
    cost_sales_list = load_cost_sales()
    
    invoice_lookup = {}
    for inv in invoices:
        key = (inv.get('Milestone', ''), inv.get('Sub-Milestone', ''))
        sales_from_str = inv.get('Sales_From_Activities', '')
        sales_from = parse_sales_activities(sales_from_str, cost_sales_list)
        invoice_lookup[key] = {
            'pct': float(inv.get('Percentage', 0) or 0),
            'sales_from': sales_from
        }
        
    act_pct_lookup = {}
    for act in activities_list:
        key = (act.get('Activity', ''), act.get('Sub-Activity', ''))
        act_pct_lookup[key] = {m: float(act.get(m, 0) or 0) for m in calc_months}
        
    act_sales_lookup = {}
    act_sales_by_main_act = {}
    for item in cost_sales_list:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        sales = float(item.get('Sales', 0) or 0)
        act_sales_lookup[(main_act, sub_act)] = sales
        if main_act not in act_sales_by_main_act:
            act_sales_by_main_act[main_act] = 0
        act_sales_by_main_act[main_act] += sales

    def fast_get_total_sales(sales_from_list):
        return sum(act_sales_by_main_act.get(a, 0) for a in sales_from_list)

    activities_by_submilestone = {}
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        sub_milestone = match.get('Sub-Milestone', '')
        milestone = match.get('Milestone', '')
        if not all([activity, sub_milestone, milestone]): continue
        key = f"{milestone} > {sub_milestone}"
        if key not in activities_by_submilestone:
            activities_by_submilestone[key] = {'milestone': milestone, 'sub_milestone': sub_milestone, 'activities': {}}
        a_key = f"{activity} > {sub_activity}" if sub_activity else activity
        activities_by_submilestone[key]['activities'][a_key] = {'activity': activity, 'sub_activity': sub_activity}
        
    results = {}
    for submilestone_key, data in activities_by_submilestone.items():
        milestone = data['milestone']
        sub_milestone = data['sub_milestone']
        inv_info = invoice_lookup.get((milestone, sub_milestone), {'pct': 0, 'sales_from': []})
        submilestone_pct = inv_info['pct']
        sales_from_list = inv_info['sales_from']
        
        for month in calc_months:
            total_contribution = 0
            activity_contributions = {}
            for act_key, act_data in data['activities'].items():
                a_lookup_key = (act_data['activity'], act_data['sub_activity'])
                contribution = (act_pct_lookup.get(a_lookup_key, {}).get(month, 0) / 100) * act_sales_lookup.get(a_lookup_key, 0)
                activity_contributions[act_key] = contribution
                total_contribution += contribution
                
            if sales_from_list:
                submilestone_value = (submilestone_pct / 100) * fast_get_total_sales(sales_from_list)
            else:
                submilestone_value = (submilestone_pct / 100) * total_contribution
                
            if total_contribution > 0:
                for act_key, contribution in activity_contributions.items():
                    if act_key not in results: results[act_key] = {m: 0 for m in calc_months}
                    results[act_key][month] += (contribution / total_contribution) * submilestone_value
                    
    if not results: return pd.DataFrame()
    data = [{'Activity': key, **months_data} for key, months_data in results.items()]
    return add_total_and_cumulative(pd.DataFrame(data))
def calculate_summary_totals():
    """Calculate total values by month across the full project duration including O&M."""
    calc_months = get_calculation_months()
    
    df = calculate_invoicing_table()
    
    if df.empty:
        return {month: 0 for month in calc_months}
    
    totals = {}
    for month in calc_months:
        if month in df.columns:
            totals[month] = df[month].sum()
        else:
            totals[month] = 0
    
    return totals

def calculate_advance_table():
    """
    Calculate advance payments table.
    
    Formula: advance_value = (advance_percentage / 100) * total_submilestone_value
    
    Returns: DataFrame with sub-milestones as rows and months as columns, showing advance amounts
    """
    from advance_utils import load_advances, get_advance
    
    invoicing_df = calculate_invoicing_table()
    advances = load_advances()
    
    if invoicing_df.empty or not advances:
        return pd.DataFrame()
        
    calc_months = get_calculation_months()
    results = {}
    
    for idx, row in invoicing_df.iterrows():
        sub_milestone_key = row.get('Sub-Milestone')
        
        # Skip totals/cumulative rows
        if pd.isna(sub_milestone_key) or sub_milestone_key in ['TOTAL', 'CUMULATIVE'] or ' > ' not in str(sub_milestone_key):
            continue
            
        milestone = sub_milestone_key.split(' > ')[0]
        sub_milestone = sub_milestone_key.split(' > ')[1]
        
        # Calculate total invoicing value for this sub-milestone
        total_value = 0
        for month in calc_months:
            if month in row:
                total_value += float(row[month]) if pd.notna(row[month]) else 0
                
        # Now apply advances based on the specified month
        has_advance = False
        month_advances = {month: 0 for month in calc_months}
        
        for month in calc_months:
            advance_pct = get_advance(milestone, sub_milestone, month)
            if advance_pct > 0:
                has_advance = True
                month_advances[month] = (advance_pct / 100) * total_value
                
        if has_advance:
            results[sub_milestone_key] = month_advances
            
    if not results:
        return pd.DataFrame()
        
    data = []
    for key, months_data in results.items():
        row = {'Sub-Milestone': key}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
        
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_advance_by_milestone():
    """
    Calculate advance totals grouped by milestone.
    
    Returns: DataFrame with milestones as rows and months as columns, showing total advance per milestone
    """
    advance_df = calculate_advance_table()
    
    if advance_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Parse milestone from 'Sub-Milestone' column (format: "Milestone > Sub-Milestone")
    results = {}
    
    for _, row in advance_df.iterrows():
        sub_milestone_key = row['Sub-Milestone']
        milestone_name = sub_milestone_key.split(' > ')[0]
        
        if milestone_name not in results:
            results[milestone_name] = {month: 0 for month in calc_months}
        
        # Add this sub-milestone's values to the milestone total
        for month in calc_months:
            if month in row.index:
                results[milestone_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for milestone, months_data in results.items():
        row = {'Milestone': milestone}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_net_invoicing_table():
    """
    Calculate net invoicing table after subtracting advances.
    
    Formula: net_value = (submilestone_pct * SUM[(activity_pct * sales)]) - advance_value
    where advance_value = (advance_pct * SUM[(activity_pct * sales)])
    
    Returns: DataFrame with sub-milestones as rows and months as columns, showing net values
    """
    invoicing_df = calculate_invoicing_table()
    advance_df = calculate_advance_table()
    
    if invoicing_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Create net dataframe by subtracting advances from invoicing
    net_df = invoicing_df.copy()
    
    # For each row in net_df, check if there's a corresponding advance
    for idx, row in net_df.iterrows():
        sub_milestone_key = row['Sub-Milestone']
        
        # Find matching advance row
        if not advance_df.empty:
            advance_rows = advance_df[advance_df['Sub-Milestone'] == sub_milestone_key]
            
            if not advance_rows.empty:
                advance_row = advance_rows.iloc[0]
                # Subtract advance from invoicing for each month
                for month in calc_months:
                    if month in net_df.columns and month in advance_row.index:
                        invoicing_val = net_df.at[idx, month]
                        advance_val = float(advance_row[month]) if pd.notna(advance_row[month]) else 0
                        net_df.at[idx, month] = invoicing_val - advance_val
    
    return add_total_and_cumulative(net_df)

def calculate_net_by_milestone():
    """
    Calculate net totals grouped by milestone (after subtracting advances).
    
    Returns: DataFrame with milestones as rows and months as columns
    """
    net_df = calculate_net_invoicing_table()
    
    if net_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Filter out TOTAL and CUMULATIVE rows if they exist
    net_df = net_df[~net_df['Sub-Milestone'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Parse milestone from 'Sub-Milestone' column (format: "Milestone > Sub-Milestone")
    results = {}
    
    for _, row in net_df.iterrows():
        sub_milestone_key = row['Sub-Milestone']
        milestone_name = sub_milestone_key.split(' > ')[0]
        
        if milestone_name not in results:
            results[milestone_name] = {month: 0 for month in calc_months}
        
        # Add this sub-milestone's values to the milestone total
        for month in calc_months:
            if month in row.index:
                results[milestone_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for milestone, months_data in results.items():
        row = {'Milestone': milestone}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_net_summary_totals():
    """Calculate net total values by month across all sub-milestones (after advances)."""
    calc_months = get_calculation_months()
    df = calculate_net_invoicing_table()
    
    if df.empty:
        return {month: 0 for month in calc_months}
    
    totals = {}
    for month in calc_months:
        if month in df.columns:
            totals[month] = df[month].sum()
        else:
            totals[month] = 0
    
    return totals

def calculate_collection_table():
    """
    Calculate collection table by shifting all invoicing amounts based on global collection period.
    
    Collection months are calculated from days: 1-30 days = 1 month, 31-60 = 2 months, etc.
    All invoicing amounts are shifted forward by the collection months uniformly.
    
    Formula: collection_value[month + collection_months] = invoicing_value[month]
    
    When shifting causes overflow (e.g., December + months > 12), overflow amount goes to January.
    
    Returns: DataFrame with sub-milestones as rows and months as columns, showing shifted values
    """
    from collection_utils import get_collection_months
    
    invoicing_df = calculate_invoicing_table()
    
    if invoicing_df.empty:
        return pd.DataFrame()
    
    # Get global collection months
    collection_months = get_collection_months()
    
    if collection_months == 0:
        # No collection period set, return original invoicing
        return invoicing_df.copy()
    
    # Get the calculation months with years
    calc_months = get_calculation_months()
    
    # Create a copy for collection data
    collection_df = invoicing_df.copy()
    
    # Shift all values forward by collection_months
    for idx, row in collection_df.iterrows():
        # Create shifted months dictionary
        shifted_values = {month: 0 for month in calc_months}
        
        # Shift each month's value forward
        for month_idx, month in enumerate(calc_months):
            if month in row.index:
                original_value = row[month]
                if original_value != 0:
                    # Calculate new month index
                    new_month_idx = month_idx + collection_months
                    
                    # Handle overflow: if beyond available months, put in last month or ignore overflow
                    if new_month_idx < len(calc_months):
                        shifted_values[calc_months[new_month_idx]] = original_value
                    # If overflow beyond timeline, we skip it (don't add to shifted_values)
        
        # Update row with shifted values
        for month in calc_months:
            if month in collection_df.columns:
                collection_df.at[idx, month] = shifted_values[month]
    
    return add_total_and_cumulative(collection_df)

def calculate_net_collection_table():
    """
    Calculate collection table by shifting NET invoicing amounts (after advance deduction).
    
    This applies collection period to the net invoicing table instead of original invoicing.
    Formula: net_collection_value[month + collection_months] = net_invoicing_value[month]
    
    When shifting causes overflow (e.g., December + months > 12), overflow amount goes to January.
    
    Returns: DataFrame with sub-milestones as rows and months as columns
    """
    from collection_utils import get_collection_months
    
    # Get net invoicing (after advance deduction)
    net_df = calculate_net_invoicing_table()
    
    if net_df.empty:
        return pd.DataFrame()
    
    # Get global collection months
    collection_months = get_collection_months()
    
    if collection_months == 0:
        # No collection period set, return net invoicing
        return net_df.copy()
    
    # Get the calculation months with years
    calc_months = get_calculation_months()
    
    # Create a copy for collection data
    collection_df = net_df.copy()
    
    # Shift all net values forward by collection_months
    for idx, row in collection_df.iterrows():
        # Create shifted months dictionary
        shifted_values = {month: 0 for month in calc_months}
        
        # Shift each month's value forward
        for month_idx, month in enumerate(calc_months):
            if month in row.index:
                original_value = row[month]
                if original_value != 0:
                    # Calculate new month index
                    new_month_idx = month_idx + collection_months
                    
                    # Handle overflow: if beyond available months, put in last month or ignore overflow
                    if new_month_idx < len(calc_months):
                        shifted_values[calc_months[new_month_idx]] = original_value
                    # If overflow beyond timeline, we skip it (don't add to shifted_values)
        
        # Update row with shifted values
        for month in calc_months:
            if month in collection_df.columns:
                collection_df.at[idx, month] = shifted_values[month]
    
    return add_total_and_cumulative(collection_df)

def calculate_net_collection_by_milestone():
    """
    Calculate net collection totals grouped by milestone.
    
    Returns: DataFrame with milestones as rows and months as columns
    """
    collection_df = calculate_net_collection_table()
    
    if collection_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Filter out TOTAL and CUMULATIVE rows if they exist
    collection_df = collection_df[~collection_df['Sub-Milestone'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Group by milestone
    milestones = {}
    for idx, row in collection_df.iterrows():
        parts = row['Sub-Milestone'].rsplit(' > ', 1)
        if len(parts) == 2:
            milestone = parts[0]
        else:
            milestone = 'Unknown'
        
        if milestone not in milestones:
            milestones[milestone] = {month: 0 for month in calc_months}
        
        for month in calc_months:
            if month in row.index:
                milestones[milestone][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    result_df = pd.DataFrame.from_dict(milestones, orient='index')
    if not result_df.empty:
        result_df.index.name = 'Milestone'
    
    return add_total_and_cumulative(result_df)

def calculate_collection_by_milestone():
    """
    Calculate collection totals grouped by milestone.
    
    Returns: DataFrame with milestones as rows and months as columns, showing shifted totals
    """
    collection_df = calculate_collection_table()
    
    if collection_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Filter out TOTAL and CUMULATIVE rows if they exist
    collection_df = collection_df[~collection_df['Sub-Milestone'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Parse milestone from 'Sub-Milestone' column (format: "Milestone > Sub-Milestone")
    results = {}
    
    for _, row in collection_df.iterrows():
        sub_milestone_key = row['Sub-Milestone']
        milestone_name = sub_milestone_key.split(' > ')[0]
        
        if milestone_name not in results:
            results[milestone_name] = {month: 0 for month in calc_months}
        
        # Add this sub-milestone's values to the milestone total
        for month in calc_months:
            if month in row.index:
                results[milestone_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for milestone, months_data in results.items():
        row = {'Milestone': milestone}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_collection_summary_totals():
    """Calculate collection total values by month across all sub-milestones."""
    calc_months = get_calculation_months()
    df = calculate_collection_table()
    
    if df.empty:
        return {month: 0 for month in calc_months}
    
    totals = {}
    for month in calc_months:
        if month in df.columns:
            totals[month] = df[month].sum()
        else:
            totals[month] = 0
    
    return totals

# ==================== VENDOR PAYMENT CALCULATIONS ====================

def get_activity_cost(activity_name, sub_activity_name=''):
    """Get cost value for an activity/sub-activity."""
    cost_sales = load_cost_sales()
    
    for item in cost_sales:
        if item.get('Activity', '') == activity_name:
            if sub_activity_name:
                if item.get('Sub-Activity', '') == sub_activity_name:
                    try:
                        return float(item.get('Cost', 0) or 0)
                    except:
                        return 0
            else:
                if item.get('Sub-Activity', '') == '':
                    try:
                        return float(item.get('Cost', 0) or 0)
                    except:
                        return 0
    return 0

def get_bill_percentage_and_creditdays(vendor_name, bill_name):
    """Get percentage and credit days for a vendor bill."""
    vendors = load_vendors()
    
    for vendor in vendors:
        if vendor.get('Vendor', '') == vendor_name:
            if vendor.get('Bill', '') == bill_name:
                try:
                    percentage = float(vendor.get('Percentage', 0) or 0)
                    credit_days = int(vendor.get('Credit_Days', 0) or 0)
                    return percentage, credit_days
                except:
                    return 0, 0
    return 0, 0

def shift_months_by_days(month_name, credit_days):
    """
    Shift a month forward by credit days.
    
    Args:
        month_name: Name of the month (e.g., 'January' or 'January 2025')
        credit_days: Number of days to shift
    
    Returns:
        Name of the shifted month (preserving year if input had year)
    """
    if credit_days <= 0:
        return month_name
    
    parts = str(month_name).split()
    month_part = parts[0]
    year_part = parts[1] if len(parts) > 1 else None
    
    month_shift = max(1, credit_days // 30)
    
    try:
        month_idx = MONTHS.index(month_part)
        new_raw_idx = month_idx + month_shift
        new_idx = new_raw_idx % len(MONTHS)
        years_added = new_raw_idx // len(MONTHS)
        shifted_month = MONTHS[new_idx]
        
        if year_part:
            year_int = int(year_part)
            return f"{shifted_month} {year_int + years_added}"
        else:
            return shifted_month
    except ValueError:
        return month_name

def calculate_vendor_payment_table():
    """
    Calculate the vendor payment table based on matches and formulas.
    """
    calc_months = get_calculation_months()
    matches = load_vendor_matches()
    vendors_list = load_vendors()
    activities_list = load_activities()
    cost_sales_list = load_cost_sales()
    
    vendor_lookup = {}
    for v in vendors_list:
        key = (v.get('Vendor', ''), v.get('Bill', ''))
        cost_from_str = v.get('Cost_From_Activities', '')
        cost_from = parse_sales_activities(cost_from_str, cost_sales_list)
        vendor_lookup[key] = {
            'pct': float(v.get('Percentage', 0) or 0),
            'credit_days': int(v.get('Credit_Days', 0) or 0),
            'cost_from': cost_from
        }
        
    act_pct_lookup = {}
    for act in activities_list:
        act_pct_lookup[(act.get('Activity', ''), act.get('Sub-Activity', ''))] = {m: float(act.get(m, 0) or 0) for m in calc_months}
        
    act_cost_lookup = {}
    for item in cost_sales_list:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        cost = float(item.get('Cost', 0) or 0)
        act_cost_lookup[(main_act, sub_act)] = cost

    activities_by_bill = {}
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        bill = match.get('Bill', '')
        vendor = match.get('Vendor', '')
        if not all([activity, bill, vendor]): continue
        key = f"{vendor} > {bill}"
        if key not in activities_by_bill:
            activities_by_bill[key] = {'vendor': vendor, 'bill': bill, 'activities': []}
        activities_by_bill[key]['activities'].append({'activity': activity, 'sub_activity': sub_activity})
        
    results = {}
    for key, data in activities_by_bill.items():
        v_info = vendor_lookup.get((data['vendor'], data['bill']), {'pct': 0, 'credit_days': 0, 'cost_from': []})
        bill_pct = v_info['pct']
        credit_days = v_info['credit_days']
        cost_from_list = v_info.get('cost_from', [])
        matched_activities = data['activities']  # Activities from matching file
        
        # Get cost values
        cost_values = []
        if cost_from_list:
            for activity_name in cost_from_list:
                activity_name_stripped = activity_name.strip()
                cost_value = 0
                for (main_act, sub_act), cost_val in act_cost_lookup.items():
                    if main_act == activity_name_stripped:
                        cost_value = cost_val
                        break
                else:
                    for (main_act, sub_act), cost_val in act_cost_lookup.items():
                        full_name = f"{main_act} {sub_act}".strip() if sub_act else main_act
                        if full_name == activity_name_stripped:
                            cost_value = cost_val
                            break
                cost_values.append(cost_value)
        else:
            # Fallback to matched activities' costs (old behavior)
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                cost_value = act_cost_lookup.get(activity_key, 0)
                cost_values.append(cost_value)
        
        results[key] = {month: 0 for month in calc_months}
        for month in calc_months:
            # Collect work distribution percentages from matched activities
            work_dist_percentages = []
            for matched_activity in matched_activities:
                activity_key = (matched_activity['activity'], matched_activity['sub_activity'])
                activity_pct = act_pct_lookup.get(activity_key, {}).get(month, 0)
                work_dist_percentages.append(activity_pct)
            
            # Apply user logic based on number of matched activities:
            if len(matched_activities) == 1:
                # Rule A: bill% * (cost of act1 + cost of act3) * work distribution % of matched activity
                total_cost = sum(cost_values)
                work_pct = work_dist_percentages[0]
                results[key][month] = (bill_pct / 100) * total_cost * (work_pct / 100)
            else:
                # Rule B: Bill% × [(Cost₁ × Work%₁) + (Cost₂ × Work%₂) + ...] (positional pairing)
                results[key][month] = calculate_milestone_value(
                    bill_pct,
                    cost_values,
                    work_dist_percentages
                )
            
        if credit_days > 0:
            shifted_results = {month: 0 for month in calc_months}
            for month, value in results[key].items():
                shifted_month = shift_months_by_days(month, credit_days)
                if shifted_month in shifted_results:
                    shifted_results[shifted_month] += value
            results[key] = shifted_results
            
    if not results: return pd.DataFrame()
    data = [{'Bill': key, **months_data} for key, months_data in results.items()]
    return add_total_and_cumulative(pd.DataFrame(data))
def calculate_vendor_by_vendor():
    """
    Calculate vendor totals grouped by vendor (summing all their bills).
    
    Returns: DataFrame with vendors as rows and months as columns
    """
    calc_months = get_calculation_months()
    
    vendor_df = calculate_vendor_payment_table()
    
    if vendor_df.empty:
        return pd.DataFrame()
    
    # Filter out TOTAL and CUMULATIVE rows
    vendor_df = vendor_df[~vendor_df['Bill'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    if vendor_df.empty:
        return pd.DataFrame()
    
    # Parse vendor from 'Bill' column (format: "Vendor > Bill")
    results = {}
    
    for _, row in vendor_df.iterrows():
        bill_key = row['Bill']
        if ' > ' in bill_key:
            vendor_name = bill_key.split(' > ')[0]
        else:
            vendor_name = 'Unknown'
        
        if vendor_name not in results:
            results[vendor_name] = {month: 0 for month in calc_months}
        
        # Add this bill's values to the vendor total
        for month in calc_months:
            if month in row:
                results[vendor_name][month] += row[month]
    
    # Convert to DataFrame
    data = []
    for vendor, months_data in results.items():
        row = {'Vendor': vendor}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_vendor_summary_totals():
    """Calculate vendor payment total values by month across the full project duration including O&M."""
    calc_months = get_calculation_months()
    
    df = calculate_vendor_payment_table()
    
    if df.empty:
        return {month: 0 for month in calc_months}
    
    totals = {}
    for month in calc_months:
        if month in df.columns:
            totals[month] = df[month].sum()
        else:
            totals[month] = 0
    
    return totals

def calculate_vendor_advance_table():
    """
    Calculate vendor payment advance table based on configured advances.
    
    Formula: advance_value = (advance_percentage / 100) * bill_payment_amount
    
    Returns: DataFrame with vendor bills as rows and months as columns, showing advance amounts
    """
    from vendor_advance_utils import load_vendor_advances, get_vendor_advance
    
    calc_months = get_calculation_months()
    
    advances = load_vendor_advances()
    
    # Create a mapping of (vendor, bill) to advance percentages by month
    advances_by_bill = {}
    
    for advance in advances:
        vendor = advance.get('Vendor', '')
        bill = advance.get('Bill', '')
        advance_pct = float(advance.get('Advance_Percentage', 0))
        months_str = advance.get('Months', '')
        
        if not all([vendor, bill, advance_pct > 0, months_str]):
            continue
        
        key = f"{vendor} > {bill}"
        advances_by_bill[key] = {
            'vendor': vendor,
            'bill': bill,
            'advance_pct': advance_pct,
            'months': set(m.strip() for m in months_str.split(',') if m.strip())
        }
    
    # Get vendor payment table
    vendor_df = calculate_vendor_payment_table()
    
    if vendor_df.empty or not advances_by_bill:
        return pd.DataFrame()
    
    # Filter out TOTAL and CUMULATIVE rows
    vendor_df = vendor_df[~vendor_df['Bill'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    if vendor_df.empty:
        return pd.DataFrame()
    
    # Calculate advance values for each bill
    results = {}
    
    for _, row in vendor_df.iterrows():
        bill_key = row['Bill']
        
        if bill_key not in advances_by_bill:
            continue
        
        advance_data = advances_by_bill[bill_key]
        vendor = advance_data['vendor']
        bill = advance_data['bill']
        advance_pct = advance_data['advance_pct']
        advance_months = advance_data['months']
        
        results[bill_key] = {month: 0 for month in calc_months}
        
        # For each month, if advance applies, calculate the advance amount
        for month in calc_months:
            if month in advance_months and month in row.index:
                bill_payment = float(row[month]) if pd.notna(row[month]) else 0
                results[bill_key][month] = (advance_pct / 100) * bill_payment
    
    # Convert to DataFrame (only include rows with advances)
    if not results:
        return pd.DataFrame()
    
    data = []
    for bill_key, months_data in results.items():
        # Only include if there's at least one advance value
        if any(v > 0 for v in months_data.values()):
            row = {'Bill': bill_key}
            for month in calc_months:
                row[month] = months_data.get(month, 0)
            data.append(row)
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_vendor_advance_by_bill():
    """
    Calculate vendor advance totals grouped by vendor (summing all their bill advances).
    
    Returns: DataFrame with vendors as rows and months as columns, showing total advance per vendor
    """
    advance_df = calculate_vendor_advance_table()
    
    if advance_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Parse vendor from 'Bill' column (format: "Vendor > Bill")
    results = {}
    
    for _, row in advance_df.iterrows():
        bill_key = row['Bill']
        if bill_key in ['TOTAL', 'CUMULATIVE']:
            continue
        
        if ' > ' in bill_key:
            vendor_name = bill_key.split(' > ')[0]
        else:
            vendor_name = 'Unknown'
        
        if vendor_name not in results:
            results[vendor_name] = {month: 0 for month in calc_months}
        
        # Add this bill's advance values to the vendor total
        for month in calc_months:
            if month in row.index:
                results[vendor_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for vendor, months_data in results.items():
        row = {'Vendor': vendor}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_net_vendor_payment_table():
    """
    Calculate net vendor payment table after subtracting advances.
    
    Formula: net_value = bill_payment_value - advance_value
    
    Returns: DataFrame with vendor bills as rows and months as columns, showing net values
    """
    vendor_df = calculate_vendor_payment_table()
    advance_df = calculate_vendor_advance_table()
    
    if vendor_df.empty:
        return vendor_df
    
    if advance_df.empty:
        return vendor_df
    
    calc_months = get_calculation_months()
    
    # Filter vendor_df to exclude TOTAL and CUMULATIVE
    vendor_df_clean = vendor_df[~vendor_df['Bill'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Create advance mapping
    advance_map = {}
    for _, row in advance_df.iterrows():
        bill_key = row['Bill']
        if bill_key not in ['TOTAL', 'CUMULATIVE']:
            advance_map[bill_key] = {month: float(row[month]) if pd.notna(row[month]) else 0 for month in calc_months}
    
    # Calculate net by subtracting advances
    results = []
    for _, row in vendor_df_clean.iterrows():
        bill_key = row['Bill']
        new_row = {'Bill': bill_key}
        
        for month in calc_months:
            vendor_payment = float(row[month]) if pd.notna(row[month]) and month in row.index else 0
            advance_amount = advance_map.get(bill_key, {}).get(month, 0)
            new_row[month] = vendor_payment - advance_amount
        
        results.append(new_row)
    
    df = pd.DataFrame(results)
    return add_total_and_cumulative(df)

def calculate_vendor_by_activity():
    """
    Calculate vendor payment totals grouped by activity.
    """
    calc_months = get_calculation_months()
    matches = load_vendor_matches()
    vendors_list = load_vendors()
    activities_list = load_activities()
    cost_sales_list = load_cost_sales()
    
    vendor_lookup = {}
    for v in vendors_list:
        key = (v.get('Vendor', ''), v.get('Bill', ''))
        cost_from_str = v.get('Cost_From_Activities', '')
        cost_from = parse_sales_activities(cost_from_str, cost_sales_list)
        vendor_lookup[key] = {
            'pct': float(v.get('Percentage', 0) or 0),
            'credit_days': int(v.get('Credit_Days', 0) or 0),
            'cost_from': cost_from
        }
        
    act_pct_lookup = {}
    for act in activities_list:
        act_pct_lookup[(act.get('Activity', ''), act.get('Sub-Activity', ''))] = {m: float(act.get(m, 0) or 0) for m in calc_months}
        
    act_cost_lookup = {}
    act_cost_by_main_act = {}
    for item in cost_sales_list:
        main_act = item.get('Activity', '')
        sub_act = item.get('Sub-Activity', '')
        cost = float(item.get('Cost', 0) or 0)
        act_cost_lookup[(main_act, sub_act)] = cost
        if main_act not in act_cost_by_main_act:
            act_cost_by_main_act[main_act] = 0
        act_cost_by_main_act[main_act] += cost

    def fast_get_total_cost(cost_from_list):
        return sum(act_cost_by_main_act.get(a, 0) for a in cost_from_list)

    activities_by_bill = {}
    for match in matches:
        activity = match.get('Activity', '')
        sub_activity = match.get('Sub-Activity', '')
        bill = match.get('Bill', '')
        vendor = match.get('Vendor', '')
        if not all([activity, bill, vendor]): continue
        key = f"{vendor} > {bill}"
        if key not in activities_by_bill:
            activities_by_bill[key] = {'vendor': vendor, 'bill': bill, 'activities': {}}
        a_key = f"{activity} > {sub_activity}" if sub_activity else activity
        activities_by_bill[key]['activities'][a_key] = {'activity': activity, 'sub_activity': sub_activity}
        
    results = {}
    for bill_key, data in activities_by_bill.items():
        v_info = vendor_lookup.get((data['vendor'], data['bill']), {'pct': 0, 'credit_days': 0, 'cost_from': []})
        bill_pct = v_info['pct']
        credit_days = v_info['credit_days']
        cost_from_list = v_info['cost_from']
        
        unshifted_results = {}
        for month in calc_months:
            total_contribution = 0
            activity_contributions = {}
            for act_key, act_data in data['activities'].items():
                a_lookup_key = (act_data['activity'], act_data['sub_activity'])
                contribution = (act_pct_lookup.get(a_lookup_key, {}).get(month, 0) / 100) * act_cost_lookup.get(a_lookup_key, 0)
                activity_contributions[act_key] = contribution
                total_contribution += contribution
                
            if cost_from_list:
                bill_value = (bill_pct / 100) * fast_get_total_cost(cost_from_list)
            else:
                bill_value = (bill_pct / 100) * total_contribution
                
            if total_contribution > 0:
                for act_key, contribution in activity_contributions.items():
                    if act_key not in unshifted_results: unshifted_results[act_key] = {m: 0 for m in calc_months}
                    unshifted_results[act_key][month] += (contribution / total_contribution) * bill_value
                    
        if credit_days > 0:
            for act_key, month_values in unshifted_results.items():
                if act_key not in results: results[act_key] = {m: 0 for m in calc_months}
                for month, value in month_values.items():
                    shifted_month = shift_months_by_days(month, credit_days)
                    if shifted_month in results[act_key]: results[act_key][shifted_month] += value
        else:
            for act_key, month_values in unshifted_results.items():
                if act_key not in results: results[act_key] = {m: 0 for m in calc_months}
                for month, value in month_values.items():
                    results[act_key][month] += value
                    
    if not results: return pd.DataFrame()
    data = [{'Activity': key, **months_data} for key, months_data in results.items()]
    return add_total_and_cumulative(pd.DataFrame(data))
def calculate_net_vendor_by_vendor():
    """
    Calculate net vendor totals grouped by vendor (after subtracting advances).
    
    Returns: DataFrame with vendors as rows and months as columns
    """
    net_df = calculate_net_vendor_payment_table()
    
    if net_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Filter out TOTAL and CUMULATIVE rows if they exist
    net_df = net_df[~net_df['Bill'].isin(['TOTAL', 'CUMULATIVE'])].copy()
    
    # Parse vendor from 'Bill' column (format: "Vendor > Bill")
    results = {}
    
    for _, row in net_df.iterrows():
        bill_key = row['Bill']
        vendor_name = bill_key.split(' > ')[0] if ' > ' in bill_key else 'Unknown'
        
        if vendor_name not in results:
            results[vendor_name] = {month: 0 for month in calc_months}
        
        # Add this bill's values to the vendor total
        for month in calc_months:
            if month in row.index:
                results[vendor_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for vendor, months_data in results.items():
        row = {'Vendor': vendor}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)

def calculate_vendor_advance_by_vendor():
    """
    Calculate vendor advance totals grouped by vendor (summing all their bill advances).
    
    Returns: DataFrame with vendors as rows and months as columns, showing total advance per vendor
    """
    advance_df = calculate_vendor_advance_table()
    
    if advance_df.empty:
        return pd.DataFrame()
    
    # Get calculation months with years
    calc_months = get_calculation_months()
    
    # Parse vendor from 'Bill' column (format: "Vendor > Bill")
    results = {}
    
    for _, row in advance_df.iterrows():
        bill_key = row['Bill']
        if bill_key in ['TOTAL', 'CUMULATIVE']:
            continue
        
        if ' > ' in bill_key:
            vendor_name = bill_key.split(' > ')[0]
        else:
            vendor_name = 'Unknown'
        
        if vendor_name not in results:
            results[vendor_name] = {month: 0 for month in calc_months}
        
        # Add this bill's advance values to the vendor total
        for month in calc_months:
            if month in row.index:
                results[vendor_name][month] += float(row[month]) if pd.notna(row[month]) else 0
    
    # Convert to DataFrame
    data = []
    for vendor, months_data in results.items():
        row = {'Vendor': vendor}
        for month in calc_months:
            row[month] = months_data.get(month, 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    return add_total_and_cumulative(df)
