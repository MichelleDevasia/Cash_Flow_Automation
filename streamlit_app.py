import streamlit as st
import pandas as pd
from activity_utils import load_activities, add_activity, get_activity_months, delete_activity, MONTHS
from cost_sales import load_cost_sales, add_or_update_cost_sales, get_summary, delete_cost_sales
from invoice_utils import (load_invoices, add_invoice_milestone, delete_milestone, 
                           get_milestone_total, get_all_milestones, get_submilestones)
from vendor_payment_utils import (load_vendors, add_vendor_bill, delete_vendor, 
                                  get_all_vendors, get_bills, get_all_bills)
from matching_utils import (load_matches, add_match, delete_match, get_matches_by_activity,
                           get_all_activities_and_subs, get_all_submilestones, delete_matches_by_activity,
                           delete_matches_by_milestone)
from vendor_payment_matching_utils import (load_vendor_matches, add_vendor_match, delete_vendor_match,
                                          get_matches_by_activity as get_vendor_matches_by_activity,
                                          get_all_activities_and_subs as get_vendor_activities_and_subs,
                                          get_all_bills as get_vendor_all_bills, delete_vendor_matches_by_activity,
                                          delete_vendor_matches_by_bill)
from calculation_utils import (calculate_invoicing_table, calculate_by_milestone, 
                               calculate_by_activity, calculate_summary_totals,
                               calculate_advance_table, calculate_advance_by_milestone,
                               calculate_net_invoicing_table, calculate_net_by_milestone,
                               calculate_net_summary_totals, calculate_collection_table,
                               calculate_collection_by_milestone, calculate_collection_summary_totals,
                               calculate_net_collection_table, calculate_net_collection_by_milestone,
                               calculate_vendor_payment_table, calculate_vendor_by_vendor,
                               calculate_vendor_summary_totals, calculate_vendor_advance_table,
                               calculate_vendor_advance_by_bill, calculate_net_vendor_payment_table,
                               get_calculation_months, calculate_vendor_by_activity,
                               calculate_net_vendor_by_vendor, calculate_vendor_advance_by_vendor)
from advance_utils import (load_advances, add_advance, delete_advance, 
                          get_advances_by_submilestone, get_all_advances, delete_advances_by_milestone,
                          get_period_months, calculate_advance_months, add_advance_with_strategy)
from vendor_advance_utils import (load_vendor_advances, add_or_update_vendor_advance, get_vendor_advance,
                                  delete_vendor_advance, delete_vendor_advances_by_vendor, 
                                  get_all_vendor_advances)
from collection_utils import (load_collection, set_collection, delete_collection,
                             get_collection_days, get_collection_months, days_to_months, get_all_collection)
from timeline_utils import (get_month_list, save_project_config, get_project_config, 
                            get_total_months, get_project_months_only, get_extended_months)
from cleanup_utils import cleanup_all_orphaned_records
from excel_export import create_invoicing_excel_report
from cashflow_utils import (create_cashflow_curve, get_cumulative_invoicing, 
                           get_cumulative_vendor_payment, calculate_net_cashflow,
                           get_custom_cumulative_invoicing, get_custom_cumulative_vendor_payment)
from formula_utils import display_table_with_formulas, build_invoicing_formula_text, build_vendor_formula_text
import calendar

# Page config
st.set_page_config(page_title="Activity Tracker", layout="wide")

st.title("📊 Activity Tracker")

