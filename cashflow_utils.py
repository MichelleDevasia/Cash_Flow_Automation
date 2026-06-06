import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from calculation_utils import (
    calculate_invoicing_table, 
    calculate_vendor_payment_table,
    get_calculation_months
)
from timeline_utils import get_project_config, get_extended_months

def extract_cumulative_row(df, index_col=None):
    """
    Extract the CUMULATIVE row from a dataframe.
    
    Args:
        df: DataFrame with months as columns and data rows
        index_col: Name of the index column (if any)
    
    Returns:
        Tuple of (months_list, cumulative_values_list) or (None, None) if CUMULATIVE not found
    """
    if df.empty:
        return None, None
    
    # Get calculation months
    calc_months = get_calculation_months()
    
    # Find the CUMULATIVE row
    cumulative_row = None
    
    if index_col and index_col in df.columns:
        cumulative_mask = df[index_col] == 'CUMULATIVE'
        if cumulative_mask.any():
            cumulative_row = df[cumulative_mask].iloc[0]
    else:
        # Try to find CUMULATIVE in the first column if it's the index
        if isinstance(df.index, pd.MultiIndex):
            # Check if CUMULATIVE is in the index
            cumulative_mask = df.index.get_level_values(0) == 'CUMULATIVE'
            if cumulative_mask.any():
                cumulative_row = df[cumulative_mask].iloc[0]
        else:
            # Check all rows for CUMULATIVE value
            for col in df.columns:
                cumulative_mask = df[col] == 'CUMULATIVE'
                if cumulative_mask.any():
                    cumulative_row = df[cumulative_mask].iloc[0]
                    break
    
    if cumulative_row is None:
        return None, None
    
    # Extract month values
    months = []
    values = []
    
    for month in calc_months:
        if month in cumulative_row.index:
            months.append(month)
            try:
                val = float(cumulative_row[month])
                values.append(val)
            except (ValueError, TypeError):
                values.append(0)
    
    return months, values


def get_cumulative_invoicing():
    """
    Get cumulative true cash inflow (net collections + advances).
    
    Returns:
        Tuple of (months_list, cumulative_values_list)
    """
    try:
        from calculation_utils import calculate_net_collection_table, calculate_advance_table
        
        calc_months = get_calculation_months()
        
        # Get Net Collections
        net_df = calculate_net_collection_table()
        _, net_vals = extract_cumulative_row(net_df)
        if not net_vals:
            net_vals = [0] * len(calc_months)
            
        # Get Advances
        adv_df = calculate_advance_table()
        _, adv_vals = extract_cumulative_row(adv_df)
        if not adv_vals:
            adv_vals = [0] * len(calc_months)
            
        # Sum them up (they should be same length since they both use calc_months)
        total_vals = [float(n) + float(a) for n, a in zip(net_vals, adv_vals)]
        
        return calc_months, total_vals
    except Exception as e:
        print(f"Error getting cumulative invoicing: {e}")
        calc_months = get_calculation_months()
        return calc_months, [0] * len(calc_months)


def get_cumulative_vendor_payment():
    """
    Get cumulative true cash outflow (net vendor payments + vendor advances).
    
    Returns:
        Tuple of (months_list, cumulative_values_list)
    """
    try:
        from calculation_utils import calculate_net_vendor_payment_table, calculate_vendor_advance_table
        
        calc_months = get_calculation_months()
        
        # Get Net Vendor Payments
        net_df = calculate_net_vendor_payment_table()
        _, net_vals = extract_cumulative_row(net_df)
        if not net_vals:
            net_vals = [0] * len(calc_months)
            
        # Get Vendor Advances
        adv_df = calculate_vendor_advance_table()
        _, adv_vals = extract_cumulative_row(adv_df)
        if not adv_vals:
            adv_vals = [0] * len(calc_months)
            
        # Sum them up
        total_vals = [float(n) + float(a) for n, a in zip(net_vals, adv_vals)]
        
        return calc_months, total_vals
    except Exception as e:
        print(f"Error getting cumulative vendor payment: {e}")
        calc_months = get_calculation_months()
        return calc_months, [0] * len(calc_months)


