from http.server import BaseHTTPRequestHandler
import pandas as pd
import io, json, math, zipfile

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# ── Constants ────────────────────────────────────────────────────────────────
EPF_EMP = 0.08
EPF_ER  = 0.12
ETF_ER  = 0.03

# ── Helpers ──────────────────────────────────────────────────────────────────

def safe(val, default=0):
    if val is None: return default
    try:
        if isinstance(val, float) and math.isnan(val): return default
        return float(val)
    except: return default

def safe_str(val, default=''):
    if val is None: return default
    try:
        if isinstance(val, float) and math.isnan(val): return default
    except: pass
    return str(val).strip()

def lkr(val):
    return '-' if val == 0 else f"LKR {val:,.2f}"

def load_payroll(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), header=[0, 1])
    df.columns = [
        'epf_no','name','department','designation','date_of_join',
        'basic_salary','bra2','bra1','allowance','total_basic_earning',
        'accessories_commission','daily_commission','pre_owned_commission',
        'additional_working_days','salary_adjustment','total_income',
        'working_days','no_pay_leaves','no_pay_deduction',
        'late_attendance','epf_employee_8','per_day_comm_advance',
        'pre_owned_comm_advance','salary_advance','salary_deduction',
        'total_deduction','net_salary','epf_employer_12',
        'etf_employer_3','total_cost'
    ]
    df = df[df['name'].apply(lambda x: isinstance(x, str) and len(str(x).strip()) > 2)]
    df = df[df['designation'].apply(lambda x: isinstance(x, str) and len(str(x).strip()) > 2)]
    return df.reset_index(drop=True)

def parse_multipart(content_type, body_bytes):
    boundary = None
    for part in content_type.split(';'):
        p = part.strip()
        if p.startswith('boundary='):
            boundary = p[9:].strip('"').strip(); break
    if not boundary:
        return {}, {}
    fields, files = {}, {}
    sep = ('--' + boundary).encode()
    for chunk in body_bytes.split(sep)[1:]:
        if chunk.strip() in (b'--', b'--\r\n', b''): continue
        if b'\r\n\r\n' not in chunk: continue
        hdr_raw, value = chunk.split(b'\r\n\r\n', 1)
        value = value.rstrip(b'\r\n')
        name = filename = None
        for line in hdr_raw.decode('utf-8', errors='replace').split('\r\n'):
            if 'Content-Disposition' in line:
                for item in line.split(';'):
                    item = item.strip()
                    if item.startswith('name='): name = item[5:].strip('"')
                    elif item.startswith('filename='): filename = item[9:].strip('"')
        if name:
            if filename: files[name] = value
            else: fields[name] = value.decode('utf-8', errors='replace')
    return fields, files

# ── PDF generation ────────────────────────────────────────────────────────────

