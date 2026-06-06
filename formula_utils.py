"""
Formula tracking and display utilities for interactive tables with hover tooltips.
Stores calculation formulas for each cell to display on hover in AgGrid tables.
"""

import pandas as pd
from typing import Dict, List, Tuple, Any
from calculation_utils import get_calculation_months


def create_formula_dict_for_invoicing(invoicing_data: Dict[str, Any]) -> Dict[Tuple[str, str], str]:
    """
    Create formula descriptions for invoicing calculations.
    
    Args:
        invoicing_data: Dictionary with calculation metadata
        
    Returns:
        Dictionary mapping (row_name, month) tuples to formula strings
    """
    formulas = {}
    
    # Example formulas for documentation
    # Formula structure: (Sub-Milestone, Month) -> "Formula description"
    
    return formulas


def add_tooltips_to_dataframe(df: pd.DataFrame, formula_dict: Dict[Tuple[str, str], str] = None) -> pd.DataFrame:
    """
    Add formula tooltip column to a dataframe.
    Stores formula information that can be displayed on hover.
    
    Args:
        df: Original dataframe with data
        formula_dict: Dictionary mapping (row_value, column) to formula string
        
    Returns:
        DataFrame with added tooltip column
    """
    if df.empty:
        return df
    
    result_df = df.copy()
    
    # Add a hidden column that stores tooltip information
    # This will be used by AgGrid to display on hover
    tooltips = []
    
    calc_months = get_calculation_months()
    row_label_col = None
    
    # Find the first non-month column as the row identifier
    for col in result_df.columns:
        if col not in calc_months and col != 'Row Total':
            row_label_col = col
            break
    
    # Generate tooltip for each row
    for idx, row in result_df.iterrows():
        row_label = row[row_label_col] if row_label_col and row_label_col in row.index else f"Row {idx}"
        
        # Create tooltip text with monthly formulas
        tooltip_lines = [f"Row: {row_label}"]
        
        for month in calc_months:
            if month in row.index:
                value = row[month]
                tooltip_lines.append(f"{month}: ${value:,.2f}")
        
        tooltip_text = " | ".join(tooltip_lines)
        tooltips.append(tooltip_text)
    
    # Store tooltips in a hidden column (will be used by AgGrid)
    result_df.insert(0, '_tooltip', tooltips)
    
    return result_df


def build_invoicing_formula_text(sub_milestone: str, month: str, 
                                 linked_activities: List[Tuple[str, str, float, float]], 
                                 sub_milestone_pct: float, sales_value: float) -> str:
    """
    Build a detailed formula explanation for an invoicing calculation.
    
    Args:
        sub_milestone: Name of the sub-milestone
        month: Month name
        linked_activities: List of (activity_name, sub_activity, monthly_pct, sales)
        sub_milestone_pct: Percentage for this sub-milestone
        sales_value: Final calculated value
        
    Returns:
        Formatted formula string for display
    """
    formula_lines = [
        f"📊 {sub_milestone} - {month}",
        f"",
        f"Sub-Milestone %: {sub_milestone_pct}%",
    ]
    
    # Add component activities
    if linked_activities:
        formula_lines.append(f"")
        formula_lines.append(f"Linked Activities:")
        for activity, sub_activity, monthly_pct, sales in linked_activities:
            activity_display = f"{activity} > {sub_activity}" if sub_activity else activity
            formula_lines.append(f"  • {activity_display}")
            formula_lines.append(f"    - Monthly %: {monthly_pct}%")
            formula_lines.append(f"    - Sales: ${sales:,.2f}")
    
    formula_lines.append(f"")
    formula_lines.append(f"Formula: (Sub-Milestone % ÷ 100) × (Activity % ÷ 100) × Sales")
    formula_lines.append(f"Result: ${sales_value:,.2f}")
    
    return "\n".join(formula_lines)


def build_vendor_formula_text(vendor: str, bill: str, month: str,
                             linked_activities: List[Tuple[str, str, float, float]],
                             bill_pct: float, cost_value: float, credit_days: int = 0) -> str:
    """
    Build a detailed formula explanation for a vendor payment calculation.
    
    Args:
        vendor: Vendor name
        bill: Bill name
        month: Month name
        linked_activities: List of (activity_name, sub_activity, monthly_pct, cost)
        bill_pct: Percentage for this bill
        cost_value: Final calculated value
        credit_days: Credit days for payment delay
        
    Returns:
        Formatted formula string for display
    """
    formula_lines = [
        f"💰 {vendor} - {bill}",
        f"📅 {month}",
        f"",
        f"Bill %: {bill_pct}%",
    ]
    
    if credit_days > 0:
        formula_lines.append(f"Credit Days: {credit_days} days")
    
    # Add component activities
    if linked_activities:
        formula_lines.append(f"")
        formula_lines.append(f"Linked Activities:")
        for activity, sub_activity, monthly_pct, cost in linked_activities:
            activity_display = f"{activity} > {sub_activity}" if sub_activity else activity
            formula_lines.append(f"  • {activity_display}")
            formula_lines.append(f"    - Monthly %: {monthly_pct}%")
            formula_lines.append(f"    - Cost: ${cost:,.2f}")
    
    formula_lines.append(f"")
    formula_lines.append(f"Formula: (Bill % ÷ 100) × (Activity % ÷ 100) × Cost")
    formula_lines.append(f"Result: ${cost_value:,.2f}")
    
    return "\n".join(formula_lines)


def display_table_with_formulas(df: pd.DataFrame, formula_dict: Dict[Tuple[str, str], str] = None, 
                                use_aggrid: bool = True) -> None:
    """
    Display a dataframe with formula tooltips using AgGrid or fallback method.
    
    Args:
        df: DataFrame to display
        formula_dict: Optional dictionary mapping (row, column) to formula text
        use_aggrid: Whether to use AgGrid (requires streamlit-aggrid package)
    """
    import streamlit as st
    
    if df.empty:
        st.warning("No data to display")
        return
    
    if use_aggrid:
        try:
            from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
            
            # Build grid options with tooltip column
            gb = GridOptionsBuilder.from_dataframe(df)
            
            # Add column definitions with tooltips
            for col in df.columns:
                if col != '_tooltip':
                    gb.configure_column(col, 
                                       wrapText=True,
                                       autoHeight=True,
                                       cellStyle={'textAlign': 'left'})
            
            gb.configure_grid_options(
                domLayout='normal',
                suppressMovableColumns=False,
                enableRangeSelection=True,
            )
            
            grid_options = gb.build()
            
            # Display using AgGrid
            AgGrid(
                df,
                gridOptions=grid_options,
                enable_enterprise_modules=False,
                update_mode=GridUpdateMode.VALUE_CHANGED,
                allow_unsafe_jscode=False,
                height=400,
                theme='light',
                fit_columns_on_grid_load=False
            )
            
        except ImportError:
            # Fallback to regular dataframe display
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Show formula info separately
            if formula_dict:
                with st.expander("📖 Formula Reference"):
                    for (row, col), formula in sorted(formula_dict.items()):
                        st.write(f"**{row} - {col}:**")
                        st.code(formula, language='text')
    else:
        # Standard display with formula reference
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if formula_dict:
            with st.expander("📖 Formula Reference"):
                for (row, col), formula in sorted(formula_dict.items()):
                    st.write(f"**{row} - {col}:**")
                    st.write(formula)