def calculate_net_cashflow(inflow_values, outflow_values):
    """
    Calculate net cashflow for each month.
    
    Formula: Net Cashflow = Inflow - Outflow
    
    Args:
        inflow_values: List of cumulative inflow values
        outflow_values: List of cumulative outflow values
    
    Returns:
        List of net cashflow values (positive = inflow exceeds outflow, profit; negative = loss)
    """
    net_values = []
    
    for inflow, outflow in zip(inflow_values, outflow_values):
        try:
            net = float(inflow) - float(outflow)
            net_values.append(net)
        except (ValueError, TypeError):
            net_values.append(0)
    
    return net_values


def format_month_label(month_str):
    """
    Format month string from 'Month Year' to abbreviated format.
    
    Example: 'June 2025' -> "Jun'25"
    
    Args:
        month_str: String in format "Month Year"
    
    Returns:
        Abbreviated month label
    """
    if not month_str:
        return ''
    
    parts = str(month_str).split()
    if len(parts) >= 2:
        month_name = parts[0][:3]  # First 3 letters
        year = parts[1][-2:]  # Last 2 digits of year
        return f"{month_name}'{year}"
    
    return month_str


def _format_value_label(value):
    """Format a numeric value as a compact currency string for chart labels."""
    abs_val = abs(value)
    sign = '-' if value < 0 else ''
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:,.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:,.0f}K"
    else:
        return f"{sign}${abs_val:,.0f}"


def _find_crossings(x_positions, inflow_values, outflow_values):
    """
    Find approximate crossing points where inflow and outflow curves intersect.
    
    Returns:
        List of (x_cross, y_cross) tuples for each crossing point.
    """
    crossings = []
    inflow_arr = np.array(inflow_values, dtype=float)
    outflow_arr = np.array(outflow_values, dtype=float)
    diff = inflow_arr - outflow_arr
    
    for i in range(len(diff) - 1):
        # Sign change means crossing
        if diff[i] * diff[i + 1] < 0:
            # Linear interpolation to find crossing x
            t = abs(diff[i]) / (abs(diff[i]) + abs(diff[i + 1]))
            x_cross = x_positions[i] + t * (x_positions[i + 1] - x_positions[i])
            y_cross = inflow_arr[i] + t * (inflow_arr[i + 1] - inflow_arr[i])
            crossings.append((x_cross, y_cross))
    
    return crossings