# ==================== HELPER FUNCTION: Display Tables with Hover Tooltips ====================
def display_table_with_hover_tooltips(df, table_name="Table", use_aggrid=True, unformatted_df=None, table_type="invoice"):
    """
    Display a dataframe with enhanced hover tooltips showing calculation formulas and breakdown.
    Uses AgGrid for interactive tables with hover information.
    
    Args:
        df: DataFrame to display (can be formatted with $ or unformatted)
        table_name: Name of the table for display
        use_aggrid: Whether to use AgGrid (has better hover support)
        unformatted_df: Optional unformatted dataframe with raw numbers for tooltip calculations
        table_type: "invoice" or "vendor" - determines which calculation logic to use
    """
    if df.empty:
        st.warning(f"⚠️ No data available for {table_name}")
        return
    
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
        
        # Load source data for breakdown calculations
        invoices = load_invoices() if table_type == "invoice" else []
        vendors = load_vendors() if table_type == "vendor" else []
        activities_list = load_activities()
        cost_sales_list = load_cost_sales()
        matches = load_matches() if table_type == "invoice" else load_vendor_matches()
        
        # Build lookup dictionaries
        invoice_lookup = {}
        if table_type == "invoice":
            for inv in invoices:
                key = (inv.get('Milestone', ''), inv.get('Sub-Milestone', ''))
                invoice_lookup[key] = {
                    'pct': float(inv.get('Percentage', 0) or 0),
                    'sales_from': inv.get('Sales_From_Activities', '')
                }
        
        vendor_lookup = {}
        if table_type == "vendor":
            for vendor in vendors:
                vendor_name = vendor.get('Vendor_Name', '')
                bill_name = vendor.get('Bill_Name', '')
                vendor_lookup[(vendor_name, bill_name)] = {
                    'pct': float(vendor.get('Percentage', 0) or 0)
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
            cost = float(item.get('Cost', 0) or 0)
            if table_type == "invoice":
                act_sales_lookup[(main_act, sub_act)] = sales
            else:
                act_sales_lookup[(main_act, sub_act)] = cost
        
        # Use unformatted data for calculations if provided, otherwise use original
        calc_df = unformatted_df.copy() if unformatted_df is not None else df.copy()
        display_df = df.copy()
        
        # Find the row identifier column (first non-month column)
        row_id_col = None
        for col in display_df.columns:
            if col not in calc_months and col != 'Row Total':
                row_id_col = col
                break
        
        # Helper function to extract numeric value from formatted string
        def extract_numeric(val):
            """Extract numeric value from formatted string like '$1,234.56' or plain number"""
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                cleaned = val.replace('$', '').replace(',', '').strip()
                try:
                    return float(cleaned) if cleaned else 0
                except ValueError:
                    return 0
            return 0
        
        # Build activity to milestone/vendor mappings
        activity_matches = {}
        for match in matches:
            if table_type == "invoice":
                key = (match.get('Milestone', ''), match.get('Sub-Milestone', ''))
            else:
                vendor = match.get('Vendor_Name', '')
                bill = match.get('Bill_Name', '')
                key = (vendor, bill)
            
            if key not in activity_matches:
                activity_matches[key] = []
            activity_matches[key].append({
                'activity': match.get('Activity', ''),
                'sub_activity': match.get('Sub-Activity', '')
            })
        
        # Add formula/tooltip column with component breakdown
        tooltip_data = []
        for idx, row in display_df.iterrows():
            row_name = str(row[row_id_col]) if row_id_col else f"Row {idx}"
            
            # Get corresponding values from calc_df if different
            calc_row = calc_df.iloc[idx] if unformatted_df is not None else row
            
            # Collect all monthly values with breakdown
            monthly_breakdowns = []
            for month in calc_months:
                if month in display_df.columns:
                    # Get numeric value
                    display_value = extract_numeric(row[month])
                    calc_value = extract_numeric(calc_row[month])
                    numeric_val = calc_value if unformatted_df is not None else display_value
                    
                    if numeric_val > 0:
                        # Try to compute breakdown components
                        try:
                            if table_type == "invoice":
                                # Extract milestone and sub-milestone from row_name
                                if " > " in row_name:
                                    parts = row_name.split(" > ")
                                    milestone, sub_milestone = parts[0].strip(), parts[1].strip()
                                    inv_info = invoice_lookup.get((milestone, sub_milestone), {})
                                    percentage = inv_info.get('pct', 0)
                                    key = (milestone, sub_milestone)
                                else:
                                    percentage = 0
                                    key = None
                            else:
                                # For vendor, extract vendor and bill
                                if " > " in row_name:
                                    parts = row_name.split(" > ")
                                    vendor_name, bill_name = parts[0].strip(), parts[1].strip()
                                    vendor_info = vendor_lookup.get((vendor_name, bill_name), {})
                                    percentage = vendor_info.get('pct', 0)
                                    key = (vendor_name, bill_name)
                                else:
                                    percentage = 0
                                    key = None
                            
                            # Get linked activities and build breakdown showing each activity's contribution
                            linked_acts = activity_matches.get(key, [])
                            activities_details = []
                            activities_contribution_sum = 0
                            
                            for act_info in linked_acts:
                                act_key = (act_info['activity'], act_info['sub_activity'])
                                activity_pct = act_pct_lookup.get(act_key, {}).get(month, 0)
                                activity_sales_cost = act_sales_lookup.get(act_key, 0)
                                
                                # This activity's contribution: activity_pct/100 × sales/cost
                                activity_contribution = (activity_pct / 100) * activity_sales_cost
                                activities_contribution_sum += activity_contribution
                                
                                # Add detail for this activity
                                activity_display = f"{act_info['activity']}"
                                if act_info['sub_activity']:
                                    activity_display += f"/{act_info['sub_activity']}"
                                
                                activities_details.append(
                                    f"{activity_display}: ({activity_pct:.1f}% ÷ 100) × ${activity_sales_cost:,.2f} = ${activity_contribution:,.2f}"
                                )
                            
                            # Build the complete breakdown
                            if activities_details:
                                activities_str = " | ".join(activities_details)
                                breakdown = f"{month}: {percentage:.1f}% × ({activities_str}) = ${numeric_val:,.2f}"
                            else:
                                breakdown = f"{month}: ${numeric_val:,.2f}"
                        except Exception as e:
                            breakdown = f"{month}: ${numeric_val:,.2f}"
                        
                        monthly_breakdowns.append(breakdown)
            
            # Build tooltip with formula and calculations
            breakdown_text = " | ".join(monthly_breakdowns) if monthly_breakdowns else "No values"
            
            tooltip_text = (
                f"{row_name}\n"
                f"\n"
                f"FORMULA: (% ÷ 100) × (Activity % ÷ 100) × Total Sales\n"
                f"\n"
                f"BREAKDOWN: {breakdown_text}"
            )
            
            tooltip_data.append(tooltip_text)
        
        # Add tooltip as a hidden column
        display_df.insert(0, '_tooltip', tooltip_data)
        display_df.insert(1, '📋 Info', ['ℹ️'] * len(display_df))
        
        # Configure AgGrid with custom column definitions
        gb = GridOptionsBuilder.from_dataframe(display_df)
        
        # Configure all columns
        for col in display_df.columns:
            if col == '_tooltip':
                gb.configure_column(
                    col,
                    hide=True,
                    suppressMovableColumns=True
                )
            elif col == '📋 Info':
                gb.configure_column(
                    col,
                    width=50,
                    suppressMovableColumns=False,
                    cellStyle={'textAlign': 'center', 'cursor': 'pointer'},
                    tooltipField='_tooltip',
                    tooltipComponentParams={'color': 'black'},
                )
            else:
                gb.configure_column(
                    col,
                    wrapText=True,
                    autoHeight=True,
                    tooltipField='_tooltip',
                    tooltipComponentParams={'color': 'black'},
                )
        
        gb.configure_grid_options(
            domLayout='normal',
            enableRangeSelection=True,
            suppressMovableColumns=False,
        )
        
        grid_options = gb.build()
        
        # Display table with AgGrid
        st.markdown(f"**{table_name}** (💡 hover over rows for formula details)")
        AgGrid(
            display_df,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            height=400,
            theme='light'
        )
        
    except ImportError:
        # Fallback to regular dataframe if AgGrid not installed
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info("💡 Tip: Install `streamlit-aggrid` for hover tooltips with formula details")


# Initialize session state for dynamic months
if 'project_months' not in st.session_state:
    config = get_project_config()
    if config:
        try:
            start_month = config.get('Start_Month', 'January')
            start_year = int(config.get('Start_Year', 2025))
            duration_months = int(config.get('Duration_Months', 12))
            om_months = int(config.get('OM_Months', 0))
            dlp_months = int(config.get('DLP_Months', 0))
            st.session_state.project_months = get_month_list(start_month, start_year, duration_months, om_months, dlp_months)
        except:
            st.session_state.project_months = None
    else:
        st.session_state.project_months = None

if 'page' not in st.session_state:
    st.session_state.page = '🏠 Home'

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation")
    pages = ['🏠 Home', '📋 Activities', '🧾 Invoice', '🛒 Vendor', '📈 Cash Flow Curve']
    page = st.radio("Select Section:", 
                    options=pages,
                    key='page_radio')
    st.session_state.page = page

# ==================== HOME PAGE (Setup + Home merged) ====================
if st.session_state.page == '🏠 Home':
    st.markdown('### 🏠 Home')

    st.info("""
    This application helps you:
    - 📋 Add and track activities with sub-activities
    - 📅 Distribute work percentages across months
    - 💰 Track costs and sales (optional)
    - 📊 View summaries and analytics

    **Quick Start:**
    1. Go to "Add Activity" to create a new activity
    2. Assign work percentages for each month
    3. (Optional) Add cost and sales information
    4. View all data in "View Activities"
    """)

    # Quick stats
    col1, col2, col3 = st.columns(3)
    activities = load_activities()

    with col1:
        st.metric("Total Activities", len(activities))

    with col2:
        # Count unique activity names
        unique_activities = len(set([a.get('Activity', '') for a in activities]))
        st.metric("Unique Activities", unique_activities)

    with col3:
        # Count with cost/sales data
        cost_sales_data = load_cost_sales()
        st.metric("With Cost/Sales", len(cost_sales_data))


    st.divider()

    st.info("""
    Configure your project timeline before adding activities.
    This defines the duration, O&M period, and DLP for all invoicing tables.
    """)

    config = get_project_config()

    # Get current config values
    current_duration = 12
    current_start_month = 'January'
    current_start_year = 2025
    current_om_months = 0
    current_dlp_months = 0

    if config:
        try:
            current_duration = int(config.get('Duration_Months', 12))
            current_start_month = config.get('Start_Month', 'January')
            current_start_year = int(config.get('Start_Year', 2025))
            current_om_months = int(config.get('OM_Months', 0))
            current_dlp_months = int(config.get('DLP_Months', 0))
        except:
            pass

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Project Duration")
        duration_months = st.number_input(
            "Project Duration (months)",
            min_value=1,
            max_value=120,
            value=current_duration,
            step=1,
            help="Total months for the project phase"
        )

        start_month = st.selectbox(
            "Start Month",
            options=['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'],
            index=['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December'].index(current_start_month),
            help="First month of the project"
        )

        start_year = st.number_input(
            "Start Year",
            min_value=2020,
            max_value=2050,
            value=current_start_year,
            step=1,
            help="Year the project starts"
        )

    with col2:
        st.subheader("O&M Period")
        om_months = st.number_input(
            "O&M Duration (months)",
            min_value=0,
            max_value=240,
            value=current_om_months,
            step=1,
            help="Operations & Maintenance period in months (0 = no O&M)"
        )

    with col3:
        st.subheader("DLP Period")
        dlp_months = st.number_input(
            "DLP Duration (months)",
            min_value=0,
            max_value=240,
            value=current_dlp_months,
            step=1,
            help="Data Lifecycle Period in months (0 = no DLP)"
        )

    # Calculate total months
    total_months = duration_months + om_months + dlp_months

    # Preview timeline
    st.subheader("Timeline Preview")
    preview_months = get_month_list(start_month, start_year, duration_months, om_months, dlp_months)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project Months", duration_months)
    with col2:
        st.metric("O&M Period", f"{om_months} months")
    with col3:
        st.metric("DLP Period", f"{dlp_months} months")
    with col4:
        st.metric("Total Timeline", f"{total_months} months")

    # Show first and last months
    if preview_months:
        st.write(f"**Timeline**: {preview_months[0]} → {preview_months[-1]}")
        st.write(f"**Total Months**: {len(preview_months)}")

    # Show all months in expandable section
    with st.expander("View All Months"):
        cols = st.columns(4)
        for i, month in enumerate(preview_months):
            with cols[i % 4]:
                st.write(f"✓ {month}")

    # Save button
    if st.button("💾 Save Project Configuration", type="primary", use_container_width=True):
        save_project_config(duration_months, start_month, start_year, om_months, dlp_months)
        st.session_state.project_months = preview_months
        st.success("✅ Project configuration saved!")
        st.info(f"Your project timeline: {duration_months} months + {om_months} months O&M + {dlp_months} months DLP = {total_months} months total from {start_month} {start_year}")

    st.divider()

    # ============ CLEANUP ORPHANED RECORDS ============
    st.subheader("🧹 Data Cleanup & Maintenance")
    st.markdown("""
    Over time, orphaned records may accumulate in your system:
    - Matching records where activities or milestones were deleted externally
    - Advance records for milestones that no longer exist
    - Vendor matches referencing deleted activities or bills

    This tool scans and removes all orphaned records to maintain data integrity.
    """)

    if st.button("🔍 Scan & Clean Orphaned Records", type="secondary", use_container_width=True):
        with st.spinner("Scanning for orphaned records..."):
            has_orphans, total_removed, results = cleanup_all_orphaned_records()

        if has_orphans:
            st.success(f"✅ Cleanup completed! Removed {total_removed} orphaned records.")

            # Show detailed results
            with st.expander("📊 Detailed Results"):
                for i, (found, removed, msg) in enumerate(results, 1):
                    if found:
                        st.write(f"**{i}. {msg}**")
                    else:
                        st.write(f"✓ {msg}")

            st.info("Your data is now clean and consistent. Deleted items will no longer appear in reports.")
        else:
            st.info("✅ No orphaned records found. Your data is already clean!")

    st.divider()
    st.markdown("**Next Step**: Go to 'Add Activity' to start creating activities")


# ==================== ACTIVITIES PAGE ====================
elif st.session_state.page == '📋 Activities':
    st.markdown('### 📋 Activities')

    act_tab1, act_tab2, act_tab3 = st.tabs(['Add Activity', 'View Activities', 'Cost & Sales'])

    with act_tab1:

        with st.form("add_activity_form"):
            # Activity Name
            activity_name = st.text_input("Activity Name *", placeholder="e.g., Project Alpha, Website Redesign")

            calc_months = get_calculation_months()

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Start Date")
                start_month = st.selectbox("Start Month", options=calc_months, key='start_month_select')

            with col2:
                st.subheader("End Date")
                end_month = st.selectbox("End Month", options=calc_months, key='end_month_select')

            # Sub-activities
            st.subheader("Sub-Activities (Optional)")
            num_sub = st.number_input("Number of sub-activities", min_value=0, max_value=10, value=0)

            sub_activities = []
            if num_sub > 0:
                for i in range(num_sub):
                    sub_name = st.text_input(f"Sub-activity {i+1}",
                                            placeholder="e.g., Design, Development",
                                            key=f"sub_{i}")
                    if sub_name:
                        sub_activities.append(sub_name)

            # Cost & Sales (Optional)
            st.subheader("Cost & Sales (Optional)")
            include_cost_sales = st.checkbox("Add cost and sales information?")

            cost = None
            sales = None
            if include_cost_sales:
                col1, col2 = st.columns(2)
                with col1:
                    cost = st.number_input("Cost", min_value=0.0, step=0.01, value=0.0)
                with col2:
                    sales = st.number_input("Sales", min_value=0.0, step=0.01, value=0.0)

            # Work Percentages
            st.subheader("Work Distribution by Month *")

            # Get months in range
            activity_months = get_activity_months(start_month, end_month)

            if not activity_months:
                st.warning("⚠️ Invalid date range. Start month must be before or equal to end month.")
            else:
                st.info(f"Period: {start_month} to {end_month} - {len(activity_months)} months")

            # Create input fields for each month
            percentages = {}
            cols = st.columns(3)

            for idx, month in enumerate(activity_months):
                col_idx = idx % 3
                with cols[col_idx]:
                    pct = st.number_input(f"{month} (%)",
                                         min_value=0,
                                         max_value=100,
                                         value=0,
                                         key=f"pct_{month}")
                    percentages[month] = pct

            # Submit button
            submit = st.form_submit_button("Add Activity", use_container_width=True)

            if submit:
                # Validation
                if not activity_name.strip():
                    st.error("❌ Activity name is required")
                elif sum(percentages.values()) != 100:
                    st.error(f"❌ Percentages must add up to 100%. Current total: {sum(percentages.values())}%")
                else:
                    try:
                        add_activity(
                            activity_name=activity_name,
                            sub_activities=sub_activities if sub_activities else [],
                            start_month=start_month,
                            end_month=end_month,
                            percentages=percentages,
                            cost=cost if include_cost_sales and cost > 0 else None,
                            sales=sales if include_cost_sales and sales > 0 else None
                        )

                        # Store cost/sales if provided
                        if include_cost_sales and (cost or sales):
                            if sub_activities:
                                for sub in sub_activities:
                                    add_or_update_cost_sales(activity_name, sub, cost, sales)
                            else:
                                add_or_update_cost_sales(activity_name, '', cost, sales)

                        st.success("✅ Activity added successfully!")
                        st.balloons()

                    except Exception as e:
                        st.error(f"Error adding activity: {str(e)}")


    with act_tab2:

        activities = load_activities()

        if not activities:
            st.info("No activities found. Create one in the 'Add Activity' section.")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                activity_filter = st.multiselect("Filter by Activity",
                                                options=sorted(set([a.get('Activity', '') for a in activities])))

            # Apply filters
            filtered = activities
            if activity_filter:
                filtered = [a for a in filtered if a.get('Activity', '') in activity_filter]

            # Display as table
            st.subheader("Activities Table")

            # Prepare data for display
            display_data = []
            for activity in filtered:
                display_data.append({
                    'Activity': activity.get('Activity', ''),
                    'Sub-Activity': activity.get('Sub-Activity', ''),
                    'Start Month': activity.get('Start Month', ''),
                    'End Month': activity.get('End Month', ''),
                    'Cost': activity.get('Cost', ''),
                    'Sales': activity.get('Sales', '')
                })

            if display_data:
                df = pd.DataFrame(display_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

            # Show work distribution for each activity
            st.subheader("📊 Work Distribution by Activity")

            for activity in filtered:
                activity_name = activity.get('Activity', '')
                sub_activity = activity.get('Sub-Activity', '')

                # Create display label
                if sub_activity:
                    display_label = f"{activity_name} → {sub_activity}"
                else:
                    display_label = activity_name

                with st.expander(f"📈 {display_label}", expanded=False):
                    # Create work distribution data
                    work_dist = []
                    for month in MONTHS:
                        pct = activity.get(month, '0')
                        if pct and pct != '0':
                            work_dist.append({
                                'Month': month,
                                'Work Distribution %': f"{pct}%"
                            })

                    if work_dist:
                        df_work = pd.DataFrame(work_dist)
                        st.dataframe(df_work, use_container_width=True, hide_index=True)

                        # Show total
                        total = sum([float(activity.get(month, 0)) for month in MONTHS])
                        if total == 100:
                            st.success(f"✅ Total: {total}%")
                        else:
                            st.warning(f"⚠️ Total: {total}% (Expected: 100%)")
                    else:
                        st.info("No work distribution data")

            # Delete Activity Section
            st.markdown("---")
            st.subheader("🗑️ Delete Activity/Sub-Activity")

            col1, col2, col3 = st.columns(3)

            with col1:
                activities_list = sorted(set([a.get('Activity', '') for a in filtered]))
                selected_activity = st.selectbox("Select Activity to Delete", options=activities_list)

            with col2:
                if selected_activity:
                    sub_activities = sorted(set([a.get('Sub-Activity', '') for a in filtered if a.get('Activity', '') == selected_activity]))
                    sub_activities = [s for s in sub_activities if s]  # Filter out empty strings

                    if sub_activities:
                        delete_option = st.selectbox("Choose what to delete", 
                                                    options=['Delete specific sub-activity', 'Delete entire activity with all sub-activities'],
                                                    key='delete_option')
                    else:
                        delete_option = 'Delete entire activity'

            with col3:
                if selected_activity:
                    if 'Delete specific sub-activity' in delete_option if 'delete_option' in st.session_state.keys() else False:
                        sub_activities = sorted(set([a.get('Sub-Activity', '') for a in filtered if a.get('Activity', '') == selected_activity]))
                        sub_activities = [s for s in sub_activities if s]
                        if sub_activities:
                            selected_sub = st.selectbox("Select Sub-Activity", options=sub_activities, key='sub_activity_select')
                            if st.button("🗑️ Delete Sub-Activity", type="secondary"):
                                if delete_activity(selected_activity, selected_sub):
                                    # Also delete from cost & sales
                                    delete_cost_sales(selected_activity, selected_sub)
                                    st.success(f"✅ Sub-activity '{selected_sub}' of '{selected_activity}' deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete sub-activity")
                    else:
                        if st.button("🗑️ Delete Entire Activity", type="secondary"):
                            if delete_activity(selected_activity):
                                # Also delete from cost & sales
                                delete_cost_sales(selected_activity)
                                st.success(f"✅ Activity '{selected_activity}' and all its sub-activities deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete activity")

            # Download as CSV
            st.markdown("---")
            csv_data = pd.DataFrame(activities)
            csv_download = csv_data.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_download,
                file_name="activities.csv",
                mime="text/csv"
            )


    with act_tab3:

        tab1, tab2, tab3 = st.tabs(["View", "Add/Update", "Summary"])

        with tab1:
            st.subheader("Cost & Sales Records")
            cost_sales_data = load_cost_sales()

            if cost_sales_data:
                df = pd.DataFrame(cost_sales_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Download
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Cost & Sales as CSV",
                    data=csv_data,
                    file_name="cost_sales.csv",
                    mime="text/csv"
                )
            else:
                st.info("No cost & sales records found.")

        with tab2:
            st.subheader("Add or Update Cost & Sales")

            with st.form("cost_sales_form"):
                activities = load_activities()
                activity_names = sorted(set([a.get('Activity', '') for a in activities]))

                selected_activity = st.selectbox("Select Activity", activity_names)

                # Get sub-activities for selected activity
                if selected_activity:
                    subs = sorted(set([a.get('Sub-Activity', '') for a in activities 
                                      if a.get('Activity', '') == selected_activity]))
                    subs = [s for s in subs if s]  # Remove empty strings

                    if subs:
                        selected_sub = st.selectbox("Select Sub-Activity", ['Main'] + subs)
                        selected_sub = '' if selected_sub == 'Main' else selected_sub
                    else:
                        selected_sub = ''

                    col1, col2 = st.columns(2)
                    with col1:
                        cost = st.number_input("Cost", min_value=0.0, step=0.01)
                    with col2:
                        sales = st.number_input("Sales", min_value=0.0, step=0.01)

                    notes = st.text_area("Notes (optional)", height=80)

                    submit = st.form_submit_button("Save Cost & Sales", use_container_width=True)

                    if submit:
                        add_or_update_cost_sales(selected_activity, selected_sub, cost, sales, notes)
                        st.success("✅ Cost & Sales saved!")

        with tab3:
            st.subheader("Summary Statistics")

            summary = get_summary()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Cost", f"${summary['total_cost']:.2f}")
            with col2:
                st.metric("Total Sales", f"${summary['total_sales']:.2f}")
            with col3:
                st.metric("Profit", f"${summary['profit']:.2f}")
            with col4:
                st.metric("Records", summary['count'])

            if summary['total_sales'] > 0:
                margin = (summary['profit'] / summary['total_sales']) * 100
                st.info(f"📊 Profit Margin: {margin:.2f}%")


# ==================== INVOICE PAGE ====================
elif st.session_state.page == '🧾 Invoice':
    st.markdown('### 🧾 Invoice')

    inv_tab1, inv_tab2, inv_tab3 = st.tabs(['Invoice Milestones', 'Invoice Matching', 'Invoicing Report'])

    with inv_tab1:

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["View Milestones", "Add Milestone", "Edit/Delete", "Advance Payments", "Collection Period"])

        with tab1:
            st.subheader("Invoice Milestones & Sub-Milestones")
            invoices = load_invoices()

            if not invoices:
                st.info("No invoice milestones found. Create one in the 'Add Milestone' tab.")
            else:
                # Display milestones grouped
                milestones = get_all_milestones()

                for milestone in milestones:
                    with st.expander(f"📌 {milestone}", expanded=False):
                        submilestones = get_submilestones(milestone)

                        if submilestones:
                            # Display as table
                            sub_data = []
                            total_pct = 0
                            for sub in submilestones:
                                sub_data.append({
                                    'Sub-Milestone': sub['name'],
                                    'Percentage': f"{sub['percentage']}%",
                                    'Description': sub['description']
                                })
                                total_pct += sub['percentage']

                            df_subs = pd.DataFrame(sub_data)
                            st.dataframe(df_subs, use_container_width=True, hide_index=True)

                            # Show total
                            if total_pct == 100:
                                st.success(f"✅ Total: {total_pct}%")
                            else:
                                st.warning(f"⚠️ Total: {total_pct}% (must be 100%)")
                        else:
                            st.write("This is a main milestone without sub-milestones (100%)")

                # Download as CSV
                csv_data = pd.DataFrame(invoices)
                csv_download = csv_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_download,
                    file_name="invoice.csv",
                    mime="text/csv"
                )

        with tab2:
            st.subheader("Add New Invoice Milestone")

            with st.form("add_milestone_form"):
                # Milestone Name
                milestone_name = st.text_input("Milestone Name *", 
                                              placeholder="e.g., Phase 1, Design & Development")

                # Get available activities for selection
                activities_list = load_activities()
                available_activities = sorted(list(set([act.get('Activity', '') for act in activities_list if act.get('Activity', '')])))

                # Option to add sub-milestones
                has_submilestones = st.checkbox("Add Sub-Milestones?", value=False)

                num_subs = 0
                sub_milestones_dict = {}
                sub_milestones_activities_dict = {}

                if has_submilestones:
                    num_subs = st.number_input("Number of sub-milestones", min_value=1, max_value=10, value=2)

                    st.info("📌 Enter the name, percentage, and activities for each sub-milestone. All percentages must total 100%.")

                    percentages_list = []

                    for i in range(num_subs):
                        st.markdown(f"**Sub-Milestone {i+1}**")

                        col1, col2 = st.columns([2, 1])
                        with col1:
                            sub_name = st.text_input(f"Name {i+1}", 
                                                   placeholder="e.g., Analysis, Development",
                                                   key=f"sub_name_{i}")

                        with col2:
                            if sub_name:
                                pct = st.number_input(f"Percentage {i+1} (%)",
                                                    min_value=0.0,
                                                    max_value=100.0,
                                                    value=0.0,
                                                    step=0.1,
                                                    key=f"sub_pct_{i}")
                                sub_milestones_dict[sub_name] = pct
                                percentages_list.append(pct)

                        # Activities selector for this sub-milestone
                        if sub_name:
                            st.markdown(f"Activities to use for sales calculation (Sub-Milestone {i+1}):")
                            sub_activities = st.multiselect(
                                f"Select activities for {sub_name}",
                                options=available_activities,
                                key=f"sub_activities_{i}",
                                label_visibility="collapsed"
                            )
                            sub_milestones_activities_dict[sub_name] = ','.join(sub_activities) if sub_activities else ''

                        st.divider()

                    # Show total percentage
                    total_pct = sum(percentages_list)
                    if total_pct > 0:
                        st.info(f"Current Total: {total_pct}% (Target: 100%)")

                # Description
                description = st.text_area("Description (optional)", height=100)

                # Submit button
                submit = st.form_submit_button("Add Milestone", use_container_width=True)

                if submit:
                    # Validation
                    if not milestone_name.strip():
                        st.error("❌ Milestone name is required")
                    elif has_submilestones and sum([v for v in sub_milestones_dict.values()]) != 100:
                        total = sum([v for v in sub_milestones_dict.values()])
                        st.error(f"❌ Sub-milestone percentages must add up to 100%. Current total: {total}%")
                    elif has_submilestones and len(sub_milestones_dict) == 0:
                        st.error("❌ Please add at least one sub-milestone")
                    else:
                        try:
                            if has_submilestones:
                                add_invoice_milestone(milestone_name, sub_milestones_dict, description, sub_milestones_activities_dict)
                            else:
                                add_invoice_milestone(milestone_name, {}, description, {})

                            st.success("✅ Milestone added successfully!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error adding milestone: {str(e)}")

        with tab3:
            st.subheader("Edit or Delete Milestones")

            milestones = get_all_milestones()

            if not milestones:
                st.info("No milestones found to edit or delete.")
            else:
                action = st.radio("Choose Action", ["Delete", "View Details"], key='action_radio')

                if action == "Delete":
                    milestone_to_delete = st.selectbox("Select Milestone to Delete", milestones)

                    if milestone_to_delete:
                        submilestones = get_submilestones(milestone_to_delete)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Milestone:** {milestone_to_delete}")
                            st.write(f"**Sub-Milestones:** {len(submilestones)}")

                        with col2:
                            if st.button("🗑️ Delete Entire Milestone", key='delete_milestone_btn'):
                                delete_milestone(milestone_to_delete)
                                delete_matches_by_milestone(milestone_to_delete)
                                delete_advances_by_milestone(milestone_to_delete)
                                st.success(f"✅ Milestone '{milestone_to_delete}' deleted!")
                                st.rerun()

                        if submilestones:
                            st.write("---")
                            st.write("**Delete Specific Sub-Milestone:**")

                            sub_to_delete = st.selectbox("Select Sub-Milestone",
                                                        [s['name'] for s in submilestones])

                            if st.button("🗑️ Delete Sub-Milestone", key='delete_sub_btn'):
                                delete_milestone(milestone_to_delete, sub_to_delete)
                                delete_matches_by_milestone(milestone_to_delete, sub_to_delete)
                                delete_advances_by_milestone(milestone_to_delete, sub_to_delete)
                                st.success(f"✅ Sub-milestone '{sub_to_delete}' deleted!")
                                st.rerun()

                else:  # View Details
                    milestone_to_view = st.selectbox("Select Milestone", milestones)

                    if milestone_to_view:
                        submilestones = get_submilestones(milestone_to_view)

                        st.subheader(f"📌 {milestone_to_view}")

                        if submilestones:
                            sub_data = []
                            total_pct = 0
                            for sub in submilestones:
                                sub_data.append({
                                    'Sub-Milestone': sub['name'],
                                    'Percentage': f"{sub['percentage']}%",
                                    'Description': sub['description']
                                })
                                total_pct += sub['percentage']

                            df_subs = pd.DataFrame(sub_data)
                            st.dataframe(df_subs, use_container_width=True, hide_index=True)

                            # Show total
                            if total_pct == 100:
                                st.success(f"✅ Total: {total_pct}%")
                            else:
                                st.warning(f"⚠️ Total: {total_pct}% (must be 100%)")
                        else:
                            st.write("This is a main milestone without sub-milestones (100%)")

        with tab4:
            st.subheader("💰 Advance Payments Management")
            st.info("Set advance payment percentage for specific milestones in specific months. Formula: (advance% × activity% × sales)")

            # Load data
            invoices = load_invoices()
            activities = load_activities()
            current_advances = load_advances()

            if not invoices or not activities:
                st.error("❌ Please add both invoice milestones and activities first.")
            else:
                advance_tab1, advance_tab2, advance_tab3 = st.tabs(["Add Advance", "View Advances", "Manage Advances"])

                with advance_tab1:
                    st.subheader("Add New Advance Payment")

                    # Get all unique milestones
                    milestones = get_all_milestones()

                    col1, col2 = st.columns(2)

                    with col1:
                        selected_milestone = st.selectbox("Select Milestone", milestones, key='adv_milestone_select')

                    with col2:
                        # Get sub-milestones for selected milestone
                        submilestones = get_submilestones(selected_milestone)
                        sub_milestone_options = [s['name'] for s in submilestones]

                        if sub_milestone_options:
                            selected_sub_milestone = st.selectbox("Select Sub-Milestone", sub_milestone_options, key='adv_submilestone_select')
                        else:
                            st.warning("⚠️ No sub-milestones found for this milestone")
                            selected_sub_milestone = None

                    # Advance percentage
                    advance_percentage = st.slider("Advance Percentage (%)", 
                                                   min_value=0, 
                                                   max_value=100, 
                                                   value=50, 
                                                   step=1,
                                                   key='adv_percentage_slider')

                    st.divider()
                    st.write("**Advance Application Strategy**")

                    # Period Selection
                    period_type = st.radio(
                        "Apply advance to which period?",
                        options=['project', 'dlp', 'om'],
                        format_func=lambda x: {'project': '📅 Project Timeline', 'dlp': '📊 DLP Period', 'om': '🔧 O&M Period'}[x],
                        key='adv_period_select',
                        horizontal=True
                    )

                    # Strategy Selection
                    strategy = st.radio(
                        "How should the advance be applied?",
                        options=['first_month', 'all_months', 'duration', 'custom'],
                        format_func=lambda x: {
                            'first_month': '📌 First Month Only',
                            'all_months': '📆 All Months',
                            'duration': '⏱️ Duration Pattern (Every N Months)',
                            'custom': '✅ Custom Selection'
                        }[x],
                        key='adv_strategy_select'
                    )

                    # Dynamic fields based on strategy
                    frequency_interval = None
                    custom_months_selection = None

                    if strategy == 'duration':
                        st.write("**Frequency Pattern:**")
                        frequency_interval = st.selectbox(
                            "Apply advance every how many months?",
                            options=[2, 3, 4, 5, 6],
                            index=0,
                            key='adv_frequency_select',
                            label_visibility="collapsed"
                        )

                    if strategy == 'custom':
                        # Get available months for the selected period
                        calc_months = get_calculation_months()
                        period_months = get_period_months(calc_months, period_type)

                        st.write(f"**Available months in {period_type.upper()} period:** {len(period_months)}")
                        custom_months_selection = st.multiselect(
                            "Select specific months for advance:",
                            options=period_months,
                            key='adv_custom_months_select'
                        )

                    # Notes
                    notes = st.text_input("Notes (optional):", placeholder="e.g., Quarterly advance payments", key='adv_notes')

                    # Submit button
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        submit = st.button("Add Advance", key='adv_submit_btn', use_container_width=True, type='primary')

                    if submit:
                        if not selected_milestone or not selected_sub_milestone:
                            st.error("❌ Please select both milestone and sub-milestone")
                        elif advance_percentage <= 0:
                            st.error("❌ Advance percentage must be greater than 0")
                        elif strategy == 'duration' and not frequency_interval:
                            st.error("❌ Please select frequency interval")
                        elif strategy == 'custom' and not custom_months_selection:
                            st.error("❌ Please select at least one month")
                        else:
                            try:
                                calc_months = get_calculation_months()
                                count = add_advance_with_strategy(
                                    milestone_name=selected_milestone,
                                    sub_milestone_name=selected_sub_milestone,
                                    advance_percentage=advance_percentage,
                                    strategy=strategy,
                                    period_type=period_type,
                                    all_months=calc_months,
                                    notes=notes,
                                    frequency_interval=frequency_interval,
                                    custom_months=custom_months_selection
                                )
                                st.success(f"✅ Advance payment added for {count} month(s)!")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error adding advance: {str(e)}")

                with advance_tab2:
                    st.subheader("View All Advances")

                    if not current_advances:
                        st.info("No advance payments configured yet.")
                    else:
                        # Display advances as table
                        advance_data = []
                        for adv in current_advances:
                            advance_data.append({
                                'Milestone': adv.get('Milestone', ''),
                                'Sub-Milestone': adv.get('Sub-Milestone', ''),
                                'Month': adv.get('Month', ''),
                                'Advance %': f"{adv.get('Advance_Percentage', 0)}%",
                                'Notes': adv.get('Notes', '')
                            })

                        df_advances = pd.DataFrame(advance_data)
                        st.dataframe(df_advances, use_container_width=True, hide_index=True)

                        # Download as CSV
                        csv_data = pd.DataFrame(current_advances)
                        csv_download = csv_data.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_download,
                            file_name="invoice_advance.csv",
                            mime="text/csv"
                        )

                with advance_tab3:
                    st.subheader("Manage Advances")

                    if not current_advances:
                        st.info("No advance payments to manage.")
                    else:
                        # Create list of advances for selection
                        advance_options = []
                        for adv in current_advances:
                            label = f"{adv.get('Milestone')} → {adv.get('Sub-Milestone')} ({adv.get('Month')}) - {adv.get('Advance_Percentage')}%"
                            advance_options.append({
                                'label': label,
                                'milestone': adv.get('Milestone'),
                                'sub_milestone': adv.get('Sub-Milestone'),
                                'month': adv.get('Month')
                            })

                        selected_advance_idx = st.selectbox("Select Advance to Delete",
                                                           range(len(advance_options)),
                                                           format_func=lambda idx: advance_options[idx]['label'],
                                                           key='adv_delete_select')

                        if selected_advance_idx is not None:
                            selected_adv = advance_options[selected_advance_idx]

                            if st.button("🗑️ Delete This Advance", key='delete_advance_btn'):
                                delete_advance(
                                    selected_adv['milestone'],
                                    selected_adv['sub_milestone'],
                                    selected_adv['month']
                                )
                                st.success("✅ Advance payment deleted!")
                                st.rerun()

        with tab5:
            st.subheader("⏳ Global Collection Period Management")
            st.info("Set a single collection period (credit days) that applies to the entire invoice. This shifts all invoicing amounts forward by the specified number of months.")

            current_collection = get_all_collection()
            current_days = get_collection_days()
            current_months = get_collection_months()

            col1, col2 = st.columns([2, 1])

            with col1:
                st.write("### Set Collection Period")

                # Collection days slider
                collection_days = st.slider("Credit Days (Collection Period)", 
                                           min_value=0, 
                                           max_value=365, 
                                           value=current_days if current_days > 0 else 30, 
                                           step=1,
                                           key='global_coll_days_slider')

                # Show calculated months
                if collection_days > 0:
                    collection_months = days_to_months(collection_days)
                    st.success(f"📅 **{collection_days} days = {collection_months} month(s)** - All invoice amounts will shift forward by {collection_months} month(s)")
                else:
                    st.info("📅 **0 days = No collection period** - Invoice amounts will not be shifted")

                # Notes
                notes = st.text_area("Notes (optional):", 
                                   value=current_collection.get('Notes', '') if current_collection else '',
                                   placeholder="e.g., Standard credit terms for this invoice",
                                   key='global_coll_notes')

                col_submit, col_delete = st.columns(2)

                with col_submit:
                    if st.button("💾 Save Collection Period", use_container_width=True, key='save_coll_btn'):
                        try:
                            set_collection(collection_days, notes)
                            st.success(f"✅ Collection period saved: {collection_days} days ({days_to_months(collection_days)} months)")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving collection period: {str(e)}")

                with col_delete:
                    if current_days > 0:
                        if st.button("🗑️ Clear Collection", use_container_width=True, key='clear_coll_btn'):
                            try:
                                delete_collection()
                                st.success("✅ Collection period cleared!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error clearing collection: {str(e)}")

            with col2:
                st.write("### Current Setting")

                if current_days > 0:
                    st.metric("Credit Days", f"{current_days} days")
                    st.metric("Shift Months", f"{current_months} month(s)")
                    st.metric("Status", "✅ Active")
                else:
                    st.info("No collection period set")

        # ==================== VENDOR PAYMENT PAGE ====================

    with inv_tab2:
        st.info("💡 Multiple activities/sub-activities can be matched to the same sub-milestone. The calculations will sum them all together.")

        # Load data
        activities = load_activities()
        invoices = load_invoices()
        current_matches = load_matches()

        if not activities:
            st.error("❌ No activities found. Please add activities first.")
        elif not invoices:
            st.error("❌ No invoices found. Please add invoice milestones first.")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["Create Matches", "View by Sub-Milestone", "View All Matches", "Manage Matches"])

            with tab1:
                st.subheader("Create New Match (Add Multiple Activities to Same Milestone)")

                # Get all activities and their sub-activities
                activities_and_subs = get_all_activities_and_subs(activities)
                # Get all sub-milestones
                submilestones = get_all_submilestones(invoices)

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**📋 Select Schedule Item (Left)**")

                    if activities_and_subs:
                        # Create display strings for activities
                        activity_options = []
                        for activity_name, sub_activity in activities_and_subs:
                            if sub_activity:
                                display_text = f"{activity_name} → {sub_activity}"
                            else:
                                display_text = f"{activity_name}"
                            activity_options.append((activity_name, sub_activity, display_text))

                        selected_activity_idx = st.selectbox(
                            "Choose an activity or sub-activity:",
                            range(len(activity_options)),
                            format_func=lambda idx: activity_options[idx][2],
                            key='activity_select'
                        )

                        selected_activity, selected_sub_activity, _ = activity_options[selected_activity_idx]

                with col2:
                    st.write("**🎯 Select Milestone Item (Right)**")

                    if submilestones:
                        # Create display strings for sub-milestones
                        submilestone_options = []
                        for milestone_name, sub_milestone, percentage in submilestones:
                            display_text = f"{milestone_name} → {sub_milestone} ({percentage}%)"
                            submilestone_options.append((milestone_name, sub_milestone, display_text))

                        selected_submilestone_idx = st.selectbox(
                            "Choose a sub-milestone:",
                            range(len(submilestone_options)),
                            format_func=lambda idx: submilestone_options[idx][2],
                            key='submilestone_select'
                        )

                        selected_milestone, selected_sub_milestone, _ = submilestone_options[selected_submilestone_idx]

                        # Show current matches for this sub-milestone
                        submilestone_matches = [m for m in current_matches if m.get('Sub-Milestone') == selected_sub_milestone]
                        if submilestone_matches:
                            st.write("**Already matched activities:**")
                            for match in submilestone_matches:
                                act_display = f"{match.get('Activity')} → {match.get('Sub-Activity')}" if match.get('Sub-Activity') else match.get('Activity')
                                st.write(f"  • {act_display}")

                st.divider()

                # Link strength and notes
                col1, col2 = st.columns(2)

                with col1:
                    link_strength = st.select_slider(
                        "Link Strength:",
                        options=['Weak', 'Medium', 'Strong'],
                        value='Medium'
                    )

                with col2:
                    notes = st.text_input("Notes (optional):", placeholder="Any additional notes about this match")

                # Create button with confirmation
                if st.button("🔗 Create Link", key='create_link_btn', use_container_width=True):
                    # Check if match already exists
                    existing = get_matches_by_activity(selected_activity, selected_sub_activity)
                    existing = [m for m in existing if m.get('Sub-Milestone') == selected_sub_milestone]

                    if existing:
                        st.warning(f"⚠️ A match already exists between {selected_activity} (Sub: {selected_sub_activity if selected_sub_activity else 'None'}) and {selected_sub_milestone}")
                    else:
                        add_match(
                            activity=selected_activity,
                            sub_activity=selected_sub_activity,
                            sub_milestone=selected_sub_milestone,
                            milestone=selected_milestone,
                            link_strength=link_strength,
                            notes=notes
                        )
                        st.success(f"✅ Link created successfully!")
                        st.balloons()
                        st.rerun()

            with tab2:
                st.subheader("Matches by Sub-Milestone")
                st.write("View all activities/sub-activities matched to each sub-milestone")

                if current_matches:
                    # Group matches by sub-milestone
                    submilestones_dict = {}
                    for match in current_matches:
                        sub_milestone = match.get('Sub-Milestone', '')
                        milestone = match.get('Milestone', '')

                        if sub_milestone not in submilestones_dict:
                            submilestones_dict[sub_milestone] = {
                                'milestone': milestone,
                                'activities': []
                            }

                        activity = match.get('Activity', '')
                        sub_activity = match.get('Sub-Activity', '')
                        activity_display = f"{activity} → {sub_activity}" if sub_activity else activity

                        submilestones_dict[sub_milestone]['activities'].append({
                            'display': activity_display,
                            'strength': match.get('Link Strength', 'Medium'),
                            'notes': match.get('Notes', '')
                        })

                    # Display each sub-milestone with its activities
                    for sub_milestone, data in sorted(submilestones_dict.items()):
                        milestone = data['milestone']
                        activities_list = data['activities']

                        with st.expander(f"🎯 {milestone} → {sub_milestone} ({len(activities_list)} activities)", expanded=False):
                            for activity_data in activities_list:
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"📋 {activity_data['display']}")
                                with col2:
                                    strength_color = {'Strong': '🟢', 'Medium': '🟡', 'Weak': '🔴'}.get(activity_data['strength'], '🟡')
                                    st.write(f"{strength_color} {activity_data['strength']}")
                                if activity_data['notes']:
                                    st.caption(f"Note: {activity_data['notes']}")
                else:
                    st.info("No matches created yet.")

            with tab3:
                st.subheader("All Activity-Milestone Matches (Table View)")

                if current_matches:
                    # Display matches with visual representation
                    match_df = pd.DataFrame(current_matches)

                    # Rename columns for display
                    display_df = match_df[['Activity', 'Sub-Activity', 'Sub-Milestone', 'Milestone', 'Link Strength', 'Notes']].copy()
                    display_df['Activity-Link'] = display_df.apply(
                        lambda x: f"{x['Activity']} → {x['Sub-Activity']}" if x['Sub-Activity'] else x['Activity'],
                        axis=1
                    )
                    display_df['Milestone-Link'] = display_df['Milestone'] + ' → ' + display_df['Sub-Milestone']

                    # Create colored display based on link strength
                    display_columns = ['Activity-Link', 'Milestone-Link', 'Link Strength', 'Notes']
                    st.dataframe(display_df[display_columns], use_container_width=True, hide_index=True)

                    # Download matches as CSV
                    csv_data = match_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Matches as CSV",
                        data=csv_data,
                        file_name="activity_milestone_matching.csv",
                        mime="text/csv"
                    )

                    # Summary statistics
                    st.divider()
                    st.subheader("Match Summary")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Matches", len(current_matches))

                    with col2:
                        strong_count = len([m for m in current_matches if m.get('Link Strength') == 'Strong'])
                        st.metric("Strong Links", strong_count)

                    with col3:
                        medium_count = len([m for m in current_matches if m.get('Link Strength') == 'Medium'])
                        st.metric("Medium Links", medium_count)

                    with col4:
                        weak_count = len([m for m in current_matches if m.get('Link Strength') == 'Weak'])
                        st.metric("Weak Links", weak_count)

                    # Show formula info
                    st.info("""
                    **Calculation Formula:**

                    For each sub-milestone, the final calculated value per month is:

                    **Final Value = Sub-Milestone % × SUM(Activity Sales × Activity Month %)**

                    When multiple activities are matched to the same sub-milestone, their (Sales × Month %) values are summed first, then multiplied by the sub-milestone percentage.
                    """)
                else:
                    st.info("No matches created yet. Create your first match in the 'Create Matches' tab.")

            with tab4:
                st.subheader("Manage Existing Matches")

                if current_matches:
                    # Create match identifiers for deletion
                    match_display = []
                    for idx, match in enumerate(current_matches):
                        activity = match.get('Activity', '')
                        sub_activity = match.get('Sub-Activity', '')
                        sub_milestone = match.get('Sub-Milestone', '')

                        activity_display = f"{activity} → {sub_activity}" if sub_activity else activity
                        display_text = f"{activity_display} 🔗 {sub_milestone}"
                        match_display.append((idx, display_text))

                    selected_match_idx = st.selectbox(
                        "Select a match to delete:",
                        [m[0] for m in match_display],
                        format_func=lambda idx: [m[1] for m in match_display if m[0] == idx][0]
                    )

                    selected_match = current_matches[selected_match_idx]

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Match Details:**")
                        st.write(f"Activity: {selected_match.get('Activity')}")
                        st.write(f"Sub-Activity: {selected_match.get('Sub-Activity') or 'N/A'}")
                        st.write(f"Sub-Milestone: {selected_match.get('Sub-Milestone')}")
                        st.write(f"Link Strength: {selected_match.get('Link Strength')}")
                        st.write(f"Notes: {selected_match.get('Notes') or 'None'}")

                    with col2:
                        if st.button("🗑️ Delete This Match", key='delete_match_btn', use_container_width=True):
                            delete_match(
                                activity=selected_match.get('Activity'),
                                sub_activity=selected_match.get('Sub-Activity'),
                                sub_milestone=selected_match.get('Sub-Milestone')
                            )
                            st.success("✅ Match deleted successfully!")
                            st.rerun()
                else:
                    st.info("No matches to manage yet.")

        # ==================== VENDOR PAYMENT MATCHING PAGE ====================

    with inv_tab3:

        # Check if we have data
        activities = load_activities()
        invoices = load_invoices()
        matches = load_matches()

        if not activities:
            st.error("❌ No activities found. Please add activities first.")
        elif not invoices:
            st.error("❌ No invoice milestones found. Please add invoice milestones first.")
        elif not matches:
            st.error("❌ No activity-milestone matches found. Please create matches first.")
        else:
            # Calculation formula explanation
            with st.expander("📖 Formula Explanation", expanded=False):
                st.info("""
                **Invoicing Calculation Formula:**

                For each month and each sub-milestone:
                ```
                Value = (Sub-Milestone Percentage / 100) × 
                        (Activity Percentage for Month / 100) × 
                        (Sales for Activity)
                ```

                This calculates what portion of each activity's sales should be invoiced 
                based on both the activity work percentage and the milestone percentage.
                """)

            # Tab selection
            calc_months = get_calculation_months()

            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
                ["Sub-Milestones", "By Milestone", "By Activity", "Totals", "Advances", "Collection", "Export"]
            )

            # Calculate all data
            invoicing_df = calculate_invoicing_table()
            milestone_df = calculate_by_milestone()
            activity_df = calculate_by_activity()
            summary_totals = calculate_summary_totals()
            advance_df = calculate_advance_table()
            advance_milestone_df = calculate_advance_by_milestone()
            net_invoicing_df = calculate_net_invoicing_table()
            net_milestone_df = calculate_net_by_milestone()
            net_summary_totals = calculate_net_summary_totals()
            collection_df = calculate_collection_table()
            collection_milestone_df = calculate_collection_by_milestone()
            collection_summary_totals = calculate_collection_summary_totals()
            net_collection_df = calculate_net_collection_table()
            net_collection_milestone_df = calculate_net_collection_by_milestone()

            # ── Milestone / Sub-Milestone Filter ─────────────────────────────────
            st.markdown("---")
            st.markdown("#### 🔍 Filter Charts & Tables by Milestone")
            col_filter1, col_filter2 = st.columns(2)

            all_milestones_list = get_all_milestones()

            with col_filter1:
                selected_milestones_filter = st.multiselect(
                    "Filter by Milestone (leave blank = show all)",
                    options=all_milestones_list,
                    default=[],
                    key='invoicing_milestone_filter',
                    help="Select one or more milestones to focus the tables and charts on those milestones only."
                )

            # Derive available sub-milestones from selected milestones
            available_submilestones = []
            if selected_milestones_filter:
                for m in selected_milestones_filter:
                    subs = get_submilestones(m)
                    for s in subs:
                        available_submilestones.append(f"{m} > {s['name']}")

            with col_filter2:
                selected_submilestones_filter = st.multiselect(
                    "Filter by Sub-Milestone (optional, refines Milestone selection)",
                    options=available_submilestones,
                    default=[],
                    key='invoicing_submilestone_filter',
                    help="Optionally narrow down to specific sub-milestones within the selected milestones."
                )

            if selected_milestones_filter or selected_submilestones_filter:
                filter_label = ", ".join(selected_submilestones_filter or selected_milestones_filter)
                st.info(f"📌 Showing data for: **{filter_label}**")
            st.markdown("---")

            # ── Apply Filters ────────────────────────────────────────────────────
            def _filter_df(df, col_name, sel_milestones, sel_subs):
                """Filter DataFrame rows by milestone/sub-milestone, preserving non-data rows."""
                if df.empty or (not sel_milestones and not sel_subs):
                    return df
                if col_name not in df.columns:
                    return df
                # Separate special rows (TOTAL, CUMULATIVE) from data rows
                special_mask = df[col_name].isin(['TOTAL', 'CUMULATIVE'])
                data_rows = df[~special_mask].copy()
                if sel_subs:
                    data_rows = data_rows[data_rows[col_name].isin(sel_subs)]
                elif sel_milestones:
                    data_rows = data_rows[data_rows[col_name].apply(
                        lambda x: any(str(x).startswith(m + ' >') or str(x) == m for m in sel_milestones)
                    )]
                return data_rows  # Return filtered data only (totals become inaccurate after filter)

            if selected_milestones_filter or selected_submilestones_filter:
                invoicing_df        = _filter_df(invoicing_df,       'Sub-Milestone', selected_milestones_filter, selected_submilestones_filter)
                net_invoicing_df    = _filter_df(net_invoicing_df,   'Sub-Milestone', selected_milestones_filter, selected_submilestones_filter)
                advance_df          = _filter_df(advance_df,         'Sub-Milestone', selected_milestones_filter, selected_submilestones_filter)
                collection_df       = _filter_df(collection_df,      'Sub-Milestone', selected_milestones_filter, selected_submilestones_filter)
                net_collection_df   = _filter_df(net_collection_df,  'Sub-Milestone', selected_milestones_filter, selected_submilestones_filter)
                milestone_df        = _filter_df(milestone_df,       'Milestone',     selected_milestones_filter, [])
                net_milestone_df    = _filter_df(net_milestone_df,   'Milestone',     selected_milestones_filter, [])
                advance_milestone_df= _filter_df(advance_milestone_df,'Milestone',    selected_milestones_filter, [])
                # Recalculate summary totals from filtered data
                summary_totals = {}
                net_summary_totals = {}
                for _m in calc_months:
                    summary_totals[_m] = float(invoicing_df[_m].sum()) if (not invoicing_df.empty and _m in invoicing_df.columns) else 0.0
                    net_summary_totals[_m] = float(net_invoicing_df[_m].sum()) if (not net_invoicing_df.empty and _m in net_invoicing_df.columns) else 0.0

            with tab1:

                st.subheader("Detailed Sub-Milestone Breakdown")

                # Show both original and net amounts
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Original invoicing value** (before deducting advances)")
                    if not invoicing_df.empty:
                        # Keep unformatted for tooltips, create formatted for display
                        unformatted_df = invoicing_df.copy()
                        display_df = invoicing_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Original Invoicing - By Sub-Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Show calculation details
                        with st.expander("📖 View Calculation Details"):
                            st.write("**How Invoicing Values Are Calculated:**")
                            st.write("""
                            For each **Sub-Milestone** and **Month**:

                            1. **Get sub-milestone percentage:**
                               - This is the percentage value assigned to the sub-milestone
                               - Example: "Phase 1" might be 30% of "Project Delivery"

                            2. **Sum all linked activities for this month:**
                               - For each activity linked to this sub-milestone:
                               - Activity Contribution = (Activity Monthly % ÷ 100) × Activity Sales

                            3. **Apply sub-milestone percentage:**
                               - Month Value = (Sub-Milestone % ÷ 100) × Sum of all activities

                            ### Example Calculation:
                            **Sub-Milestone:** "Design Phase" (25% of total)
                            - Activity "UI Design" is 50% in January with $10,000 sales
                            - Activity "UX Design" is 50% in January with $5,000 sales
                            - **Step 1:** Sum = (50/100 × $10,000) + (50/100 × $5,000) = $7,500
                            - **Step 2:** Invoicing = (25/100) × $7,500 = **$1,875**
                            """)

                        # Download as CSV
                        csv_data = invoicing_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_sub_milestones_original.csv",
                            mime="text/csv",
                            key='download_original_sub'
                        )
                    else:
                        st.warning("⚠️ No calculations available. Make sure all activities have sales data and are matched to milestones.")

                with sub_tab2:
                    st.write("**Advance amounts** (deducted from original)")
                    if not advance_df.empty:
                        # Format for display
                        unformatted_df = advance_df.copy()
                        display_df = advance_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        display_table_with_hover_tooltips(display_df, "Advance Payments - By Sub-Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Download as CSV
                        csv_data = advance_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_sub_milestones_advances.csv",
                            mime="text/csv",
                            key='download_advances_sub'
                        )
                    else:
                        st.info("ℹ️ No advance payments configured.")

                with sub_tab3:
                    st.write("**Net invoicing value** (Original - Advances)")
                    if not net_invoicing_df.empty:
                        # Format for display
                        unformatted_df = net_invoicing_df.copy()
                        display_df = net_invoicing_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Net Invoicing - By Sub-Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Download as CSV
                        csv_data = net_invoicing_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_sub_milestones_net.csv",
                            mime="text/csv",
                            key='download_net_sub'
                        )
                    else:
                        st.warning("⚠️ No calculations available.")

            with tab2:
                st.subheader("Total by Milestone")

                # Show both original and net amounts
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Original invoicing value** (before deducting advances)")
                    if not milestone_df.empty:
                        # Format for display
                        unformatted_df = milestone_df.copy()
                        display_df = milestone_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Original Invoicing - By Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Show calculation details
                        with st.expander("📖 View Calculation Details"):
                            st.write("**How Milestone Totals Are Calculated:**")
                            st.write("""
                            Each milestone's total is the **sum of all its sub-milestones** for each month:

                            - **Milestone Total (Month) = Sub-Milestone 1 (Month) + Sub-Milestone 2 (Month) + ... + Sub-Milestone N (Month)**

                            Each sub-milestone value is calculated using:
                            - **(Sub-Milestone % ÷ 100) × SUM of linked activities**
                            """)

                        # Download as CSV
                        csv_data = milestone_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_by_milestone_original.csv",
                            mime="text/csv",
                            key='download_original_milestone'
                        )
                    else:
                        st.warning("⚠️ No calculations available.")

                with sub_tab2:
                    st.write("**Total advance amounts** by milestone")
                    if not advance_milestone_df.empty:
                        # Format for display
                        unformatted_df = advance_milestone_df.copy()
                        display_df = advance_milestone_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        display_table_with_hover_tooltips(display_df, "Advance Payments - By Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Download as CSV
                        csv_data = advance_milestone_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_by_milestone_advances.csv",
                            mime="text/csv",
                            key='download_advances_milestone'
                        )
                    else:
                        st.info("ℹ️ No advance payments configured.")

                with sub_tab3:
                    st.write("**Net invoicing value** (Original - Advances)")
                    if not net_milestone_df.empty:
                        # Format for display
                        unformatted_df = net_milestone_df.copy()
                        display_df = net_milestone_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Net Invoicing - By Milestone", unformatted_df=unformatted_df, table_type="invoice")

                        # Download as CSV
                        csv_data = net_milestone_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_by_milestone_net.csv",
                            mime="text/csv",
                            key='download_net_milestone'
                        )
                    else:
                        st.warning("⚠️ No calculations available.")

            with tab3:
                st.subheader("Total by Activity")
                st.write("Aggregated values for each activity/sub-activity across all months.")

                if not activity_df.empty:
                    # Format for display
                    unformatted_df = activity_df.copy()
                    display_df = activity_df.copy()
                    for month in calc_months:
                        if month in display_df.columns:
                            display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                    display_table_with_hover_tooltips(display_df, "Total by Activity", unformatted_df=unformatted_df, table_type="invoice")

                    # Download as CSV
                    csv_data = activity_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Activity Summary as CSV",
                        data=csv_data,
                        file_name="invoicing_by_activity.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ No calculations available.")

            with tab4:
                st.subheader("Monthly Totals")

                # Create sub-tabs for original, advances, and net
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Total original invoicing amount** for each month across all milestones")

                    # Create summary dataframe
                    totals_data = []
                    for month in calc_months:
                        totals_data.append({'Month': month, 'Total Invoice Amount': f"${summary_totals.get(month, 0):,.2f}"})

                    totals_df = pd.DataFrame(totals_data)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.dataframe(totals_df, use_container_width=True, hide_index=True)

                    with col2:
                        # Create chart
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[summary_totals.get(month, 0) for month in calc_months],
                            marker=dict(
                                color=[summary_totals.get(month, 0) for month in calc_months],
                                colorscale='Viridis',
                                line=dict(width=0),
                            ),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>',
                            opacity=0.85
                        ))
                        fig.update_layout(
                            title=dict(text='Monthly Original Totals', font=dict(size=18)),
                            xaxis=dict(title='Month', tickangle=-45),
                            yaxis=dict(title='Amount ($)', tickformat='$,.0f'),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=60, r=20, t=60, b=80),
                            hoverlabel=dict(bgcolor='white', font_size=13),
                            bargap=0.15
                        )
                        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.05)')
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                        st.plotly_chart(fig, use_container_width=True)

                        # Grand total
                        grand_total = sum(summary_totals.values())
                        st.metric("Grand Total (All Months)", f"${grand_total:,.2f}")

                with sub_tab2:
                    st.write("**Total advance payments** for each month across all milestones")

                    # Calculate advance totals by month
                    advance_totals = {}
                    for month in calc_months:
                        advance_totals[month] = 0

                    if not advance_df.empty:
                        for _, row in advance_df.iterrows():
                            for month in calc_months:
                                if month in row.index:
                                    advance_totals[month] += row[month]

                    # Create summary dataframe
                    advance_totals_data = []
                    for month in calc_months:
                        advance_totals_data.append({'Month': month, 'Total Advance Amount': f"${advance_totals.get(month, 0):,.2f}"})

                    advance_totals_df = pd.DataFrame(advance_totals_data)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.dataframe(advance_totals_df, use_container_width=True, hide_index=True)

                    with col2:
                        # Create chart
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[advance_totals.get(month, 0) for month in calc_months],
                            marker=dict(
                                color=[advance_totals.get(month, 0) for month in calc_months],
                                colorscale='Plasma',
                                line=dict(width=0),
                            ),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>',
                            opacity=0.85
                        ))
                        fig.update_layout(
                            title=dict(text='Monthly Advance Totals', font=dict(size=18)),
                            xaxis=dict(title='Month', tickangle=-45),
                            yaxis=dict(title='Amount ($)', tickformat='$,.0f'),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=60, r=20, t=60, b=80),
                            hoverlabel=dict(bgcolor='white', font_size=13),
                            bargap=0.15
                        )
                        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.05)')
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                        st.plotly_chart(fig, use_container_width=True)

                        # Grand total
                        advance_grand_total = sum(advance_totals.values())
                        st.metric("Grand Total Advances (All Months)", f"${advance_grand_total:,.2f}")

                with sub_tab3:
                    st.write("**Net invoicing amount** (Original - Advances) for each month across all milestones")

                    # Create summary dataframe
                    net_totals_data = []
                    for month in calc_months:
                        net_amount = net_summary_totals.get(month, 0)
                        net_totals_data.append({'Month': month, 'Net Invoice Amount': f"${net_amount:,.2f}"})

                    net_totals_df = pd.DataFrame(net_totals_data)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.dataframe(net_totals_df, use_container_width=True, hide_index=True)

                    with col2:
                        # Create chart
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[net_summary_totals.get(month, 0) for month in calc_months],
                            marker=dict(
                                color=[net_summary_totals.get(month, 0) for month in calc_months],
                                colorscale='Greens',
                                line=dict(width=0),
                            ),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>',
                            opacity=0.85
                        ))
                        fig.update_layout(
                            title=dict(text='Monthly Net Invoice Totals', font=dict(size=18)),
                            xaxis=dict(title='Month', tickangle=-45),
                            yaxis=dict(title='Amount ($)', tickformat='$,.0f'),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=60, r=20, t=60, b=80),
                            hoverlabel=dict(bgcolor='white', font_size=13),
                            bargap=0.15
                        )
                        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.05)')
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                        st.plotly_chart(fig, use_container_width=True)

                        # Grand total
                        net_grand_total = sum(net_summary_totals.values())
                        st.metric("Grand Total Net (All Months)", f"${net_grand_total:,.2f}")

            with tab5:
                st.subheader("Advance Payments Breakdown")
                st.write("Advance payment amounts calculated for each sub-milestone by month.")

                if advance_df.empty:
                    st.info("ℹ️ No advance payments configured. Add advances in the Invoice section.")
                else:
                    # Display sub-milestone advances
                    st.write("**By Sub-Milestone:**")

                    display_df = advance_df.copy()
                    for month in calc_months:
                        if month in display_df.columns:
                            display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Display milestone totals
                    st.write("**Total by Milestone:**")

                    if not advance_milestone_df.empty:
                        display_df = advance_milestone_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # Download advances
                    csv_data = advance_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Advances as CSV",
                        data=csv_data,
                        file_name="invoicing_advances.csv",
                        mime="text/csv"
                    )

            with tab6:
                st.subheader("Collection Table (After Advances & Collection Period)")
                st.write("Net invoicing amounts (after advance deduction) shifted based on collection periods. Amounts move forward by the collection months.")

                # Show both sub-milestone and milestone views with comparison
                sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["Net Collection (Sub-Milestone)", "Net Collection (By Milestone)", "Comparison", "Monthly Totals"])

                with sub_tab1:
                    st.write("**Net collection amounts by sub-milestone** (shifted forward by collection period, after advance deduction)")

                    if not net_collection_df.empty:
                        display_df = net_collection_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        st.dataframe(display_df, use_container_width=True, hide_index=True)

                        # Download as CSV
                        csv_data = net_collection_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_net_collection_sub_milestones.csv",
                            mime="text/csv",
                            key='download_net_collection_sub'
                        )
                    else:
                        st.info("ℹ️ No data available for net collection.")

                with sub_tab2:
                    st.write("**Net collection amounts by milestone** (aggregated)")

                    if not net_collection_milestone_df.empty:
                        display_df = net_collection_milestone_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        st.dataframe(display_df, use_container_width=True, hide_index=True)

                        # Download as CSV
                        csv_data = net_collection_milestone_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="invoicing_net_collection_by_milestone.csv",
                            mime="text/csv",
                            key='download_net_collection_milestone'
                        )
                    else:
                        st.info("ℹ️ No data available for net collection.")

                with sub_tab3:
                    st.write("**Comparison: Original Collection vs Net Collection**")

                    if not collection_df.empty and not net_collection_df.empty:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Original Collection** (before advance)")
                            display_df = collection_df.copy()
                            for month in calc_months:
                                if month in display_df.columns:
                                    display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
                            st.dataframe(display_df, use_container_width=True, hide_index=True)

                        with col2:
                            st.write("**Net Collection** (after advance)")
                            display_df = net_collection_df.copy()
                            for month in calc_months:
                                if month in display_df.columns:
                                    display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Need data to compare.")

                with sub_tab4:
                    st.write("**Total Net Collection amounts by month**")

                    # Create summary dataframe for net collection
                    net_collection_totals_data = []
                    net_collection_grand_total = 0

                    for month in calc_months:
                        month_total = 0
                        if not net_collection_df.empty:
                            if month in net_collection_df.columns:
                                month_total = net_collection_df[month].sum()
                        net_collection_totals_data.append({
                            'Month': month,
                            'Net Collection': month_total
                        })
                        net_collection_grand_total += month_total

                    net_collection_totals_df = pd.DataFrame(net_collection_totals_data)

                    col1, col2 = st.columns(2)

                    with col1:
                        # Format for display
                        display_df = net_collection_totals_df.copy()
                        display_df['Net Collection'] = display_df['Net Collection'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(display_df, use_container_width=True, hide_index=True)

                        # Grand total
                        st.metric("Grand Total Net Collections (All Months)", f"${net_collection_grand_total:,.2f}")

                    with col2:
                        # Create chart
                        import plotly.graph_objects as go
                        net_coll_values = [row['Net Collection'] for _, row in net_collection_totals_df.iterrows()]
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=net_coll_values,
                            marker=dict(
                                color=net_coll_values,
                                colorscale='Tealgrn',
                                line=dict(width=0),
                            ),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>',
                            opacity=0.85
                        ))
                        fig.update_layout(
                            title=dict(text='Monthly Net Collection Totals', font=dict(size=18)),
                            xaxis=dict(title='Month', tickangle=-45),
                            yaxis=dict(title='Amount ($)', tickformat='$,.0f'),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(l=60, r=20, t=60, b=80),
                            hoverlabel=dict(bgcolor='white', font_size=13),
                            bargap=0.15
                        )
                        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.05)')
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                        st.plotly_chart(fig, use_container_width=True)


            with tab7:
                st.subheader("Export to Excel")

                st.write("Generate a comprehensive Excel report with all calculations.")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("📊 Generate Excel Report", use_container_width=True):
                        try:
                            # Create Excel file
                            excel_file = create_invoicing_excel_report()

                            st.download_button(
                                label="📥 Download Excel Report",
                                data=excel_file,
                                file_name="Invoicing_Report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key='excel_download'
                            )

                            st.success("✅ Excel report generated successfully!")
                        except Exception as e:
                            st.error(f"❌ Error generating Excel report: {str(e)}")

                st.divider()

                st.subheader("Report Contents")
                st.info("""
                The Excel report includes:

                📋 **Sheet 1: Sub-Milestone Details**
                - Each sub-milestone as a row
                - Monthly values from January to December
                - Total row showing monthly sums

                📋 **Sheet 2: By Milestone**
                - Each main milestone as a row
                - Aggregated values for all sub-milestones
                - Monthly totals

                📋 **Sheet 3: By Activity**
                - Each activity/sub-activity as a row
                - Monthly values showing total invoicing per activity

                All values are formatted with currency formatting for easy analysis.
                """)

        # ==================== SUMMARY PAGE ====================

