# Quick Start Guide

## 🚀 Starting the Application

### Option 1: Windows Batch File (Easiest)
Double-click `start_app.bat` in the folder

### Option 2: Command Line
```bash
streamlit run streamlit_app.py
```

### Option 3: PowerShell
```powershell
cd "c:\Users\Miche\OneDrive\Desktop\lt\pro4"
streamlit run streamlit_app.py
```

## 📝 First Steps

1. **Open the App**: The app will open in your browser at `http://localhost:8501`

2. **Add Your First Activity**:
   - Click "Add Activity" in the sidebar
   - Enter an activity name (e.g., "Q2 Project Planning")
   - Select start date (year + month)
   - Select end date (year + month)
   - Decide if you want sub-activities
   - Enter work percentages for each month (they must add to 100%)
   - Optionally add cost and sales
   - Click "Add Activity"

3. **View Your Activities**:
   - Go to "View Activities"
   - You'll see a table of all activities
   - Download as CSV if needed

4. **Track Costs & Sales** (Optional):
   - Go to "Cost & Sales"
   - Add or update costs and sales for your activities
   - View summary statistics

5. **Dashboard**:
   - Go to "Summary"
   - See visual charts of work distribution
   - View profit analysis

## 💡 Example Activity

**Activity Name**: Website Redesign
**Start**: March 2024
**End**: August 2024
**Sub-activities**: Frontend, Backend
**Work Distribution**:
- March: 10%
- April: 20%
- May: 25%
- June: 25%
- July: 20%
- August: 0%
**Total**: 100% ✅

## 🔧 Troubleshooting

**Port already in use?**
```bash
streamlit run streamlit_app.py --server.port 8502
```

**Want to clear all data?**
- Delete `activities.csv` and `cost_sales.csv`
- Restart the app

**Want to go back to CLI version?**
```bash
python activity_tracker.py
```

## 📊 File Structure

After running the app, you'll see:
- `activities.csv` - All activity data
- `cost_sales.csv` - Cost and sales information
- Both can be opened in Excel for further analysis