def create_cashflow_curve(custom_months=None, custom_inflow=None, custom_outflow=None, custom_net=None):
    """
    Create a comprehensive, professional cash flow S-curve visualization.
    
    Features:
    - Smooth interpolated cumulative inflow & outflow curves with gradient fills
    - Net cashflow bars (emerald green for positive, dark red for negative)
    - Annotated key data points (first, last, peak months)
    - Peak exposure annotation
    - Crossing-point detection and annotation
    - Modern color palette and clean typography
    
    Returns:
        matplotlib figure object
    """
    # --- Modern styling setup ---
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except OSError:
        try:
            plt.style.use('seaborn-whitegrid')
        except OSError:
            pass  # Fall back to default style
    
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans']
    
    # --- Color palette ---
    COLOR_INFLOW = '#2E86AB'   # Steel blue
    COLOR_OUTFLOW = '#E74C3C'  # Coral red
    COLOR_NET_POS = '#27AE60'  # Emerald
    COLOR_NET_NEG = '#C0392B'  # Dark red
    COLOR_TEXT = '#2C3E50'
    COLOR_GRID = '#D5D8DC'
    COLOR_SPINE = '#BDC3C7'
    
    # --- Get data ---
    if custom_months is not None and custom_inflow is not None and custom_outflow is not None and custom_net is not None:
        months = custom_months
        inflow_values = custom_inflow
        outflow_values = custom_outflow
        net_values = custom_net
    else:
        months_inflow, inflow_values = get_cumulative_invoicing()
        months_outflow, outflow_values = get_cumulative_vendor_payment()
        
        # Use the longer list as reference
        if len(months_inflow) >= len(months_outflow):
            months = months_inflow
            # Pad outflow if needed
            while len(outflow_values) < len(months):
                outflow_values.append(outflow_values[-1] if outflow_values else 0)
        else:
            months = months_outflow
            # Pad inflow if needed
            while len(inflow_values) < len(months):
                inflow_values.append(inflow_values[-1] if inflow_values else 0)
        
        # Calculate net cashflow
        net_values = calculate_net_cashflow(inflow_values, outflow_values)
    
    # --- Create figure ---
    fig, ax1 = plt.subplots(figsize=(15, 9), dpi=300)
    fig.patch.set_facecolor('#FAFBFC')
    ax1.set_facecolor('#FAFBFC')
    
    # Clean spines
    for spine in ['top', 'right']:
        ax1.spines[spine].set_visible(False)
    ax1.spines['left'].set_color(COLOR_SPINE)
    ax1.spines['bottom'].set_color(COLOR_SPINE)
    ax1.spines['left'].set_linewidth(0.8)
    ax1.spines['bottom'].set_linewidth(0.8)
    
    # --- X-axis setup ---
    x_positions = np.arange(len(months))
    formatted_labels = [format_month_label(m) for m in months]
    
    # --- Smooth interpolation using numpy ---
    if len(x_positions) > 2:
        x_smooth = np.linspace(x_positions[0], x_positions[-1], max(len(x_positions) * 8, 200))
        inflow_smooth = np.interp(x_smooth, x_positions, inflow_values)
        outflow_smooth = np.interp(x_smooth, x_positions, outflow_values)
    else:
        x_smooth = x_positions.astype(float)
        inflow_smooth = np.array(inflow_values, dtype=float)
        outflow_smooth = np.array(outflow_values, dtype=float)
    
    # --- Plot net cashflow bars (behind lines) ---
    bar_colors = [COLOR_NET_POS if val >= 0 else COLOR_NET_NEG for val in net_values]
    bars = ax1.bar(x_positions, net_values, color=bar_colors, alpha=0.6,
                   width=0.4, label='Net Cashflow', zorder=2,
                   edgecolor=[c + '80' for c in bar_colors], linewidth=0.5)
    
    # --- Gradient fill under curves ---
    ax1.fill_between(x_smooth, 0, inflow_smooth, alpha=0.08, color=COLOR_INFLOW, zorder=3)
    ax1.fill_between(x_smooth, 0, outflow_smooth, alpha=0.08, color=COLOR_OUTFLOW, zorder=3)
    
    # --- Plot smooth cumulative lines ---
    ax1.plot(x_smooth, inflow_smooth, color=COLOR_INFLOW, linewidth=2.8,
             label='Cumulative Cash Inflow', zorder=5, solid_capstyle='round')
    ax1.plot(x_positions, inflow_values, color=COLOR_INFLOW, linewidth=0,
             marker='o', markersize=4.5, markerfacecolor='white',
             markeredgecolor=COLOR_INFLOW, markeredgewidth=1.8, zorder=6)
    
    ax1.plot(x_smooth, outflow_smooth, color=COLOR_OUTFLOW, linewidth=2.8,
             label='Cumulative Cash Outflow', zorder=5, solid_capstyle='round')
    ax1.plot(x_positions, outflow_values, color=COLOR_OUTFLOW, linewidth=0,
             marker='s', markersize=4.5, markerfacecolor='white',
             markeredgecolor=COLOR_OUTFLOW, markeredgewidth=1.8, zorder=6)
    
    # --- Axis formatting ---
    ax1.set_xlabel('Timeline', fontsize=11, fontweight='medium', color=COLOR_TEXT, labelpad=10)
    ax1.set_ylabel('Amount (Cr)', fontsize=11, fontweight='medium', color=COLOR_TEXT, labelpad=10)
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(formatted_labels, rotation=45, ha='right', fontsize=9, color='#555555')
    ax1.tick_params(axis='y', labelsize=9, colors='#555555')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Light grid on both axes
    ax1.grid(axis='both', alpha=0.15, linestyle='-', color=COLOR_GRID, linewidth=0.6)
    
    # Zero baseline
    ax1.axhline(y=0, color='#7F8C8D', linestyle='-', linewidth=0.8, alpha=0.6, zorder=1)
    
    # --- Value labels at last data points ---
    if len(inflow_values) > 0:
        last_idx = len(inflow_values) - 1
        ax1.annotate(_format_value_label(inflow_values[last_idx]),
                     xy=(x_positions[last_idx], inflow_values[last_idx]),
                     xytext=(8, 6), textcoords='offset points',
                     fontsize=8.5, fontweight='bold', color=COLOR_INFLOW,
                     ha='left', va='bottom', zorder=8)
    
    if len(outflow_values) > 0:
        last_idx = len(outflow_values) - 1
        ax1.annotate(_format_value_label(outflow_values[last_idx]),
                     xy=(x_positions[last_idx], outflow_values[last_idx]),
                     xytext=(8, -6), textcoords='offset points',
                     fontsize=8.5, fontweight='bold', color=COLOR_OUTFLOW,
                     ha='left', va='top', zorder=8)
    
    # --- Annotate key data points (first, peak, last) for inflow ---
    if len(inflow_values) > 2:
        peak_inflow_idx = int(np.argmax(inflow_values))
        for idx in [0, peak_inflow_idx]:
            if idx != len(inflow_values) - 1:  # Skip if same as last (already labeled)
                ax1.annotate(_format_value_label(inflow_values[idx]),
                             xy=(x_positions[idx], inflow_values[idx]),
                             xytext=(0, 10), textcoords='offset points',
                             fontsize=7.5, color=COLOR_INFLOW, ha='center', va='bottom',
                             alpha=0.85, zorder=8)
    
    # --- Peak exposure annotation (BUG 4 fix) ---
    negative_values = [v for v in net_values if v < 0]
    peak_negative = min(negative_values) if negative_values else 0
    
    if negative_values:
        peak_idx = net_values.index(peak_negative)
        peak_month_label = formatted_labels[peak_idx] if peak_idx < len(formatted_labels) else ''
        
        annotation_text = (
            f"Peak Cash Exposure\n"
            f"{_format_value_label(abs(peak_negative))} in {peak_month_label}"
        )
        
        bbox_props = dict(boxstyle='round,pad=0.6', facecolor='#FFF5F5',
                         edgecolor=COLOR_NET_NEG, linewidth=1.2, alpha=0.95)
        
        # Smart placement: offset right and below
        x_offset = min(peak_idx + 1.5, len(months) - 1)
        y_offset = peak_negative - abs(peak_negative) * 0.25
        
        ax1.annotate(annotation_text,
                    xy=(peak_idx, peak_negative),
                    xytext=(x_offset, y_offset),
                    bbox=bbox_props,
                    fontsize=9,
                    fontweight='bold',
                    color=COLOR_NET_NEG,
                    ha='left',
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2',
                                  color=COLOR_NET_NEG, lw=1.3),
                    zorder=9)
    
    # --- Crossing-point annotation ---
    crossings = _find_crossings(x_positions, inflow_values, outflow_values)
    for i, (x_cross, y_cross) in enumerate(crossings[:2]):  # Show at most 2 crossings
        ax1.plot(x_cross, y_cross, marker='D', markersize=7, color='#8E44AD',
                 markeredgecolor='white', markeredgewidth=1.5, zorder=10)
        
        cross_label = "Breakeven" if i == 0 else f"Crossing #{i + 1}"
        ax1.annotate(cross_label,
                     xy=(x_cross, y_cross),
                     xytext=(0, 18), textcoords='offset points',
                     fontsize=8, fontweight='bold', color='#8E44AD',
                     ha='center', va='bottom',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#F4ECF7',
                              edgecolor='#8E44AD', linewidth=0.8, alpha=0.9),
                     arrowprops=dict(arrowstyle='->', color='#8E44AD', lw=1.0),
                     zorder=10)
    
    # --- Legend (compact, upper left, semi-transparent) ---
    legend = ax1.legend(loc='upper left', frameon=True, fancybox=True, shadow=False,
                       fontsize=9.5, borderpad=0.8, labelspacing=0.5,
                       handlelength=2.0, handleheight=0.8)
    legend.get_frame().set_facecolor('#FFFFFFD0')  # Semi-transparent white
    legend.get_frame().set_edgecolor(COLOR_SPINE)
    legend.get_frame().set_linewidth(0.6)
    
    # --- Title and subtitle ---
    if len(formatted_labels) >= 2:
        date_range = f"{formatted_labels[0]}  →  {formatted_labels[-1]}"
    else:
        date_range = ""
    
    ax1.set_title('Project Cash Flow S-Curve', fontsize=16, fontweight='bold',
                  color=COLOR_TEXT, pad=24, loc='left')
    if date_range:
        ax1.text(0.0, 1.02, date_range, transform=ax1.transAxes,
                 fontsize=10, color='#7F8C8D', style='italic', va='bottom')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    return fig


