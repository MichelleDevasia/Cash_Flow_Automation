# 🔍 Interactive Table Hover Tooltips - Feature Guide

## What's New?

Your Cash Flow Automation system now includes **interactive hover tooltips** on all Invoice and Vendor Payment tables. When you hover over rows in the detailed reports, you'll see:

- **Calculation formulas** displayed in the info icon column (📋)
- **Monthly breakdown** showing each month's calculation
- **Formula explanation** with step-by-step details

## Installation & Setup

### Step 1: Install Required Package

The feature uses `streamlit-aggrid` for advanced table functionality. It's already added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install streamlit-aggrid>=0.3.4
```

### Step 2: Restart the Application

After installation, restart your Streamlit app:

```bash
streamlit run streamlit_app.py
```

## How to Use the Hover Tooltips

### Invoice Report Tables

Navigate to **🧾 Invoice → Invoice Calculation Report (Invoicing Report)**

The following tables now have hover tooltips:

1. **Sub-Milestones Tab**
   - Original Invoicing values
   - Advance Payments deducted
   - Net Invoicing (after advances)

2. **By Milestone Tab**
   - Milestone-level totals
   - Advance payments by milestone
   - Net amounts by milestone

3. **By Activity Tab**
   - Activity contribution to invoicing
   - Monthly distribution per activity

### Vendor Payment Tables

Navigate to **🛒 Vendor → Vendor Payment Report**

The following tables now have hover tooltips:

1. **By Bill Tab** (Tab 1)
   - Original payment values
   - Advance payments to vendors
   - Net vendor payments

2. **By Vendor Tab** (Tab 2)
   - Aggregated vendor totals
   - Advances by vendor
   - Net payments by vendor

3. **By Activity Tab** (Tab 3)
   - Vendor payments by activity
   - Activity cost contribution

## Understanding the Formula Display

### Invoice Formula Breakdown

When you hover over a cell, you'll see:
```
📊 Sub-Milestone Name - Month

Sub-Milestone %: 25%

Linked Activities:
• Activity Name > Sub-Activity
  - Monthly %: 30%
  - Sales: $10,000

Formula: (Sub-Milestone % ÷ 100) × (Activity % ÷ 100) × Sales
Result: $750
```

**Interpretation:**
- Sub-milestone percentage applies to the entire calculation
- Each linked activity's monthly percentage contributes
- Sales value is the total amount being distributed

### Vendor Payment Formula Breakdown

When you hover over a vendor payment cell:
```
💰 Vendor Name - Bill Name
📅 Month

Bill %: 50%
Credit Days: 30

Linked Activities:
• Activity Name > Sub-Activity
  - Monthly %: 40%
  - Cost: $5,000

Formula: (Bill % ÷ 100) × (Activity % ÷ 100) × Cost
Result: $1,000
```

**Interpretation:**
- Bill percentage applies to the entire calculation
- Each linked activity's monthly percentage contributes
- Cost value is the expense amount being distributed
- Credit days shift when payment is recognized

## Features

### 📋 Info Icon Column

- First column in each table shows a 📋 icon
- Hover over the icon to see row-level formula details
- Shows all months' calculations for that row

### Monthly Breakdown

Each tooltip includes:
- Individual month values
- Calculation for that specific month
- Currency formatting ($X,XXX.XX)

### Formula Explanation

The expandable "📖 View Calculation Details" section in each tab provides:
- How values are calculated
- Example calculations
- Step-by-step formulas

## Keyboard Shortcuts & Tips

| Action | Result |
|--------|--------|
| **Hover** over 📋 icon | See formula & monthly breakdown |
| **Hover** over month column | See formula for that month |
| Click **📖 View Calculation Details** | See detailed formula explanation |
| **Expand** any section | Show/hide calculation details |
| **Download CSV** | Export the table data with values |

## Troubleshooting

### Tooltips Not Showing

**Problem:** Hover tooltips are not displaying

**Solution:**
1. Ensure `streamlit-aggrid` is installed: `pip install streamlit-aggrid>=0.3.4`
2. Restart Streamlit: `Ctrl+C` then `streamlit run streamlit_app.py`
3. Clear browser cache: `Ctrl+Shift+Delete` (Chrome/Firefox)
4. Refresh page: `F5` or `Ctrl+R`

### Tables Displaying Slowly

**Problem:** Tables take a long time to load

**Solution:**
- This is normal for large datasets
- Try filtering tables using the **Filter by Milestone** or **Filter by Vendor** options
- Use the filters to focus on specific sections

### Fallback to Regular Display

**Note:** If `streamlit-aggrid` is not installed, tables will display using regular Streamlit dataframes with a tip message to install `streamlit-aggrid` for enhanced tooltips.

## Technical Details

### Files Modified

1. **formula_utils.py** (NEW)
   - Formula tracking and display utilities
   - Helper functions for building formula text
   - Fallback display support

2. **streamlit_app.py** (MODIFIED)
   - Added `display_table_with_hover_tooltips()` function
   - Imported formula utilities
   - Replaced all major table displays with hover-enabled versions

3. **requirements.txt** (MODIFIED)
   - Added `streamlit-aggrid>=0.3.4`
   - Added `python-dateutil>=2.8.0` (if not present)

### Configuration

The `display_table_with_hover_tooltips()` function:
- Automatically detects column types (months vs. row labels)
- Builds formula strings dynamically
- Falls back to regular display if AgGrid unavailable
- Maintains all existing functionality

## What's Calculated in the Tooltips?

### Invoice Calculations

For each **Sub-Milestone** and **Month**:

```
Invoice Amount = (Sub-Milestone % / 100) × 
                  (Activity % / 100) × 
                  Activity Sales
```

**Factors:**
1. Sub-Milestone percentage (e.g., 25% of total project)
2. Activity work percentage for that month
3. Sales value of the activity

### Vendor Payment Calculations

For each **Bill** and **Month**:

```
Payment Amount = (Bill % / 100) × 
                 (Activity % / 100) × 
                 Activity Cost × 
                 (1 - Credit Days Shift)
```

**Factors:**
1. Bill percentage (e.g., 50% of vendor costs)
2. Activity cost percentage for that month
3. Cost value of the activity
4. Credit days shift (if applicable)

## Future Enhancements

Potential improvements:
- Copy formula to clipboard on click
- Export formula annotations with CSV
- Formula audit trail / history
- Custom formula templates
- Formula validator / checker

## Support

For questions or issues:
1. Check the **📖 View Calculation Details** sections in each tab
2. Review this guide's **Troubleshooting** section
3. Verify all requirements are installed
4. Ensure data is properly configured (activities, milestones, matches)

---

**Version:** 1.0
**Last Updated:** June 1, 2026