def draw_payslip_pdf(emp, pay_period):
    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)

    DARK   = colors.HexColor('#1a1a2e')
    ACCENT = colors.HexColor('#0f4c75')
    LIGHT  = colors.HexColor('#f0f4f8')
    MID    = colors.HexColor('#dbe4ee')
    GREEN  = colors.HexColor('#1b7a4e')
    RED    = colors.HexColor('#c0392b')
    WHITE  = colors.white
    GRAY   = colors.HexColor('#6b7280')
    SKY    = colors.HexColor('#7ec8e3')

    m  = 18 * mm
    cw = W - 2 * m

    # Header
    c.setFillColor(DARK);  c.rect(0, H-38*mm, W, 38*mm, fill=1, stroke=0)
    c.setFillColor(ACCENT);c.rect(0, H-42*mm, W,  5*mm, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 16); c.setFillColor(WHITE)
    c.drawString(m, H-15*mm, 'iDealz Lanka (Pvt) Ltd')
    c.setFont('Helvetica', 9); c.setFillColor(colors.HexColor('#a0b4c8'))
    c.drawString(m, H-22*mm, 'No. 86, Galle Road, Colombo 04   |   0777 243 243   |   hr@idealz.lk')
    c.setFont('Helvetica-Bold', 11); c.setFillColor(SKY)
    c.drawRightString(W-m, H-15*mm, 'SALARY PAYSLIP')
    c.setFont('Helvetica', 9); c.setFillColor(colors.HexColor('#a0b4c8'))
    c.drawRightString(W-m, H-22*mm, pay_period.upper())

    # Employee card
    iy = H - 56*mm
    c.setFillColor(LIGHT); c.roundRect(m, iy-18*mm, cw, 21*mm, 3*mm, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 12); c.setFillColor(DARK)
    c.drawString(m+5*mm, iy-5*mm, safe_str(emp.get('name'), 'N/A').upper())
    c.setFont('Helvetica', 8); c.setFillColor(GRAY)
    c.drawString(m+5*mm, iy-10*mm, safe_str(emp.get('designation'), '-').upper())
    c.drawString(m+5*mm, iy-15*mm, safe_str(emp.get('department'), '-').upper())
    c.setFont('Helvetica-Bold', 8); c.setFillColor(ACCENT)
    c.drawRightString(W-m-5*mm, iy-5*mm, f"EPF No: {safe_str(emp.get('epf_no'), '-')}")
    c.setFont('Helvetica', 8); c.setFillColor(GRAY)
    c.drawRightString(W-m-5*mm, iy-11*mm, f'Pay Period: {pay_period.upper()}')

    half = cw / 2 - 3*mm
    ty   = iy - 25*mm
    RH, HH = 7*mm, 8*mm

    def hdr(x, y, w, t):
        c.setFillColor(ACCENT); c.rect(x, y, w, HH, fill=1, stroke=0)
        c.setFont('Helvetica-Bold', 9); c.setFillColor(WHITE)
        c.drawString(x+4*mm, y+2.5*mm, t)
        c.drawRightString(x+w-4*mm, y+2.5*mm, 'AMOUNT (LKR)')

    def row(x, y, w, lbl, val, bold=False, alt=False, vc=None):
        if alt: c.setFillColor(LIGHT); c.rect(x, y, w, RH, fill=1, stroke=0)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', 8); c.setFillColor(DARK)
        c.drawString(x+4*mm, y+2.2*mm, lbl)
        c.setFillColor(vc or (DARK if bold else GREEN))
        c.drawRightString(x+w-4*mm, y+2.2*mm, lkr(val))

    def tot(x, y, w, lbl, val, vc=None):
        c.setFillColor(MID); c.rect(x, y, w, RH, fill=1, stroke=0)
        c.setFont('Helvetica-Bold', 9); c.setFillColor(DARK)
        c.drawString(x+4*mm, y+2.2*mm, lbl)
        c.setFillColor(vc or DARK); c.drawRightString(x+w-4*mm, y+2.2*mm, lkr(val))

    # Earnings
    # Total Basic Earning = Basic + BRA2 + BRA1 + Allowance
    # Total Income = Total Basic Earning + Accessories Commission
    #              + Daily Commission + Pre Owned Commission
    #              + Additional Working Days + Salary Adjustment
    basic  = safe(emp.get('basic_salary'))
    bra2   = safe(emp.get('bra2'))
    bra1   = safe(emp.get('bra1'))
    allow  = safe(emp.get('allowance'))
    tb     = basic + bra2 + bra1 + allow        # Total Basic Earning

    ac     = safe(emp.get('accessories_commission'))
    dc     = safe(emp.get('daily_commission'))
    po     = safe(emp.get('pre_owned_commission'))
    aw     = safe(emp.get('additional_working_days'))
    sa_adj = safe(emp.get('salary_adjustment'))
    te     = tb + ac + dc + po + aw + sa_adj    # Total Income

    hdr(m, ty, half, 'EARNINGS')
    r = ty - RH
    for lbl, v, b, a in [
        ('Basic Salary',             basic,  False, False),
        ('BRA 2 (Act 2016)',         bra2,   False, True),
        ('BRA 1 (Act 2005)',         bra1,   False, False),
        ('Allowance',                allow,  False, True),
        ('Total Basic Earning',      tb,     True,  False),
        ('Accessories Commission',   ac,     False, True),
        ('Daily Commission',         dc,     False, False),
        ('Pre Owned Commission',     po,     False, True),
        ('Additional Working Days',  aw,     False, False),
        ('Salary Adjustment',        sa_adj, False, True),
    ]:
        row(m, r, half, lbl, v, b, a); r -= RH
    tot(m, r, half, 'TOTAL INCOME', te, GREEN)
    eb = r

    # Deductions — read directly from payroll sheet, no auto-calculation
    # If HR leaves EPF/ETF blank or 0 for new employees, it simply shows as 0
    epf8 = safe(emp.get('epf_employee_8'))        # Employee EPF 8% — from sheet
    np_d = safe(emp.get('no_pay_deduction'))
    la   = safe(emp.get('late_attendance'))
    lr   = safe(emp.get('salary_deduction'))
    sa   = safe(emp.get('salary_advance'))
    pd_adv = safe(emp.get('per_day_comm_advance'))
    po_adv = safe(emp.get('pre_owned_comm_advance'))
    td   = epf8 + np_d + la + lr + sa + pd_adv + po_adv

    dx = m + half + 6*mm
    hdr(dx, ty, half, 'DEDUCTIONS')
    r2 = ty - RH
    for lbl, v, b, a in [
        ('EPF 8% (Employee)',        epf8,   True,  False),
        ('No Pay Deduction',         np_d,   False, True),
        ('Late Arrivals',            la,     False, False),
        ('Loan Repayment',           lr,     False, True),
        ('Salary Advance',           sa,     False, False),
        ('Per Day Comm. Advance',    pd_adv, False, True),
        ('Pre Owned Comm. Advance',  po_adv, False, False),
    ]:
        row(dx, r2, half, lbl, v, b, a, vc=RED if v > 0 else GRAY); r2 -= RH
    tot(dx, r2, half, 'TOTAL DEDUCTIONS', td, RED)

    # Net Pay
    ny  = min(eb, r2) - 12*mm
    net = te - td
    c.setFillColor(DARK); c.roundRect(m, ny, cw, 14*mm, 3*mm, fill=1, stroke=0)
    c.setFont('Helvetica', 10); c.setFillColor(SKY)
    c.drawString(m+8*mm, ny+5.5*mm, 'NET PAY')
    c.setFont('Helvetica-Bold', 16); c.setFillColor(WHITE)
    c.drawRightString(W-m-8*mm, ny+4.5*mm, f'LKR {net:,.2f}')

    # Employer contributions — read directly from sheet, 0 if not applicable
    epf_er = safe(emp.get('epf_employer_12'))     # Employer EPF 12% — from sheet
    etf_er = safe(emp.get('etf_employer_3'))       # Employer ETF 3%  — from sheet
    ey2 = ny - 14*mm
    c.setFillColor(LIGHT); c.roundRect(m, ey2, cw, 12*mm, 3*mm, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 8); c.setFillColor(ACCENT)
    c.drawString(m+5*mm, ey2+7.5*mm, 'EMPLOYER CONTRIBUTIONS  (not deducted from employee)')
    c.setFont('Helvetica', 8); c.setFillColor(DARK)
    if epf_er == 0 and etf_er == 0:
        c.drawString(m+5*mm, ey2+2.5*mm, 'Not applicable for this employee')
    else:
        c.drawString(m+5*mm, ey2+2.5*mm,
            f'EPF 12%: LKR {epf_er:,.2f}   |   ETF 3%: LKR {etf_er:,.2f}')

    # Footer
    c.setFillColor(ACCENT); c.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    c.setFont('Helvetica', 7); c.setFillColor(WHITE)
    c.drawCentredString(W/2, 2.5*mm, 'This is a system generated payslip   |   iDealz Lanka (Pvt) Ltd')

    c.save(); buf.seek(0)
    return buf.read()

# ── Vercel handler ────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors(); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        ct     = self.headers.get('Content-Type', '')
        fields, files = parse_multipart(ct, body)

        try:
            file_bytes = files.get('payroll')
            if file_bytes is None:
                return self._json(400, {'error': 'No payroll file uploaded'})

            period = fields.get('period', 'MAR 2026').strip() or 'MAR 2026'
            df     = load_payroll(file_bytes)

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for _, emp in df.iterrows():
                    name = safe_str(emp.get('name', ''))
                    if not name: continue
                    pdf_bytes = draw_payslip_pdf(emp, period)
                    safe_name = name.replace(' ', '_').replace('/', '-')
                    zf.writestr(
                        f"Payslip_{safe_name}_{period.replace(' ', '_')}.pdf",
                        pdf_bytes
                    )

            zip_buf.seek(0)
            data  = zip_buf.read()
            fname = f"iDealz_Payslips_{period.replace(' ', '_')}.zip"

            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self._json(500, {'error': str(e)})

    def _json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *args): pass