def save_and_display_cashflow_curve(output_path='cashflow_curve.png'):
    """
    Create, save, and display the cash flow curve.
    
    Args:
        output_path: Path where to save the PNG file
    
    Returns:
        Path to the saved file or None if error
    """
    try:
        fig = create_cashflow_curve()
        
        # Save the figure
        fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Cash flow curve saved to: {output_path}")
        
        # Display
        plt.show()
        
        return output_path
    
    except Exception as e:
        print(f"❌ Error creating cash flow curve: {e}")
        return None


def save_and_display_vendor_chart(vendor_name, output_path=None):
    """
    Create, save, and display the vendor cumulative chart.
    
    Args:
        vendor_name: Name of the vendor to visualize
        output_path: Optional path where to save the PNG file
    
    Returns:
        Path to the saved file or None if error
    """
    try:
        fig = create_vendor_cumulative_chart(vendor_name)
        
        # Save if path provided
        if output_path:
            fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✅ Vendor chart saved to: {output_path}")
        
        # Display
        plt.show()
        
        return output_path if output_path else True
    
    except Exception as e:
        print(f"❌ Error creating vendor chart: {e}")
        return None

def get_custom_cumulative_invoicing(selected_milestones):
    """
    Get cumulative true cash inflow (net collections + advances) for specific milestones.
    """
    try:
        from calculation_utils import calculate_net_collection_by_milestone, calculate_advance_by_milestone, get_calculation_months
        import pandas as pd
        
        calc_months = get_calculation_months()
        if not selected_milestones:
            return calc_months, [0] * len(calc_months)
            
        # Get Net Collections
        net_df = calculate_net_collection_by_milestone()
        # Get Advances
        adv_df = calculate_advance_by_milestone()
        
        total_vals = [0] * len(calc_months)
        
        if not net_df.empty:
            net_df = net_df[net_df['Milestone'].isin(selected_milestones)]
            for month_idx, month in enumerate(calc_months):
                if month in net_df.columns:
                    total_vals[month_idx] += net_df[month].sum()
                    
        if not adv_df.empty:
            adv_df = adv_df[adv_df['Milestone'].isin(selected_milestones)]
            for month_idx, month in enumerate(calc_months):
                if month in adv_df.columns:
                    total_vals[month_idx] += adv_df[month].sum()
                    
        # Now make it cumulative
        cumulative_vals = []
        current_sum = 0
        for val in total_vals:
            current_sum += float(val) if pd.notna(val) else 0
            cumulative_vals.append(current_sum)
            
        return calc_months, cumulative_vals
    except Exception as e:
        print(f"Error getting custom cumulative invoicing: {e}")
        from calculation_utils import get_calculation_months
        calc_months = get_calculation_months()
        return calc_months, [0] * len(calc_months)


