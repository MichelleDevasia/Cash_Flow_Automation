import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def add_page_border(section):
    sectPr = section._sectPr
    # Look for existing pgBorders first to avoid duplicates
    pgBorders = sectPr.find(qn('w:pgBorders'))
    if pgBorders is None:
        pgBorders = OxmlElement('w:pgBorders')
        pgBorders.set(qn('w:offset-from'), 'page')
        sectPr.append(pgBorders)
    
    # Add border for each side
    for border_name in ['top', 'left', 'bottom', 'right']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '12')  # 1.5 pt
        border.set(qn('w:space'), '24')
        border.set(qn('w:color'), '365F91')  # Formal Steel Blue Color
        pgBorders.append(border)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_report():
    doc = docx.Document()
    
    # Page setup - Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        add_page_border(section)
        
    # Styles Setup
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    # ---------------- PAGE 1: TITLE PAGE & ACKNOWLEDGMENT ----------------
    
    # Cover Page Top Spacing
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(36)
    
    run = p.add_run("INTERNSHIP REPORT\n\n")
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D) # Deep Navy
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("CASH FLOW AUTOMATION AND ACTIVITY TRACKING SYSTEM\n")
    run_sub.font.size = Pt(16)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    
    p_loc = doc.add_paragraph()
    p_loc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_loc = p_loc.add_run("L&T Construction\n")
    run_loc.font.size = Pt(14)
    run_loc.font.bold = True
    run_loc.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    # Metadata Spacing
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(72)
    p_meta.paragraph_format.space_after = Pt(72)
    
    run_meta = p_meta.add_run(
        "Submitted by:\n"
        "MICHELLE DEVASIA\n"
        "Register No: 2260384\n"
        "B.Tech in Computer Science (Specialisation in Data Science)\n"
        "Christ (Deemed to be University), Bengaluru\n\n"
        "Under the Guidance of:\n"
        "Mr. Karthik Chandra, Ms. Mounika, Ms. Chaitra\n"
        "L&T Construction\n\n"
        "Period of Internship: May 2nd, 2026 – June 5th, 2026"
    )
    run_meta.font.size = Pt(12)
    run_meta.font.bold = True
    
    doc.add_page_break()
    
    # ACKNOWLEDGMENTS (Page 1 Continued)
    p_ack_title = doc.add_paragraph()
    p_ack_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_ack_title.paragraph_format.space_before = Pt(18)
    run_ack = p_ack_title.add_run("ACKNOWLEDGEMENTS")
    run_ack.font.size = Pt(16)
    run_ack.font.bold = True
    run_ack.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    p_ack_body1 = doc.add_paragraph(
        "I would like to express my deepest gratitude to L&T Construction for providing me with a challenging and enriching "
        "opportunity to undertake this internship. This project has been an invaluable learning experience, giving me "
        "practical exposure to industrial planning, project finance, and web-based software automation."
    )
    p_ack_body1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    p_ack_body2 = doc.add_paragraph(
        "I am highly indebted to my industry mentors, Mr. Karthik Chandra, Ms. Mounika, and Ms. Chaitra, for their continuous support, "
        "technical mentorship, and constructive feedback throughout the course of this project. Their guidance was essential in "
        "designing a generalized system that meets the complex demands of modern construction operations."
    )
    p_ack_body2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    p_ack_body3 = doc.add_paragraph(
        "I also extend my sincere gratitude to the Department of Computer Science at Christ (Deemed to be University), Bengaluru, "
        "for their academic support and facilitating this industry collaboration, helping to bridge academic knowledge with "
        "real-world computational engineering practices."
    )
    p_ack_body3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_page_break()
    
    # ---------------- PAGE 2: SYSTEM DESIGN & FRAMEWORK ----------------
    p_p2_title = doc.add_paragraph()
    p_p2_title.paragraph_format.space_before = Pt(12)
    run_p2_title = p_p2_title.add_run("1. PROJECT CONTEXT & SYSTEM DESIGN")
    run_p2_title.font.size = Pt(16)
    run_p2_title.font.bold = True
    run_p2_title.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    # 1.1 Context
    p_1_1 = doc.add_paragraph()
    run_1_1 = p_1_1.add_run("1.1 Project Overview & Objectives")
    run_1_1.font.size = Pt(13)
    run_1_1.font.bold = True
    
    doc.add_paragraph(
        "Cash flow management is one of the most critical aspects of construction project execution. Managing "
        "project financial schedules involves tracking substantial contracts, scheduling progress, predicting "
        "billing milestones, and controlling vendor outflows. This internship focused on building a fully "
        "customizable and generalized cash flow automation system using a Python-based Streamlit web application. "
        "The primary goal was to construct a robust, flexible application that allows planning engineers to "
        "dynamically configure activities, milestones, and billing distributions without hardcoded formulas or rigid constraints."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # 1.2 System Objectives
    p_1_2 = doc.add_paragraph()
    run_1_2 = p_1_2.add_run("1.2 System Architecture & Design Objectives")
    run_1_2.font.size = Pt(13)
    run_1_2.font.bold = True
    
    doc.add_paragraph(
        "To provide a generalized solution, the system follows a decoupled architectural pattern. Instead of relying "
        "on fixed row/column layouts, the application stores raw entity data and links them dynamically. The main objectives include:"
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    bullets = [
        ("Complete Customizability:", " Users must have the ability to Create, Read, Update, and Delete (CRUD) activities, "
         "sub-activities, billing milestones, and vendor payment rules directly within the graphical web interface."),
        ("Generalized Framework:", " The application must adapt to any project configuration, timeline length, "
         "or activity breakdown without requiring code changes or schema redefinitions."),
        ("Dynamic Formulas:", " Invoicing and payment computations are executed on-the-fly, combining relational lists "
         "by position and name using flexible criteria instead of fixed cell formulas.")
    ]
    for b_title, b_desc in bullets:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_t = bp.add_run(b_title)
        r_t.bold = True
        bp.add_run(b_desc)
        
    # 1.3 Data Flow Structure
    p_1_3 = doc.add_paragraph()
    p_1_3.paragraph_format.space_before = Pt(12)
    run_1_3 = p_1_3.add_run("1.3 Core Data Flow and Storage Model")
    run_1_3.font.size = Pt(13)
    run_1_3.font.bold = True
    
    doc.add_paragraph(
        "The application utilizes local flat-file storage (CSV format) for lightweight execution. "
        "The relational diagram below describes the core data storage structure that feeds into the calculation engine:"
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Table of Core Files
    table = doc.add_table(rows=5, cols=3)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Data File'
    hdr_cells[1].text = 'Key Attributes'
    hdr_cells[2].text = 'Role in System'
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        set_cell_margins(cell)
        
    records = [
        ("activities.csv", "Activity Name, Sub-Activity, Monthly Work %, Start/End Month", "Tracks task execution timeline and monthly percentages"),
        ("cost_sales.csv", "Activity, Sub-Activity, Total Cost, Total Sales, Last Updated", "Holds the financial values mapped to specific work packages"),
        ("invoice.csv", "Milestone, Sub-Milestone, Billing %, Sales Source Activities", "Defines client billing events and links sales sources"),
        ("matching_utils.py", "Activity-Milestone Matching Data structure", "Pairs scheduling progress data directly to client billing milestones")
    ]
    
    for idx, (f, attr, role) in enumerate(records, start=1):
        row_cells = table.rows[idx].cells
        row_cells[0].text = f
        row_cells[1].text = attr
        row_cells[2].text = role
        for cell in row_cells:
            set_cell_margins(cell)
            
    doc.add_page_break()
    
    # ---------------- PAGE 3: CORE FEATURES & TECHNICAL IMPLEMENTATION ----------------
    p_p3_title = doc.add_paragraph()
    p_p3_title.paragraph_format.space_before = Pt(12)
    run_p3_title = p_p3_title.add_run("2. TECHNICAL IMPLEMENTATION & CALCULATIONS")
    run_p3_title.font.size = Pt(16)
    run_p3_title.font.bold = True
    run_p3_title.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    # 2.1 Streamlit Frontend
    p_2_1 = doc.add_paragraph()
    run_2_1 = p_2_1.add_run("2.1 Interactive Web Architecture")
    run_2_1.font.size = Pt(13)
    run_2_1.font.bold = True
    
    doc.add_paragraph(
        "The front-end interface is constructed entirely using Python's Streamlit framework, leveraging dynamic session state "
        "management to handle stateful navigation, form inputs, and real-time computation tables. The interactive interface "
        "provides the planning team with a live dashboard to update work progress and instantly visualize cash flow trends."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # 2.2 Billing Milestone Invoicing Logic
    p_2_2 = doc.add_paragraph()
    p_2_2.paragraph_format.space_before = Pt(12)
    run_2_2 = p_2_2.add_run("2.2 Invoicing Calculation Engine and Formulas")
    run_2_2.font.size = Pt(13)
    run_2_2.font.bold = True
    
    doc.add_paragraph(
        "To allow complete decoupling, the cash inflows are calculated using a specific positional pairing formula. "
        "A milestone's invoice amount in a given month is calculated as a product of its defined billing percentage, the "
        "sales values of specified source activities, and the actual monthly schedule progress of matched activities."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    p_formula = doc.add_paragraph()
    p_formula.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f = p_formula.add_run(
        "Invoice Amount (M, Month) = (Milestone % / 100) * \n"
        "Sum_{i} [ Sales(Activity_i) * (Work % (Activity_i, Month) / 100) ]"
    )
    run_f.font.bold = True
    run_f.font.size = Pt(11)
    run_f.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    # Positional Pairing detail
    p_pairing = doc.add_paragraph()
    p_pairing.paragraph_format.space_before = Pt(6)
    run_pair_title = p_pairing.add_run("Positional Matching Principle: ")
    run_pair_title.bold = True
    p_pairing.add_run(
        "When calculating milestone billing, the activities selected as Sales Sources and the activities matched for work "
        "progress are paired positionally by index (1st with 1st, 2nd with 2nd). If one list is shorter, the last element "
        "of the shorter list is automatically repeated to complete the pairing. This provides complete mathematical "
        "generalization for mismatched lists without breaking calculations."
    )
    p_pairing.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # 2.3 Vendor Payments & Outflow Structure
    p_2_3 = doc.add_paragraph()
    p_2_3.paragraph_format.space_before = Pt(12)
    run_2_3 = p_2_3.add_run("2.3 Vendor Payment Outflow Logic")
    run_2_3.font.size = Pt(13)
    run_2_3.font.bold = True
    
    doc.add_paragraph(
        "Vendor outflows track project expenses. The system introduces credit days to simulate payment delay windows "
        "common in construction logistics. Vendor billing follows conditional rules based on the matched activity count:"
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph(
        "Rule A (Single Mapped Activity): Base Payment = (Bill % / 100) * [Sum of Selected Costs] * [Work % of Activity / 100]\n"
        "Rule B (Multiple Mapped Activities): Base Payment = (Bill % / 100) * Sum [ Cost_i * (Work %_i / 100) ] via positional pairing",
        style='Normal'
    ).paragraph_format.left_indent = Inches(0.4)
    
    doc.add_paragraph(
        "To apply credit terms (e.g., 30, 45, 90, or 180 days), the calculated base payment is shifted forward in the timeline:\n"
        "Shift Months = max(1, Credit Days // 30) (if Credit Days > 0)\n"
        "Final Payment [Month + Shift Months] = Base Payment [Month]",
        style='Normal'
    ).paragraph_format.left_indent = Inches(0.4)
    
    doc.add_page_break()
    
    # ---------------- PAGE 4: RESULTS, OUTCOMES & LEARNINGS ----------------
    p_p4_title = doc.add_paragraph()
    p_p4_title.paragraph_format.space_before = Pt(12)
    run_p4_title = p_p4_title.add_run("3. RESULTS, OUTCOMES & KEY LEARNINGS")
    run_p4_title.font.size = Pt(16)
    run_p4_title.font.bold = True
    run_p4_title.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    # 3.1 Financial Verification and Cash Flow Curves
    p_3_1 = doc.add_paragraph()
    run_3_1 = p_3_1.add_run("3.1 Core Financial Verification and Cash Flow Analysis")
    run_3_1.font.size = Pt(13)
    run_3_1.font.bold = True
    
    doc.add_paragraph(
        "The system has been successfully verified against historical project profiles. In a test case utilizing a contract value of "
        "$97.07M, the calculation engine matched all invoicing milestone sums perfectly (100% mathematical integrity). "
        "By comparing the shifted vendor payment outflows and milestone billing inflows, the application automatically computes "
        "the cumulative net cash flow over the project timeline. This enables project managers to visualize cash deficits, identify "
        "critical funding gaps, and optimize credit terms with sub-contractors to maintain positive working capital."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # 3.2 Key Challenges: Complete Customizability
    p_3_2 = doc.add_paragraph()
    p_3_2.paragraph_format.space_before = Pt(12)
    run_3_2 = p_3_2.add_run("3.2 Technical Challenge: Generalization & Multi-level CRUD")
    run_3_2.font.size = Pt(13)
    run_3_2.font.bold = True
    
    doc.add_paragraph(
        "The primary technical challenge encountered during the development was implementing complete customizability. "
        "The system was required to allow users to Create, Read, Update, and Delete (CRUD) elements anywhere in the data schema—including "
        "changing activities, sub-activities, timelines, and payment formulas. Managing relational consistency in local CSV files "
        "without database constraints required creating custom validation modules. If an activity is renamed or deleted, the software "
        "automatically propagates updates to the milestone matching and vendor configuration modules, preventing orphaned references "
        "and maintaining the stability of the dynamic formulas."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # 3.3 Learning Curves
    p_3_3 = doc.add_paragraph()
    p_3_3.paragraph_format.space_before = Pt(12)
    run_3_3 = p_3_3.add_run("3.3 Internship Learnings & Personal Growth")
    run_3_3.font.size = Pt(13)
    run_3_3.font.bold = True
    
    doc.add_paragraph(
        "This internship served as an excellent bridge between theoretical data science concepts and actual project management workflows. "
        "The core areas of personal and technical development included:"
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    learn_bullets = [
        ("AI-Assisted Software Engineering:", " A significant learning curve was mastering prompt engineering. "
         "By learning to structure prompts more precisely, I was able to accelerate prototyping, generate robust validation algorithms, "
         "and discover advanced AI development platforms to debug complex indexing structures in Python."),
        ("Streamlit and CSV Operations:", " Gained hands-on experience in building interactive, responsive frontends and managing "
         "relational data flows in CSV format using Pandas, ensuring data updates are immediately reflected in visual layouts."),
        ("Construction Financial Dynamics:", " Developed an understanding of key financial terms used in industrial projects, "
         "including milestone billing, vendor credit day shifts, and profit margin estimations.")
    ]
    for l_title, l_desc in learn_bullets:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_t = bp.add_run(l_title)
        r_t.bold = True
        bp.add_run(l_desc)
        
    # 3.4 Conclusion
    p_3_4 = doc.add_paragraph()
    p_3_4.paragraph_format.space_before = Pt(12)
    run_3_4 = p_3_4.add_run("3.4 Project Closeout & Summary")
    run_3_4.font.size = Pt(13)
    run_3_4.font.bold = True
    
    doc.add_paragraph(
        "The project successfully completed its development and validation phases. The automated tool provides planning engineers "
        "with a dynamic web interface to manage timelines, costs, sales, and vendor invoices without relying on hardcoded excel grids. "
        "The customizability ensures it can adapt to future projects, serving as a robust template for automated project planning."
    ).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Save Report
    output_filename = "Michelle_Devasia_LT_Internship_Report.docx"
    doc.save(output_filename)
    print(f"Report successfully saved as {output_filename}")

if __name__ == '__main__':
    create_report()
