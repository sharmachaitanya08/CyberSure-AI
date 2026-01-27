from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import uuid, os
from textwrap import wrap
import re
from reportlab.lib.utils import ImageReader


# ================= PAGE SETTINGS =================
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
TOP_MARGIN = PAGE_HEIGHT - 40
BOTTOM_MARGIN = 40
MAX_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN


# ================= LABEL ALIGN HELPER =================
def label_value(label, value, width=12):
    return f"{label.ljust(width)}: {value}"



def normalize_fir_text(text: str) -> str:
    """
    Ensure FIR text is split into readable paragraphs
    even if AI returns a single long paragraph
    """
    if not text:
        return ""

    # already has paragraph breaks
    if "\n\n" in text:
        return text

    # sentence based split
    sentences = re.split(r'(?<=[.!?])\s+', text)

    parts = []
    current = ""

    for s in sentences:
        current += s + " "
        if len(current) > 300:   # 👈 approx paragraph size
            parts.append(current.strip())
            current = ""

    if current.strip():
        parts.append(current.strip())

    return "\n\n".join(parts)



# ================= TEXT WRAPPER =================
def draw_paragraph(c, text, y, font="Times-Roman", size=10.5, leading=17):
    """
    Draw wrapped text safely across pages with proper spacing
    """
    c.setFont(font, size)
    text_obj = c.beginText(LEFT_MARGIN, y)

    max_chars = int(MAX_WIDTH / (size * 0.55))

    for line in text.split("\n"):
        wrapped_lines = wrap(line, max_chars) or [""]
        for w in wrapped_lines:
            if text_obj.getY() < BOTTOM_MARGIN:
                c.drawText(text_obj)
                c.showPage()
                c.setFont(font, size)
                text_obj = c.beginText(LEFT_MARGIN, TOP_MARGIN)
            text_obj.textLine(w)

    c.drawText(text_obj)
    return text_obj.getY() - 10


# ================= MAIN PDF GENERATOR =================
def generate_pdf(fir):
    os.makedirs("generated_fir", exist_ok=True)

    file_id = uuid.uuid4().hex[:10].upper()
    year = datetime.now().year
    lr_no = f"{file_id}/{year}"

    filename = f"FIR_{file_id}.pdf"

    path = f"generated_fir/{filename}"

    c = canvas.Canvas(path, pagesize=A4)
    y = TOP_MARGIN

    # ================= HEADER =================
    logo_path = "logo.png"

    TITLE_FONT_SIZE = 14
    LOGO_SIZE = 75   # square box, shape oval hi rahegi

# Title Y reference
    header_y = y

# ---- LOGO (vertically aligned with title) ----
    try:
       logo = ImageReader(logo_path)

       c.drawImage(
        logo,
        LEFT_MARGIN,
        header_y - (LOGO_SIZE /2)-4,  # 👈 KEY ALIGNMENT FIX
        width=LOGO_SIZE,
        height=LOGO_SIZE,
        preserveAspectRatio=True,     # 👈 shape SAFE (oval)
        mask='auto'
      )
    except:
       pass

# ---- TITLE ----
    c.setFont("Times-Bold", TITLE_FONT_SIZE)
    c.drawCentredString(PAGE_WIDTH / 2, header_y, "RAJASTHAN POLICE")

# Move Y down after header
    y -= 65


    c.setFont("Times-Roman", 10)
    c.drawString(LEFT_MARGIN, y, f"LR NO: {file_id}/2025")
    c.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        y,
        f"DATE: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}"
    )
    y -= 35
    
    # ================= 1. COMPLAINANT DETAILS =================
    c.setFont("Times-Bold", 11)
    c.drawString(LEFT_MARGIN, y, "1. COMPLAINANT DETAILS")
    y -= 22

    y = draw_paragraph(
        c,
        f"{label_value('Name', fir.get('name', 'N/A').title())}\n"
        f"{label_value('Address', fir.get('address', 'N/A').title())}\n"
        f"{label_value('Pincode', str(fir.get('pincode', 'N/A')))}\n"
        f"{label_value('Mobile', str(fir.get('mobile', 'N/A')))}\n",
        y
    )

    # ================= 2. CRIME DETAILS =================
    bns_list = ", ".join(fir.get("bns_sections", []))
    bnss_list = ", ".join(fir.get("bnss_sections", []))
    it_list = ", ".join(fir.get("it_act_sections", []))

    bns_sections = (
    f"Sections {bns_list} of the Bharatiya Nyaya Sanhita"
    if bns_list else None
    )

    bnss_sections = (
    f"Sections {bnss_list} of the Bharatiya Nagarik Suraksha Sanhita"
    if bnss_list else None
    )

    it_act_sections = (
    f"Sections {it_list} of the Information Technology Act"
    if it_list else None
    )



    y -= 10
    c.setFont("Times-Bold", 11)
    c.drawString(LEFT_MARGIN, y, "2. CRIME DETAILS")
    y -= 22

    crime_details_text = f"Nature of Offence:\n{fir.get('crime_type', 'N/A').title()}\n\n"

    if bns_list:
      crime_details_text += (
        "Applicable BNS Sections:\n"
        f"{bns_sections}\n\n"
      )

    if bnss_list:
      crime_details_text += (
        "Applicable BNSS Sections:\n"
        f"{bnss_sections}\n\n"
      )

    if it_list:
      crime_details_text += (
        "Applicable IT Act Sections:\n"
        f"{it_act_sections}\n\n"
      )

    crime_details_text = crime_details_text.rstrip("\n")

    y = draw_paragraph(
       c,
       crime_details_text,
       y
    )



    # ================= 3. INCIDENT DESCRIPTION =================
    y -= 10
    c.setFont("Times-Bold", 11)
    c.drawString(LEFT_MARGIN, y, "3. BRIEF DESCRIPTION OF THE INCIDENT")
    y -= 22

    fir_text = normalize_fir_text(fir.get("fir_text", "N/A"))

    y = draw_paragraph(
        c,
        fir_text,
        y,
        font="Times-Roman",
        size=10.5,
        leading=20
    )

    # ================= NOTES =================
    y -= 10
    c.setFont("Times-Bold", 10)
    c.drawString(LEFT_MARGIN, y, "NOTES:")
    y -= 16

    y = draw_paragraph(
        c,
        "(i) This is a digitally generated report and does not require a physical signature.\n"
        "(ii) The concerned authority may verify the identity if required.",
        y,
        font="Times-Roman",
        size=9.5,
        leading=15
    )

    # ================= DISCLAIMERS =================
    y -= 6
    c.setFont("Times-Bold", 10)
    c.drawString(LEFT_MARGIN, y, "DISCLAIMERS:")
    y -= 16

    y = draw_paragraph(
        c,
        "(i) This document is generated for assistance and preliminary reporting purposes only.\n"
        "(ii) False reporting is punishable under applicable law.",
        y,
        font="Times-Roman",
        size=9.5,
        leading=15
    )

    # ================= FOOTER =================
    footer_y = 90

    c.setFont("Times-Bold", 11)
    c.drawCentredString(
        PAGE_WIDTH / 2,
        footer_y + 20,
        "INFORMATION REPORT"
    )

    c.drawCentredString(
        PAGE_WIDTH / 2,
        footer_y,
        f"SO NO: {lr_no} RAJASTHAN POLICE"
    )

    c.save()
    return path,lr_no