def get_custom_cumulative_vendor_payment(selected_vendors):
    """
    Get cumulative true cash outflow (net vendor payments + vendor advances) for specific vendors.
    """
    try:
        from calculation_utils import calculate_net_vendor_by_vendor, calculate_vendor_advance_by_vendor, get_calculation_months
        import pandas as pd
        
        calc_months = get_calculation_months()
        if not selected_vendors:
            return calc_months, [0] * len(calc_months)
            
        # Get Net Vendor Payments
        net_df = calculate_net_vendor_by_vendor()
        # Get Vendor Advances
        adv_df = calculate_vendor_advance_by_vendor()
        
        total_vals = [0] * len(calc_months)
        
        if not net_df.empty:
            net_df = net_df[net_df['Vendor'].isin(selected_vendors)]
            for month_idx, month in enumerate(calc_months):
                if month in net_df.columns:
                    total_vals[month_idx] += net_df[month].sum()
                    
        if not adv_df.empty:
            adv_df = adv_df[adv_df['Vendor'].isin(selected_vendors)]
            for month_idx, month in enumerate(calc_months):
                if month in adv_df.columns:
                    total_vals[month_idx] += adv_df[month].sum()
                    
        # Now make it cumulative
        cumulative_vals = []
        current_sum = 0
        for val in total_vals:
            current_sum += float(val) if pd.notna(val) else 0
            cumulative_vals.append(current_sum)
            
        return calc_months, cumulative_vals
    except Exception as e:
        print(f"Error getting custom cumulative vendor payment: {e}")
        from calculation_utils import get_calculation_months
        calc_months = get_calculation_months()
        return calc_months, [0] * len(calc_months)