# ==================== VENDOR PAGE ====================
elif st.session_state.page == '🛒 Vendor':
    st.markdown('### 🛒 Vendor')

    ven_tab1, ven_tab2, ven_tab3 = st.tabs(['Vendor Bills', 'Vendor Matching', 'Vendor Payment Report'])

    with ven_tab1:

        tab1, tab2, tab3, tab4 = st.tabs(["View Vendors", "Add Vendor", "Edit/Delete", "Payment Advances"])

        with tab1:
            st.subheader("Vendor Bills & Payments")
            vendors = load_vendors()

            if not vendors:
                st.info("No vendor payments found. Create one in the 'Add Vendor' tab.")
            else:
                # Display vendors grouped
                vendor_names = get_all_vendors()

                for vendor in vendor_names:
                    with st.expander(f"🏢 {vendor}", expanded=False):
                        bills_list = get_bills(vendor)

                        if bills_list:
                            # Display as table
                            bill_data = []
                            total_pct = 0
                            for bill in bills_list:
                                bill_data.append({
                                    'Bill': bill['name'],
                                    'Percentage': f"{bill['percentage']}%",
                                    'Credit Days': f"{bill['credit_days']} days",
                                    'Description': bill['description']
                                })
                                total_pct += bill['percentage']

                            df_bills = pd.DataFrame(bill_data)
                            st.dataframe(df_bills, use_container_width=True, hide_index=True)

                            # Show total
                            if total_pct == 100:
                                st.success(f"✅ Total: {total_pct}%")
                            else:
                                st.warning(f"⚠️ Total: {total_pct}% (should be 100%)")
                        else:
                            st.write("This is a main vendor without bills (100%)")

                # Download as CSV
                csv_data = pd.DataFrame(vendors)
                csv_download = csv_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_download,
                    file_name="vendor_payment.csv",
                    mime="text/csv"
                )

        with tab2:
            st.subheader("Add New Vendor Payment")

            with st.form("add_vendor_form"):
                # Vendor Name
                vendor_name = st.text_input("Vendor Name *", 
                                           placeholder="e.g., ABC Construction, XYZ Supplies")

                # Get available activities for selection
                activities_list = load_activities()
                available_activities = sorted(list(set([act.get('Activity', '') for act in activities_list if act.get('Activity', '')])))

                # Option to add bills
                has_bills = st.checkbox("Add Bills?", value=False)

                num_bills = 0
                bills_dict = {}

                if has_bills:
                    num_bills = st.number_input("Number of bills", min_value=1, max_value=10, value=2)

                    st.info("📋 Enter the bill name, percentage, credit days, and cost activities. All percentages should total 100%.")

                    percentages_list = []

                    for i in range(num_bills):
                        st.markdown(f"**Bill {i+1}**")
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            bill_name = st.text_input(f"Name {i+1}", 
                                                    placeholder="e.g., Labor, Materials",
                                                    key=f"bill_name_{i}")

                        with col2:
                            if bill_name:
                                pct = st.number_input(f"Percentage {i+1} (%)",
                                                    min_value=0.0,
                                                    max_value=100.0,
                                                    value=0.0,
                                                    step=0.1,
                                                    key=f"bill_pct_{i}")
                                percentages_list.append(pct)

                        with col3:
                            if bill_name:
                                credit_days = st.number_input(f"Credit Days {i+1}",
                                                             min_value=0,
                                                             max_value=365,
                                                             value=0,
                                                             step=1,
                                                             key=f"bill_days_{i}")

                        if bill_name:
                            st.markdown(f"Activities to use for cost calculation (Bill {i+1}):")
                            cost_activities = st.multiselect(
                                f"Select activities for {bill_name}",
                                options=available_activities,
                                key=f"bill_cost_act_{i}",
                                label_visibility="collapsed"
                            )
                            bills_dict[bill_name] = {
                                'percentage': pct,
                                'credit_days': credit_days,
                                'cost_from_activities': ','.join(cost_activities) if cost_activities else ''
                            }

                        st.divider()

                    # Show total percentage
                    total_pct = sum(percentages_list)
                    if total_pct > 0:
                        st.info(f"Current Total: {total_pct}% (Target: 100%)")

                # Description
                description = st.text_area("Description (optional)", height=100)

                # Submit button
                submit = st.form_submit_button("Add Vendor", use_container_width=True)

                if submit:
                    # Validation
                    if not vendor_name.strip():
                        st.error("❌ Vendor name is required")
                    elif has_bills and sum([v['percentage'] for v in bills_dict.values()]) != 100:
                        total = sum([v['percentage'] for v in bills_dict.values()])
                        st.error(f"❌ Bill percentages must add up to 100%. Current total: {total}%")
                    elif has_bills and len(bills_dict) == 0:
                        st.error("❌ Please add at least one bill")
                    else:
                        try:
                            if has_bills:
                                add_vendor_bill(vendor_name, bills_dict, description)
                            else:
                                add_vendor_bill(vendor_name, {}, description)

                            st.success("✅ Vendor added successfully!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error adding vendor: {str(e)}")

        with tab3:
            st.subheader("Edit or Delete Vendors")

            vendor_names = get_all_vendors()

            if not vendor_names:
                st.info("No vendors found to edit or delete.")
            else:
                action = st.radio("Choose Action", ["Delete", "View Details"], key='vendor_action_radio')

                if action == "Delete":
                    vendor_to_delete = st.selectbox("Select Vendor to Delete", vendor_names)

                    if vendor_to_delete:
                        bills_list = get_bills(vendor_to_delete)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Vendor:** {vendor_to_delete}")
                            st.write(f"**Bills:** {len(bills_list)}")

                        with col2:
                            if st.button("🗑️ Delete Entire Vendor", key='delete_vendor_btn'):
                                delete_vendor(vendor_to_delete)
                                delete_vendor_matches_by_bill(vendor_to_delete)
                                delete_vendor_advances_by_vendor(vendor_to_delete)
                                st.success(f"✅ Vendor '{vendor_to_delete}' deleted!")
                                st.rerun()

                        if bills_list:
                            st.write("---")
                            st.write("**Delete Specific Bill:**")

                            bill_to_delete = st.selectbox("Select Bill",
                                                         [b['name'] for b in bills_list])

                            if st.button("🗑️ Delete Bill", key='delete_bill_btn'):
                                delete_vendor(vendor_to_delete, bill_to_delete)
                                delete_vendor_matches_by_bill(vendor_to_delete, bill_to_delete)
                                delete_vendor_advances_by_vendor(vendor_to_delete, bill_to_delete)
                                st.success(f"✅ Bill '{bill_to_delete}' deleted!")
                                st.rerun()

        with tab4:
            st.subheader("💰 Vendor Payment Advances")
            st.info("💡 Configure advance payments for vendor bills. Similar to invoice advances, choose when and how to apply them.")

            vendor_names = get_all_vendors()

            if not vendor_names:
                st.info("No vendors found. Please add vendors first.")
            else:
                # Select vendor and bill
                selected_vendor = st.selectbox("Select Vendor", vendor_names, key='advance_vendor_select')

                if selected_vendor:
                    bills_list = get_bills(selected_vendor)
                    bill_names = [b['name'] for b in bills_list]

                    if bill_names:
                        selected_bill = st.selectbox("Select Bill", bill_names, key='advance_bill_select')

                        # Get existing advance if it exists
                        existing_advance = get_vendor_advance(selected_vendor, selected_bill)

                        with st.form("vendor_advance_form"):
                            st.write("---")
                            st.write("**Advance Configuration**")

                            # Advance percentage
                            advance_pct = st.number_input(
                                "Advance Percentage (%)",
                                min_value=0,
                                max_value=100,
                                value=int(existing_advance.get('Advance_Percentage', 0)) if existing_advance else 0,
                                step=5
                            )

                            # Period selection
                            period_options = ["Project Timeline", "DLP Period", "O&M Period"]
                            selected_period = period_options.index(existing_advance.get('Period', 'Project Timeline')) if existing_advance else 0
                            period = st.radio(
                                "Apply Advance During:",
                                period_options,
                                index=selected_period
                            )

                            # Strategy selection
                            strategy_options = ["First Month Only", "All Months", "Duration Pattern", "Custom Selection"]
                            selected_strategy_idx = 0
                            if existing_advance:
                                strategy_map = {
                                    'first_month': 0,
                                    'all_months': 1,
                                    'duration_pattern': 2,
                                    'custom': 3
                                }
                                selected_strategy_idx = strategy_map.get(existing_advance.get('Application_Strategy', 'first_month'), 0)

                            strategy = st.selectbox(
                                "Advance Application Strategy:",
                                strategy_options,
                                index=selected_strategy_idx
                            )

                            # Conditional fields based on strategy
                            months_to_apply = None

                            if strategy == "Duration Pattern":
                                freq_options = ["Every 2 Months", "Every 3 Months", "Alternate Months (1,3,5...)"]
                                freq_map = {"Every 2 Months": "every_2_months", 
                                           "Every 3 Months": "every_3_months",
                                           "Alternate Months (1,3,5...)": "alternate_months"}

                                # Get existing pattern
                                existing_pattern = None
                                if existing_advance and existing_advance.get('Application_Strategy') == 'duration_pattern':
                                    existing_pattern = existing_advance.get('Months', '')

                                selected_freq = st.selectbox(
                                    "Select Pattern:",
                                    freq_options,
                                    index=0 if not existing_pattern else freq_options.index(next((k for k, v in freq_map.items() if v in existing_pattern), freq_options[0]))
                                )

                                # Calculate months based on period
                                strategy_key = 'duration_pattern'
                                frequency = freq_map[selected_freq]

                                # Determine period for calculation
                                period_key = 'project' if period == 'Project Timeline' else ('dlp' if period == 'DLP Period' else 'oam')

                                # Calculate months (using same pattern as invoice)
                                from advance_utils import calculate_advance_months
                                months_list = calculate_advance_months(period_key, strategy_key, frequency=frequency)
                                months_to_apply = ','.join(months_list) if months_list else ""

                                st.write(f"**Advance Months:** {months_to_apply if months_to_apply else 'No months available'}")

                            elif strategy == "Custom Selection":
                                # Get available months for the period
                                from advance_utils import get_period_months
                                period_key = 'project' if period == 'Project Timeline' else ('dlp' if period == 'DLP Period' else 'oam')
                                available_months = get_period_months(period_key)

                                # Get existing selections
                                existing_selections = []
                                if existing_advance and existing_advance.get('Application_Strategy') == 'custom':
                                    existing_selections = existing_advance.get('Months', '').split(',')

                                selected_months = st.multiselect(
                                    "Select Months:",
                                    available_months,
                                    default=existing_selections if existing_selections else []
                                )

                                months_to_apply = ','.join(selected_months) if selected_months else ""

                            else:
                                # First Month Only or All Months
                                strategy_key = 'first_month' if strategy == "First Month Only" else 'all_months'
                                from advance_utils import calculate_advance_months
                                months_list = calculate_advance_months('project', strategy_key)
                                months_to_apply = ','.join(months_list) if months_list else ""

                            # Notes
                            notes = st.text_area(
                                "Notes (optional)",
                                value=existing_advance.get('Notes', '') if existing_advance else "",
                                height=100
                            )

                            # Submit button
                            if st.form_submit_button("💾 Save Advance Configuration"):
                                # Convert strategy to internal format
                                strategy_map = {
                                    'First Month Only': 'first_month',
                                    'All Months': 'all_months',
                                    'Duration Pattern': 'duration_pattern',
                                    'Custom Selection': 'custom'
                                }

                                strategy_internal = strategy_map[strategy]

                                add_or_update_vendor_advance(
                                    selected_vendor,
                                    selected_bill,
                                    advance_pct,
                                    strategy_internal,
                                    period,
                                    months_to_apply,
                                    notes
                                )

                                st.success(f"✅ Advance configured for {selected_vendor} - {selected_bill}!")
                                st.rerun()

                        # Display existing advances for this vendor/bill
                        st.write("---")
                        st.write("**Configured Advances for This Bill:**")

                        if existing_advance:
                            advance_col1, advance_col2, advance_col3 = st.columns(3)
                            with advance_col1:
                                st.metric("Advance %", f"{existing_advance.get('Advance_Percentage')}%")
                            with advance_col2:
                                st.metric("Strategy", existing_advance.get('Application_Strategy', 'N/A').replace('_', ' ').title())
                            with advance_col3:
                                st.metric("Period", existing_advance.get('Period', 'N/A'))

                            st.write(f"**Months:** {existing_advance.get('Months', 'N/A')}")
                            if existing_advance.get('Notes'):
                                st.write(f"**Notes:** {existing_advance.get('Notes')}")

                            if st.button("🗑️ Delete This Advance", key='delete_vendor_advance_btn'):
                                delete_vendor_advance(selected_vendor, selected_bill)
                                st.success("✅ Advance deleted!")
                                st.rerun()
                        else:
                            st.info("No advance configured for this bill yet.")
                    else:
                        st.info(f"No bills found for {selected_vendor}")

        # ==================== MATCHING PAGE ====================

    with ven_tab2:
        st.info("💡 Multiple activities/sub-activities can be matched to the same bill. The calculations will sum them all together.")

        # Load data
        activities = load_activities()
        vendors = load_vendors()
        current_matches = load_vendor_matches()

        if not activities:
            st.error("❌ No activities found. Please add activities first.")
        elif not vendors:
            st.error("❌ No vendor payments found. Please add vendor payments first.")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["Create Matches", "View by Bill", "View All Matches", "Manage Matches"])

            with tab1:
                st.subheader("Create New Match (Add Multiple Activities to Same Bill)")

                # Get all activities and their sub-activities
                activities_and_subs = get_vendor_activities_and_subs(activities)
                # Get all bills
                bills_list = get_vendor_all_bills(vendors)

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**📋 Select Schedule Item (Left)**")

                    if activities_and_subs:
                        # Create display strings for activities
                        activity_options = []
                        for activity_name, sub_activity in activities_and_subs:
                            if sub_activity:
                                display_text = f"{activity_name} → {sub_activity}"
                            else:
                                display_text = f"{activity_name}"
                            activity_options.append((activity_name, sub_activity, display_text))

                        selected_activity_idx = st.selectbox(
                            "Choose an activity or sub-activity:",
                            range(len(activity_options)),
                            format_func=lambda idx: activity_options[idx][2],
                            key='vendor_activity_select'
                        )

                        selected_activity, selected_sub_activity, _ = activity_options[selected_activity_idx]

                with col2:
                    st.write("**💳 Select Vendor Bill (Right)**")

                    if bills_list:
                        # Create display strings for bills
                        bill_options = []
                        for vendor_name, bill_name, percentage, credit_days in bills_list:
                            display_text = f"{vendor_name} → {bill_name} ({percentage}%, {credit_days}d)"
                            bill_options.append((vendor_name, bill_name, display_text))

                        selected_bill_idx = st.selectbox(
                            "Choose a bill:",
                            range(len(bill_options)),
                            format_func=lambda idx: bill_options[idx][2],
                            key='vendor_bill_select'
                        )

                        selected_vendor, selected_bill, _ = bill_options[selected_bill_idx]

                        # Show current matches for this bill
                        bill_matches = [m for m in current_matches if m.get('Bill') == selected_bill]
                        if bill_matches:
                            st.write("**Already matched activities:**")
                            for match in bill_matches:
                                act_display = f"{match.get('Activity')} → {match.get('Sub-Activity')}" if match.get('Sub-Activity') else match.get('Activity')
                                st.write(f"  • {act_display}")

                st.divider()

                # Link strength and notes
                col1, col2 = st.columns(2)

                with col1:
                    link_strength = st.select_slider(
                        "Link Strength:",
                        options=['Weak', 'Medium', 'Strong'],
                        value='Medium',
                        key='vendor_link_strength'
                    )

                with col2:
                    notes = st.text_input("Notes (optional):", placeholder="Any additional notes about this match", key='vendor_notes')

                # Create button with confirmation
                if st.button("🔗 Create Link", key='vendor_create_link_btn', use_container_width=True):
                    # Check if match already exists
                    existing = get_vendor_matches_by_activity(selected_activity, selected_sub_activity)
                    existing = [m for m in existing if m.get('Bill') == selected_bill]

                    if existing:
                        st.warning(f"⚠️ A match already exists between {selected_activity} (Sub: {selected_sub_activity if selected_sub_activity else 'None'}) and {selected_bill}")
                    else:
                        add_vendor_match(
                            activity=selected_activity,
                            sub_activity=selected_sub_activity,
                            bill=selected_bill,
                            vendor=selected_vendor,
                            link_strength=link_strength,
                            notes=notes
                        )
                        st.success(f"✅ Link created successfully!")
                        st.balloons()
                        st.rerun()

            with tab2:
                st.subheader("Matches by Bill")
                st.write("View all activities/sub-activities matched to each bill")

                if current_matches:
                    # Group matches by bill
                    bills_dict = {}
                    for match in current_matches:
                        bill = match.get('Bill', '')
                        vendor = match.get('Vendor', '')

                        if bill not in bills_dict:
                            bills_dict[bill] = {
                                'vendor': vendor,
                                'activities': []
                            }

                        activity = match.get('Activity', '')
                        sub_activity = match.get('Sub-Activity', '')
                        activity_display = f"{activity} → {sub_activity}" if sub_activity else activity

                        bills_dict[bill]['activities'].append({
                            'display': activity_display,
                            'strength': match.get('Link Strength', 'Medium'),
                            'notes': match.get('Notes', '')
                        })

                    # Display each bill with its activities
                    for bill, data in sorted(bills_dict.items()):
                        vendor = data['vendor']
                        activities_list = data['activities']

                        with st.expander(f"💳 {vendor} → {bill} ({len(activities_list)} activities)", expanded=False):
                            for activity_data in activities_list:
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"📋 {activity_data['display']}")
                                with col2:
                                    strength_color = {'Strong': '🟢', 'Medium': '🟡', 'Weak': '🔴'}.get(activity_data['strength'], '🟡')
                                    st.write(f"{strength_color} {activity_data['strength']}")
                                if activity_data['notes']:
                                    st.caption(f"Note: {activity_data['notes']}")
                else:
                    st.info("No matches created yet.")

            with tab3:
                st.subheader("All Activity-Bill Matches (Table View)")

                if current_matches:
                    # Display matches with visual representation
                    match_df = pd.DataFrame(current_matches)

                    # Reorder columns for better display
                    display_cols = ['Activity', 'Sub-Activity', 'Bill', 'Vendor', 'Link Strength', 'Notes']
                    if 'Last Updated' in match_df.columns:
                        display_cols.append('Last Updated')

                    match_df = match_df[display_cols]

                    # Color code the link strength
                    def color_strength(val):
                        colors = {
                            'Strong': '#90EE90',
                            'Medium': '#FFD700',
                            'Weak': '#FFB6C6'
                        }
                        color = colors.get(val, 'white')
                        return f'background-color: {color}'

                    # Apply styling
                    styled_df = match_df.style.map(color_strength, subset=['Link Strength'])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)

                    # Download as CSV
                    csv_data = match_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv_data,
                        file_name="activity_vendor_bill_matching.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No matches to display.")

            with tab4:
                st.subheader("Manage Matches")

                if current_matches:
                    # Select a match to delete
                    match_options = []
                    for match in current_matches:
                        activity = match.get('Activity', '')
                        sub_activity = match.get('Sub-Activity', '')
                        bill = match.get('Bill', '')
                        vendor = match.get('Vendor', '')

                        activity_display = f"{activity} → {sub_activity}" if sub_activity else activity
                        display_text = f"{activity_display} → {vendor} ({bill})"

                        match_options.append((activity, sub_activity, bill, vendor, display_text))

                    selected_match_idx = st.selectbox(
                        "Select a match to delete:",
                        range(len(match_options)),
                        format_func=lambda idx: match_options[idx][4],
                        key='vendor_match_select'
                    )

                    if selected_match_idx is not None:
                        selected_activity, selected_sub_activity, selected_bill, selected_vendor, _ = match_options[selected_match_idx]
                        selected_match = current_matches[selected_match_idx]

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Match Details:**")
                            st.write(f"Activity: {selected_activity}")
                            st.write(f"Sub-Activity: {selected_sub_activity if selected_sub_activity else 'None'}")
                            st.write(f"Vendor: {selected_vendor}")
                            st.write(f"Bill: {selected_bill}")
                            st.write(f"Link Strength: {selected_match.get('Link Strength', 'N/A')}")

                        with col2:
                            if st.button("🗑️ Delete This Match", key='vendor_delete_match_btn', use_container_width=True):
                                delete_vendor_match(selected_activity, selected_sub_activity, selected_bill, selected_vendor)
                                st.success("✅ Match deleted successfully!")
                                st.rerun()
                else:
                    st.info("No matches to manage yet.")

        # ==================== VENDOR PAYMENT REPORT PAGE ====================

    with ven_tab3:

        # Check if we have data
        activities = load_activities()
        vendors = load_vendors()
        vendor_matches = load_vendor_matches()

        if not activities:
            st.error("❌ No activities found. Please add activities first.")
        elif not vendors:
            st.error("❌ No vendor payments found. Please add vendor payments first.")
        elif not vendor_matches:
            st.error("❌ No vendor payment matches found. Please create matches in 'Vendor Payment Matching' page.")
        else:
            calc_months = get_calculation_months()

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                ["By Bill", "By Vendor", "By Activity", "Totals", "Advances", "Export"]
            )

            # Calculate all data
            vendor_df = calculate_vendor_payment_table()
            vendor_by_vendor_df = calculate_vendor_by_vendor()
            vendor_activity_df = calculate_vendor_by_activity()
            summary_totals = calculate_vendor_summary_totals()
            advance_df = calculate_vendor_advance_table()
            advance_vendor_df = calculate_vendor_advance_by_vendor()
            net_vendor_df = calculate_net_vendor_payment_table()
            net_vendor_by_vendor_df = calculate_net_vendor_by_vendor()

            net_summary_totals = {}
            for _m in calc_months:
                # Recompute net_summary_totals properly ignoring special rows
                if not net_vendor_df.empty and _m in net_vendor_df.columns:
                    data_rows = net_vendor_df[~net_vendor_df['Bill'].isin(['TOTAL', 'CUMULATIVE'])]
                    net_summary_totals[_m] = float(data_rows[_m].sum())
                else:
                    net_summary_totals[_m] = 0.0

            # ── Vendor / Bill Filter ─────────────────────────────────
            st.markdown("---")
            st.markdown("#### 🔍 Filter Charts & Tables by Vendor")
            col_filter1, col_filter2 = st.columns(2)

            from vendor_payment_utils import load_vendors
            vendors_list = load_vendors()
            all_vendors_names = [v.get('Vendor', '') for v in vendors_list if v.get('Vendor')]

            with col_filter1:
                selected_vendors_filter = st.multiselect(
                    "Filter by Vendor (leave blank = show all)",
                    options=all_vendors_names,
                    default=[],
                    key='vendor_filter',
                    help="Select one or more vendors to focus the tables and charts on those vendors only."
                )

            # Derive available bills from selected vendors
            available_bills = []
            if selected_vendors_filter:
                matches = load_vendor_matches()
                for match in matches:
                    v = match.get('Vendor', '')
                    b = match.get('Bill', '')
                    if v in selected_vendors_filter and b:
                        bill_key = f"{v} > {b}"
                        if bill_key not in available_bills:
                            available_bills.append(bill_key)

            with col_filter2:
                selected_bills_filter = st.multiselect(
                    "Filter by Bill (optional, refines Vendor selection)",
                    options=available_bills,
                    default=[],
                    key='bill_filter',
                    help="Optionally narrow down to specific bills within the selected vendors."
                )

            if selected_vendors_filter or selected_bills_filter:
                filter_label = ", ".join(selected_bills_filter or selected_vendors_filter)
                st.info(f"📌 Showing data for: **{filter_label}**")
            st.markdown("---")

            # ── Apply Filters ────────────────────────────────────────────────────
            def _filter_df(df, col_name, sel_parents, sel_children):
                if df.empty or (not sel_parents and not sel_children):
                    return df
                if col_name not in df.columns:
                    return df
                special_mask = df[col_name].isin(['TOTAL', 'CUMULATIVE'])
                data_rows = df[~special_mask].copy()
                if sel_children:
                    data_rows = data_rows[data_rows[col_name].isin(sel_children)]
                elif sel_parents:
                    data_rows = data_rows[data_rows[col_name].apply(
                        lambda x: any(str(x).startswith(p + ' >') or str(x) == p for p in sel_parents)
                    )]
                return data_rows

            if selected_vendors_filter or selected_bills_filter:
                vendor_df = _filter_df(vendor_df, 'Bill', selected_vendors_filter, selected_bills_filter)
                net_vendor_df = _filter_df(net_vendor_df, 'Bill', selected_vendors_filter, selected_bills_filter)
                advance_df = _filter_df(advance_df, 'Bill', selected_vendors_filter, selected_bills_filter)
                vendor_by_vendor_df = _filter_df(vendor_by_vendor_df, 'Vendor', selected_vendors_filter, [])
                net_vendor_by_vendor_df = _filter_df(net_vendor_by_vendor_df, 'Vendor', selected_vendors_filter, [])
                advance_vendor_df = _filter_df(advance_vendor_df, 'Vendor', selected_vendors_filter, [])
                # Recalculate summary totals from filtered data
                summary_totals = {}
                net_summary_totals = {}
                for _m in calc_months:
                    summary_totals[_m] = float(vendor_df[_m].sum()) if (not vendor_df.empty and _m in vendor_df.columns) else 0.0
                    net_summary_totals[_m] = float(net_vendor_df[_m].sum()) if (not net_vendor_df.empty and _m in net_vendor_df.columns) else 0.0

            with tab1:
                st.subheader("Detailed Bill Breakdown")

                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Original payment value** (before deducting advances)")
                    if not vendor_df.empty:
                        unformatted_df = vendor_df.copy()
                        display_df = vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Original Vendor Payments - By Bill", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.warning("⚠️ No calculations available.")

                with sub_tab2:
                    st.write("**Advance amounts** (deducted from original)")
                    if not advance_df.empty:
                        unformatted_df = advance_df.copy()
                        display_df = advance_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        display_table_with_hover_tooltips(display_df, "Advance Payments - By Bill", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.info("ℹ️ No advance payments configured.")

                with sub_tab3:
                    st.write("**Net payment value** (Original - Advances)")
                    if not net_vendor_df.empty:
                        unformatted_df = net_vendor_df.copy()
                        display_df = net_vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Net Vendor Payments - By Bill", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.warning("⚠️ No calculations available.")

            with tab2:
                st.subheader("Total by Vendor")

                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Original payment value** (before deducting advances)")
                    if not vendor_by_vendor_df.empty:
                        unformatted_df = vendor_by_vendor_df.copy()
                        display_df = vendor_by_vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Original Vendor Payments - By Vendor", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.warning("⚠️ No calculations available.")

                with sub_tab2:
                    st.write("**Total advance amounts** by vendor")
                    if not advance_vendor_df.empty:
                        unformatted_df = advance_vendor_df.copy()
                        display_df = advance_vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")

                        display_table_with_hover_tooltips(display_df, "Advance Payments - By Vendor", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.info("ℹ️ No advance payments configured.")

                with sub_tab3:
                    st.write("**Net payment value** (Original - Advances)")
                    if not net_vendor_by_vendor_df.empty:
                        unformatted_df = net_vendor_by_vendor_df.copy()
                        display_df = net_vendor_by_vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                        display_table_with_hover_tooltips(display_df, "Net Vendor Payments - By Vendor", unformatted_df=unformatted_df, table_type="vendor")
                    else:
                        st.warning("⚠️ No calculations available.")

            with tab3:
                st.subheader("Total by Activity")
                st.write("Aggregated values for each activity/sub-activity across all months.")

                if not vendor_activity_df.empty:
                    unformatted_df = vendor_activity_df.copy()
                    display_df = vendor_activity_df.copy()
                    for month in calc_months:
                        if month in display_df.columns:
                            display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                            display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}")

                    display_table_with_hover_tooltips(display_df, "Total Vendor Payments by Activity", unformatted_df=unformatted_df, table_type="vendor")
                else:
                    st.warning("⚠️ No calculations available.")

            with tab4:
                st.subheader("Monthly Totals")

                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Original Amount", "Less: Advances", "Net Amount (After Advances)"])

                with sub_tab1:
                    st.write("**Total original payment amount** for each month across all vendors")
                    totals_data = [{'Month': month, 'Total Payment Amount': f"${summary_totals.get(month, 0):,.2f}"} for month in calc_months]
                    totals_df = pd.DataFrame(totals_data)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(totals_df, use_container_width=True, hide_index=True)
                    with col2:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[summary_totals.get(month, 0) for month in calc_months],
                            marker=dict(colorscale='Viridis', color=[summary_totals.get(month, 0) for month in calc_months]),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>', opacity=0.85
                        ))
                        fig.update_layout(title='Monthly Original Totals', yaxis=dict(title='Amount ($)', tickformat='$,.0f'))
                        st.plotly_chart(fig, use_container_width=True)
                        st.metric("Grand Total (All Months)", f"${sum(summary_totals.values()):,.2f}")

                with sub_tab2:
                    st.write("**Total advance payments** for each month across all vendors")
                    advance_totals = {month: 0 for month in calc_months}
                    if not advance_df.empty:
                        for _, row in advance_df.iterrows():
                            if row.get('Bill') in ['TOTAL', 'CUMULATIVE']:
                                continue
                            for month in calc_months:
                                if month in row.index:
                                    advance_totals[month] += float(row[month]) if pd.notna(row[month]) else 0

                    advance_totals_data = [{'Month': month, 'Total Advance Amount': f"${advance_totals.get(month, 0):,.2f}"} for month in calc_months]
                    advance_totals_df = pd.DataFrame(advance_totals_data)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(advance_totals_df, use_container_width=True, hide_index=True)
                    with col2:
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[advance_totals.get(month, 0) for month in calc_months],
                            marker=dict(colorscale='Plasma', color=[advance_totals.get(month, 0) for month in calc_months]),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>', opacity=0.85
                        ))
                        fig.update_layout(title='Monthly Advance Totals', yaxis=dict(title='Amount ($)', tickformat='$,.0f'))
                        st.plotly_chart(fig, use_container_width=True)
                        st.metric("Grand Total Advances (All Months)", f"${sum(advance_totals.values()):,.2f}")

                with sub_tab3:
                    st.write("**Net payment amount** (Original - Advances) for each month across all vendors")
                    net_totals_data = [{'Month': month, 'Net Payment Amount': f"${net_summary_totals.get(month, 0):,.2f}"} for month in calc_months]
                    net_totals_df = pd.DataFrame(net_totals_data)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(net_totals_df, use_container_width=True, hide_index=True)
                    with col2:
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[m.split()[0][:3] + "'" + m.split()[1][-2:] if len(m.split()) > 1 else m[:3] for m in calc_months],
                            y=[net_summary_totals.get(month, 0) for month in calc_months],
                            marker=dict(colorscale='Greens', color=[net_summary_totals.get(month, 0) for month in calc_months]),
                            hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.2f}<extra></extra>', opacity=0.85
                        ))
                        fig.update_layout(title='Monthly Net Payment Totals', yaxis=dict(title='Amount ($)', tickformat='$,.0f'))
                        st.plotly_chart(fig, use_container_width=True)
                        st.metric("Grand Total Net (All Months)", f"${sum(net_summary_totals.values()):,.2f}")

            with tab5:
                st.subheader("Advance Payments Breakdown")
                st.write("Advance payment amounts calculated for each bill by month.")
                if advance_df.empty:
                    st.info("ℹ️ No advance payments configured.")
                else:
                    st.write("**By Bill:**")
                    display_df = advance_df.copy()
                    for month in calc_months:
                        if month in display_df.columns:
                            display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                            display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    st.write("**Total by Vendor:**")
                    if not advance_vendor_df.empty:
                        display_df = advance_vendor_df.copy()
                        for month in calc_months:
                            if month in display_df.columns:
                                display_df[month] = pd.to_numeric(display_df[month], errors='coerce').fillna(0)
                                display_df[month] = display_df[month].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
                        st.dataframe(display_df, use_container_width=True, hide_index=True)

            with tab6:
                st.subheader("Export Data")
                st.write("Download calculated vendor payment data as CSV.")

                col1, col2 = st.columns(2)
                with col1:
                    if not vendor_df.empty: st.download_button("📥 Original Payments by Bill", data=vendor_df.to_csv(index=False), file_name="vendor_payments_original.csv", mime="text/csv")
                    if not advance_df.empty: st.download_button("📥 Advances by Bill", data=advance_df.to_csv(index=False), file_name="vendor_advances.csv", mime="text/csv")
                    if not net_vendor_df.empty: st.download_button("📥 Net Payments by Bill", data=net_vendor_df.to_csv(index=False), file_name="vendor_net_payments.csv", mime="text/csv")
                with col2:
                    if not vendor_by_vendor_df.empty: st.download_button("📥 Original Payments by Vendor", data=vendor_by_vendor_df.to_csv(index=False), file_name="vendor_payments_by_vendor.csv", mime="text/csv")
                    if not vendor_activity_df.empty: st.download_button("📥 Payments by Activity", data=vendor_activity_df.to_csv(index=False), file_name="vendor_payments_by_activity.csv", mime="text/csv")

            _old_ui = '''
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["Vendor Bills", "By Vendor", "Summary", "Payment Advances", "Net Payments"])

            with tab1:
                st.subheader("💳 Vendor Payment by Bill (Monthly Breakdown)")
                st.info("💡 Formula: (Bill % / 100) × (Activity % / 100) × Activity Cost. Credit days shift payments forward.")

                try:
                    vendor_table = calculate_vendor_payment_table()

                    if vendor_table.empty:
                        st.warning("⚠️ No data available. Ensure all activities have costs assigned and matches are created.")
                    else:
                        # Clean the table - replace None with 0 for numeric columns
                        for col in vendor_table.columns:
                            if col not in ['Bill']:
                                vendor_table[col] = pd.to_numeric(vendor_table[col], errors='coerce').fillna(0)

                        # Display the table with formatting
                        def format_func(val):
                            if pd.isna(val) or val is None:
                                return ''
                            try:
                                return f'{val:,.2f}'
                            except:
                                return str(val)

                        display_table = vendor_table.copy()
                        for col in display_table.columns:
                            if col not in ['Bill']:
                                display_table[col] = display_table[col].apply(format_func)

                        st.dataframe(display_table,
                                    use_container_width=True,
                                    hide_index=True)

                        # Show calculation details in expandable section
                        with st.expander("📖 View Calculation Details"):
                            st.write("**Hover over cells to see calculation formulas:**")
                            st.write("""
                            ### Calculation Breakdown:

                            For each **Bill** and **Month**:

                            1. **Sum all linked activities:** 
                               - For each activity/sub-activity linked to this bill:
                               - Value = (Activity Monthly % ÷ 100) × Activity Cost

                            2. **Apply bill percentage:**
                               - Month Value = (Bill % ÷ 100) × Sum of all activities

                            3. **Apply credit days shift** (if configured):
                               - Payments shift forward by estimated months (~30 days = 1 month)
                               - Example: If bill has 15 credit days, January payment appears in February

                            ### Row Totals:
                            - **Row Total:** Sum of all months for each bill
                            - **TOTAL:** Sum of all bills for each month
                            - **CUMULATIVE:** Running total across all months
                            """)

                            st.divider()
                            st.write("**Example Calculation:**")
                            st.write("""
                            If Activity "Design" is linked to Bill "Labor" (50%):
                            - Activity is 40% in January with $1,000 cost
                            - Bill has 0 credit days
                            - **Calculation:** (50/100) × (40/100) × $1,000 = $200
                            """)

                        # Download as CSV
                        csv_data = vendor_table.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="vendor_payment_by_bill.csv",
                            mime="text/csv",
                            key='vendor_bill_csv'
                        )
                except Exception as e:
                    st.error(f"❌ Error calculating vendor payments: {str(e)}")

            with tab2:
                st.subheader("💳 Vendor Payment by Vendor (Aggregated)")

                try:
                    vendor_by_vendor = calculate_vendor_by_vendor()

                    if vendor_by_vendor.empty:
                        st.warning("⚠️ No data available.")
                    else:
                        # Clean the table - replace None with 0 for numeric columns
                        for col in vendor_by_vendor.columns:
                            if col not in ['Vendor']:
                                vendor_by_vendor[col] = pd.to_numeric(vendor_by_vendor[col], errors='coerce').fillna(0)

                        # Display the table with formatting
                        def format_func(val):
                            if pd.isna(val) or val is None:
                                return ''
                            try:
                                return f'{val:,.2f}'
                            except:
                                return str(val)

                        display_table = vendor_by_vendor.copy()
                        for col in display_table.columns:
                            if col not in ['Vendor']:
                                display_table[col] = display_table[col].apply(format_func)

                        st.dataframe(display_table,
                                    use_container_width=True,
                                    hide_index=True)

                        # Show calculation details in expandable section
                        with st.expander("📖 View Calculation Details"):
                            st.write("**How Vendor Aggregation Works:**")
                            st.write("""
                            Each vendor's total is calculated by **summing all of their bills** for each month:

                            - **Vendor Total (Month) = Bill 1 (Month) + Bill 2 (Month) + ... + Bill N (Month)**

                            Each bill is calculated using the formula:
                            - **(Bill % ÷ 100) × SUM of linked activities**
                            """)


                        # Download as CSV
                        csv_data = vendor_by_vendor.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="vendor_payment_by_vendor.csv",
                            mime="text/csv",
                            key='vendor_vendor_csv'
                        )
                except Exception as e:
                    st.error(f"❌ Error calculating vendor totals: {str(e)}")

            with tab3:
                st.subheader("📊 Summary Statistics")

                try:
                    totals = calculate_vendor_summary_totals()

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        total_amount = sum(totals.values())
                        st.metric("Total Vendor Payments", f"${total_amount:,.2f}")

                    with col2:
                        avg_monthly = total_amount / len([v for v in totals.values() if v > 0]) if any(totals.values()) else 0
                        st.metric("Average Monthly", f"${avg_monthly:,.2f}")

                    with col3:
                        max_month = max(totals.items(), key=lambda x: x[1]) if totals else ('N/A', 0)
                        st.metric("Peak Month", f"${max_month[1]:,.2f} ({max_month[0]})")

                    # Monthly breakdown
                    st.write("---")
                    st.write("**Monthly Payment Totals:**")

                    monthly_data = []
                    for month in MONTHS:
                        if month in totals:
                            monthly_data.append({
                                'Month': month,
                                'Total': totals[month]
                            })

                    if monthly_data:
                        df_monthly = pd.DataFrame(monthly_data)

                        # Display with formatting and explanation
                        def format_func(val):
                            if pd.isna(val) or val is None:
                                return ''
                            try:
                                return f'${val:,.2f}'
                            except:
                                return str(val)

                        display_monthly = df_monthly.copy()
                        display_monthly['Total'] = display_monthly['Total'].apply(format_func)

                        st.dataframe(display_monthly,
                                    use_container_width=True,
                                    hide_index=True)

                        # Chart
                        st.line_chart(df_monthly.set_index('Month')['Total'])

                        # Show calculation details in expandable section
                        with st.expander("📖 View Calculation Details"):
                            st.write("**Summary Statistics Calculations:**")
                            st.write(f"""
                            - **Total Vendor Payments:** Sum of all monthly totals across all vendors
                              - = {' + '.join([f'${v:,.2f}' for v in totals.values() if v > 0])}
                              - = **${total_amount:,.2f}**

                            - **Average Monthly:** Total divided by number of active months
                              - = ${total_amount:,.2f} ÷ {len([v for v in totals.values() if v > 0])} months
                              - = **${avg_monthly:,.2f}**

                            - **Peak Month:** The month with the highest total payments
                              - = **{max_month[0]} with ${max_month[1]:,.2f}**
                            """)
                    else:
                        st.info("No monthly totals available.")
                except Exception as e:
                    st.error(f"❌ Error calculating summary: {str(e)}")

            with tab4:
                st.subheader("💰 Vendor Payment Advances (Monthly Breakdown)")
                st.info("💡 Advances are applied to selected months based on your configuration. Formula: (Advance % / 100) × Bill Payment Amount")

                try:
                    advance_table = calculate_vendor_advance_table()

                    if advance_table.empty:
                        st.info("ℹ️ No payment advances configured. Configure advances in the 'Vendor Payment > Payment Advances' tab.")
                    else:
                        # Clean the table - replace None with 0 for numeric columns
                        for col in advance_table.columns:
                            if col not in ['Bill']:
                                advance_table[col] = pd.to_numeric(advance_table[col], errors='coerce').fillna(0)

                        # Display the table with formatting
                        def format_func(val):
                            if pd.isna(val) or val is None:
                                return ''
                            try:
                                return f'{val:,.2f}'
                            except:
                                return str(val)

                        display_table = advance_table.copy()
                        for col in display_table.columns:
                            if col not in ['Bill']:
                                display_table[col] = display_table[col].apply(format_func)

                        st.dataframe(display_table,
                                    use_container_width=True,
                                    hide_index=True)

                        # Show calculation details
                        with st.expander("📖 View Calculation Details"):
                            st.write("""
                            ### Advance Payment Calculation:

                            For each **Bill** and **Month** where advance is applied:

                            1. **Get configured advance percentage** for this bill
                            2. **Get the vendor payment amount** for this bill in this month
                            3. **Calculate advance:**
                               - Advance Amount = (Advance % ÷ 100) × Bill Payment Amount

                            ### Key Points:
                            - Advances are only calculated in configured months
                            - Multiple advance strategies available:
                              - **First Month Only:** Apply advance only in the first month
                              - **All Months:** Apply advance in every month of the period
                              - **Duration Pattern:** Apply advance every 2/3 months or alternate months
                              - **Custom Selection:** Choose specific months for the advance

                            ### Row Totals:
                            - **Row Total:** Sum of all advance months for each bill
                            - **TOTAL:** Sum of all bills for each month
                            - **CUMULATIVE:** Running total of advances across all months
                            """)

                        # Download as CSV
                        csv_data = advance_table.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="vendor_payment_advances.csv",
                            mime="text/csv",
                            key='vendor_advance_csv'
                        )
                except Exception as e:
                    st.error(f"❌ Error calculating vendor advances: {str(e)}")

            with tab5:
                st.subheader("💳 Net Vendor Payments (After Advances)")
                st.info("💡 Formula: Net Payment = Total Bill Payment - Advance Payment. Shows actual payments owed to vendors.")

                try:
                    net_table = calculate_net_vendor_payment_table()

                    if net_table.empty:
                        st.warning("⚠️ No data available.")
                    else:
                        # Clean the table - replace None with 0 for numeric columns
                        for col in net_table.columns:
                            if col not in ['Bill']:
                                net_table[col] = pd.to_numeric(net_table[col], errors='coerce').fillna(0)

                        # Display the table with formatting
                        def format_func(val):
                            if pd.isna(val) or val is None:
                                return ''
                            try:
                                return f'{val:,.2f}'
                            except:
                                return str(val)

                        display_table = net_table.copy()
                        for col in display_table.columns:
                            if col not in ['Bill']:
                                display_table[col] = display_table[col].apply(format_func)

                        st.dataframe(display_table,
                                    use_container_width=True,
                                    hide_index=True)

                        # Show calculation details
                        with st.expander("📖 View Calculation Details"):
                            st.write("""
                            ### Net Payment Calculation:

                            For each **Bill** and **Month**:

                            **Net Payment = Total Vendor Payment - Advance Payment**

                            ### Example:
                            - If total vendor payment for "Vendor A > Bill 1" in January is $1,000
                            - And advance of 30% is configured and applied in January
                            - Advance amount = (30/100) × $1,000 = $300
                            - Net payment = $1,000 - $300 = $700

                            ### Interpretation:
                            - Positive values: Net payment owed to vendor
                            - Zero or negative: No payment owed (advance already covered)
                            - **TOTAL Row:** Sum of all net bill payments by month
                            - **CUMULATIVE Row:** Running total of net payments across project
                            """)

                        # Download as CSV
                        csv_data = net_table.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_data,
                            file_name="net_vendor_payments.csv",
                            mime="text/csv",
                            key='net_vendor_csv'
                        )
                except Exception as e:
                    st.error(f"❌ Error calculating net vendor payments: {str(e)}")
            '''

        # ==================== INVOICING REPORT PAGE ====================

