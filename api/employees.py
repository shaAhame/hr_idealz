from http.server import BaseHTTPRequestHandler
import pandas as pd
import io, json, math

# ── Helpers ──────────────────────────────────────────────────────────────────

def safe_str(val, default=''):
    if val is None: return default
    try:
        if isinstance(val, float) and math.isnan(val): return default
    except: pass
    return str(val).strip()

def load_payroll(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), header=[0, 1])
    # ── Column mapping (A→AI) ─────────────────────────────────────────────
    # A   EPF NO
    # B   Name
    # C   Department
    # D   Designation
    # E   Date of Join
    # F   Basic Salary
    # G   BRA 2 (Act 2016)
    # H   BRA 1 (Act 2005)
    # I   Allowance
    # J   Total Basic Earning
    # K   Total Accessories Commission
    # L   Daily Commission
    # M   Repair Commission
    # N   Company Commission
    # O   Pre Owned Commission
    # P   Additional Working Days
    # Q   Salary Adjustment
    # R   Total Income
    # S   Number of Working Days
    # T   No Pay Leaves
    # U   No Pay Deduction
    # V   Late Attendance
    # W   Employee Contribution (EPF 8%)
    # X   Per Day Commission Advance
    # Y   Repair Commission Advance
    # Z   Company Commission Advance
    # AA  Pre Owned Commission Advance
    # AB  Salary Advance
    # AC  Loan Repayment
    # AD  Salary Deduction
    # AE  Total Deduction
    # AF  Net Salary
    # AG  Employer Contribution (EPF 12%)
    # AH  ETF 3%
    # AI  Total Cost
    df.columns = [
        'epf_no','name','department','designation','date_of_join',
        'basic_salary','bra2','bra1','allowance','total_basic_earning',
        'accessories_commission','daily_commission',
        'repair_commission','company_commission',
        'pre_owned_commission','additional_working_days','salary_adjustment','total_income',
        'working_days','no_pay_leaves','no_pay_deduction',
        'late_attendance','epf_employee_8',
        'per_day_comm_advance',
        'repair_comm_advance','company_comm_advance',
        'pre_owned_comm_advance','salary_advance','loan_repayment','salary_deduction',
        'total_deduction','net_salary',
        'epf_employer_12','etf_employer_3','total_cost'
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

# ── Vercel handler ────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors(); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        ct     = self.headers.get('Content-Type', '')
        _, files = parse_multipart(ct, body)

        try:
            file_bytes = files.get('payroll')
            if file_bytes is None:
                return self._json(400, {'error': 'No payroll file uploaded'})
            df    = load_payroll(file_bytes)
            names = [safe_str(r.get('name', '')) for _, r in df.iterrows()]
            names = [n for n in names if n]
            depts = list(set([safe_str(r.get('department', '')) for _, r in df.iterrows() if safe_str(r.get('department', ''))]))
            self._json(200, {'count': len(names), 'names': names, 'departments': depts})
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
