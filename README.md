# Activity Tracker - Data Collection System

## Overview
A **Streamlit-based web application** for collecting and managing activity data with:
- 📋 Activity names with optional sub-activities
- 📅 Calendar-based month/year selection
- 📊 Monthly work percentage distribution (must add to 100%)
- 💰 Optional cost and sales tracking
- 📁 CSV file storage for easy analysis
- 📈 Interactive dashboards and visualizations

## Project Structure

```
activity_tracker/
├── streamlit_app.py       # Main Streamlit UI interface
├── activity_utils.py      # Activity management utilities
├── cost_sales.py          # Cost and sales management module
├── activity_tracker.py    # Legacy CLI version
├── requirements.txt       # Python dependencies
├── activities.csv         # Activity data storage
├── cost_sales.csv         # Cost/sales data storage
└── README.md             # This file
```

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Or manually install:
```bash
pip install streamlit pandas plotly
```

## Running the Application

### Streamlit Web UI (Recommended)
```bash
streamlit run streamlit_app.py
```
The app will open at `http://localhost:8501`

### Legacy CLI Version
```bash
python activity_tracker.py
```

## Features

### 🏠 Home Page
- Quick overview of activities and statistics
- Access to all main features

### ➕ Add Activity
- **Activity Name**: Give your activity a name
- **Calendar Date Selection**: Choose start and end dates with year and month dropdowns
- **Sub-Activities**: Add multiple sub-activities (optional)
- **Work Distribution**: Assign work percentages to each month (must total 100%)
- **Cost & Sales**: Optionally add cost and sales data

### 👁️ View Activities
- Display all activities in a table format
- Filter by activity name
- Download activities as CSV

### 💰 Cost & Sales Management
- **View**: See all cost/sales records
- **Add/Update**: Add or modify cost and sales for activities
- **Summary**: View total cost, sales, profit, and profit margin

### 📊 Summary & Dashboard
- Work distribution chart across months
- Cost vs Sales comparison
- Key metrics and statistics
- Profit margin calculation

## CSV File Structure

### activities.csv
Columns:
- **Activity**: Main activity name
- **Sub-Activity**: Sub-activity name (empty if main activity)
- **Start Month**: Month work begins (January-December)
- **End Month**: Month work ends (January-December)
- **Cost**: Optional cost value
- **Sales**: Optional sales value
- **January through December**: Work percentage for each month (0-100)

Example:
```
Activity,Sub-Activity,Start Month,End Month,Cost,Sales,January,February,March,April,May,June,July,August,September,October,November,December
Project Alpha,,January,June,,50,20,20,15,15,15,15,0,0,0,0,0,0
Project Alpha,Design,January,February,,30,10,10,0,0,0,0,0,0,0,0,0,0
Project Alpha,Development,March,June,,20,0,0,15,15,15,15,0,0,0,0,0,0
```

### cost_sales.csv
Columns:
- **Activity**: Activity name
- **Sub-Activity**: Sub-activity name (or empty for main)
- **Cost**: Total cost
- **Sales**: Total sales
- **Notes**: Any additional notes
- **Last Updated**: When the record was last modified

## Validation Rules

✅ **Activity Name**: Required, cannot be empty
✅ **Start/End Month**: Must be valid months (January-December)
✅ **Work Percentages**: Must total exactly 100% across the activity period
✅ **Cost/Sales**: Optional, must be valid numbers if provided

## Tips

- **Multiple Sub-Activities**: Each sub-activity gets the same cost/sales if provided
- **Percentage Distribution**: Carefully distribute work across months (e.g., 25% in 4 months = 100%)
- **Edit Data**: Download CSV, edit in Excel, and re-import
- **Cost/Sales**: Completely optional - add only when needed
- **Export**: All data is stored in CSV format for easy sharing and analysis

## File Storage

All data is stored locally in CSV files:
- `activities.csv` - All activity and work percentage data
- `cost_sales.csv` - Cost and sales information
- Both files are in the same directory as the application

## Example Workflow

1. **Go to Add Activity**
   - Enter "Website Redesign"
   - Select start: March 2024
   - Select end: August 2024
   - Add sub-activities: "Frontend", "Backend"
   - Distribute work: March-August (e.g., 10%, 20%, 25%, 25%, 20%, 0% = 100%)

2. **Add Cost & Sales**
   - Go to Cost & Sales
   - Select "Website Redesign > Frontend"
   - Add cost: $5000
   - Add sales: $8000

3. **View Dashboard**
   - See work distribution chart
   - View profit calculations ($3000 in this case)
   - Download reports

## Troubleshooting

**Issue**: "Percentages must add up to 100%"
- Make sure all months sum to exactly 100%
- Check for decimal values (use whole numbers)

**Issue**: CSV file not updating
- Restart the Streamlit app: Press Ctrl+C and run again
- Refresh the browser page

**Issue**: Streamlit not starting
- Ensure Python 3.8+
- Reinstall streamlit: `pip install --upgrade streamlit`