# ==================== CASH FLOW CURVE PAGE ====================
elif st.session_state.page == '📈 Cash Flow Curve':
    st.markdown("### 💰 Project Cash Flow Analysis")
    
    st.info("""
    This cash flow curve visualization shows:
    - **Blue Line**: Cumulative Cash Inflow (Invoicing / Collections)
    - **Red Line**: Cumulative Cash Outflow (Vendor Payments)
    - **Green Bars**: Net Cashflow (Inflow − Outflow) — Green = cash surplus, Red = cash deficit
    - **Annotation**: Peak cash exposure (maximum deficit point)
    """)
    
    # Check if we have data
    activities = load_activities()
    invoices = load_invoices()
    matches = load_matches()
    vendors = load_vendors()
    vendor_matches = load_vendor_matches()
    
    if not activities:
        st.error("❌ No activities found. Please add activities first.")
    elif not invoices or not matches:
        st.error("❌ No invoice data found. Please set up invoicing first (Invoicing Report).")
    elif not vendors or not vendor_matches:
        st.error("❌ No vendor payment data found. Please set up vendor payments first (Vendor Payment Report).")
    else:
        tab1, tab2 = st.tabs(["Overall Project Cash Flow", "Nuanced Analysis (Custom Subgraphs)"])
        
        with tab1:
            # Create two columns - one for chart controls, one for the chart
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.subheader("Chart Options")
                
                # Get data for display
                months_inflow, inflow_values = get_cumulative_invoicing()
                months_outflow, outflow_values = get_cumulative_vendor_payment()
                net_values = calculate_net_cashflow(inflow_values, outflow_values)
                
                # Find peak negative value
                negative_values = [v for v in net_values if v < 0]
                peak_negative = min(negative_values) if negative_values else 0
                
                # Display key metrics
                st.write("**Key Metrics:**")
                
                total_inflow = inflow_values[-1] if inflow_values else 0
                total_outflow = outflow_values[-1] if outflow_values else 0
                net_cf = total_inflow - total_outflow
                
                st.metric("Total Cash Inflow", f"${total_inflow:,.2f}")
                st.metric("Total Cash Outflow", f"${total_outflow:,.2f}")
                
                if net_cf >= 0:
                    st.metric("Net Cashflow", f"${net_cf:,.2f}", delta="Cash Surplus", delta_color="normal")
                else:
                    st.metric("Net Cashflow", f"${net_cf:,.2f}", delta="Cash Deficit", delta_color="inverse")
                
                if negative_values:
                    st.metric("Peak -Ve Cashflow", f"${abs(peak_negative):,.2f} Cr")
                    
                    # Find the month with peak negative value
                    peak_month_idx = net_values.index(peak_negative)
                    if peak_month_idx < len(months_inflow):
                        st.caption(f"**Month:** {months_inflow[peak_month_idx]}")
                
                # Download button
                st.divider()
                if st.button("💾 Save Chart as PNG", use_container_width=True):
                    try:
                        import tempfile
                        import os
                        
                        # Create temp file
                        temp_dir = tempfile.gettempdir()
                        output_path = os.path.join(temp_dir, 'cashflow_curve.png')
                        
                        # Create the chart
                        fig = create_cashflow_curve()
                        
                        # Save it
                        fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
                        
                        # Read and provide download
                        with open(output_path, 'rb') as f:
                            img_data = f.read()
                        
                        st.download_button(
                            label="📥 Download PNG Image",
                            data=img_data,
                            file_name="Project_Cashflow_Curve.png",
                            mime="image/png",
                            key='download_cashflow_png'
                        )
                        
                        st.success("✅ Chart saved successfully!")
                        
                        # Clean up
                        os.remove(output_path)
                        
                    except Exception as e:
                        st.error(f"❌ Error saving chart: {str(e)}")
            
            with col2:
                st.subheader("Cash Flow Curve")
                
                try:
                    # Create and display the chart
                    fig = create_cashflow_curve()
                    st.pyplot(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error creating cash flow curve: {str(e)}")
                    st.write("Debug info:")
                    st.write(f"Inflow months: {len(months_inflow)}")
                    st.write(f"Outflow months: {len(months_outflow)}")
                    st.write(f"Inflow values: {len(inflow_values)}")
                    st.write(f"Outflow values: {len(outflow_values)}")
            
        with tab2:
            st.info("💡 Nuanced Analysis lets you select specific Invoice Milestones and Vendor Bills to compare their localized cash flows against each other.")
            
            filter_col1, filter_col2 = st.columns(2)
            
            # Extract unique milestones
            unique_milestones = sorted(list(set([inv.get('Milestone', '') for inv in invoices if inv.get('Milestone', '')])))
            # Extract unique vendors
            unique_vendors = sorted(list(set([v.get('Vendor', '') for v in vendors if v.get('Vendor', '')])))
            
            with filter_col1:
                selected_milestones = st.multiselect("Select Invoice Milestones:", options=unique_milestones, default=unique_milestones[:1] if unique_milestones else None)
            
            with filter_col2:
                selected_vendors = st.multiselect("Select Vendors:", options=unique_vendors, default=unique_vendors[:1] if unique_vendors else None)
                
            if not selected_milestones and not selected_vendors:
                st.warning("Please select at least one Milestone or Vendor to view the customized subgraph.")
            else:
                sub_col1, sub_col2 = st.columns([1, 3])
                
                with sub_col1:
                    st.subheader("Subgraph Options")
                    
                    # Get custom data for display
                    months_inflow, inflow_values = get_custom_cumulative_invoicing(selected_milestones)
                    months_outflow, outflow_values = get_custom_cumulative_vendor_payment(selected_vendors)
                    
                    # Ensure matching length
                    if len(months_inflow) >= len(months_outflow):
                        custom_months = months_inflow
                        while len(outflow_values) < len(custom_months): outflow_values.append(outflow_values[-1] if outflow_values else 0)
                    else:
                        custom_months = months_outflow
                        while len(inflow_values) < len(custom_months): inflow_values.append(inflow_values[-1] if inflow_values else 0)
                    
                    net_values = calculate_net_cashflow(inflow_values, outflow_values)
                    
                    # Find peak negative value
                    negative_values = [v for v in net_values if v < 0]
                    peak_negative = min(negative_values) if negative_values else 0
                    
                    # Display key metrics
                    st.write("**Nuanced Metrics:**")
                    
                    total_inflow = inflow_values[-1] if inflow_values else 0
                    total_outflow = outflow_values[-1] if outflow_values else 0
                    net_cf = total_inflow - total_outflow
                    
                    st.metric("Subgraph Inflow", f"${total_inflow:,.2f}")
                    st.metric("Subgraph Outflow", f"${total_outflow:,.2f}")
                    
                    if net_cf >= 0:
                        st.metric("Subgraph Net", f"${net_cf:,.2f}", delta="Surplus", delta_color="normal")
                    else:
                        st.metric("Subgraph Net", f"${net_cf:,.2f}", delta="Deficit", delta_color="inverse")
                    
                    if negative_values:
                        st.metric("Peak -Ve", f"${abs(peak_negative):,.2f}")
                        
                        peak_month_idx = net_values.index(peak_negative)
                        if peak_month_idx < len(custom_months):
                            st.caption(f"**Month:** {custom_months[peak_month_idx]}")
                            
                    st.divider()
                    if st.button("💾 Save Subgraph as PNG", use_container_width=True, key="btn_save_subgraph"):
                        try:
                            import tempfile
                            import os
                            
                            temp_dir = tempfile.gettempdir()
                            output_path = os.path.join(temp_dir, 'subgraph_cashflow_curve.png')
                            
                            fig = create_cashflow_curve(custom_months=custom_months, custom_inflow=inflow_values, custom_outflow=outflow_values, custom_net=net_values)
                            fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
                            
                            with open(output_path, 'rb') as f:
                                img_data = f.read()
                            
                            st.download_button(
                                label="📥 Download PNG",
                                data=img_data,
                                file_name="Nuanced_Analysis_Curve.png",
                                mime="image/png",
                                key='download_subgraph_png'
                            )
                        except Exception as e:
                            st.error(f"❌ Error saving chart: {str(e)}")
                            
                with sub_col2:
                    st.subheader("Nuanced Cash Flow Curve")
                    try:
                        fig = create_cashflow_curve(custom_months=custom_months, custom_inflow=inflow_values, custom_outflow=outflow_values, custom_net=net_values)
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Error creating custom cash flow curve: {str(e)}")

        # Display detailed data table below
        st.divider()
        st.subheader("Detailed Monthly Data")
        
        # Create detailed data table
        months_list = months_inflow if len(months_inflow) >= len(months_outflow) else months_outflow
        
        # Pad arrays if needed
        inflow_padded = inflow_values + [inflow_values[-1] if inflow_values else 0] * (len(months_list) - len(inflow_values))
        outflow_padded = outflow_values + [outflow_values[-1] if outflow_values else 0] * (len(months_list) - len(outflow_values))
        net_padded = calculate_net_cashflow(inflow_padded, outflow_padded)
        
        # Create DataFrame
        detailed_data = {
            'Month': months_list,
            'Cash Inflow': inflow_padded,
            'Cash Outflow': outflow_padded,
            'Net Cashflow': net_padded
        }
        
        df_detail = pd.DataFrame(detailed_data)
        
        # Format for display
        df_display = df_detail.copy()
        df_display['Cash Inflow'] = df_display['Cash Inflow'].apply(lambda x: f"${x:,.2f}")
        df_display['Cash Outflow'] = df_display['Cash Outflow'].apply(lambda x: f"${x:,.2f}")
        df_display['Net Cashflow'] = df_display['Net Cashflow'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Download detailed data as CSV
        csv_data = df_detail.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_data,
            file_name="cashflow_data.csv",
            mime="text/csv"
        )
