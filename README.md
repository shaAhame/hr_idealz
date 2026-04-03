# iDealz Payslip Generator — Vercel Deployment Guide

## Project Structure

```
idealz-payslip/
├── vercel.json          ← routing config
├── requirements.txt     ← Python packages (auto-installed by Vercel)
├── api/
│   ├── employees.py     ← POST /api/employees  (reads payroll, returns employee list)
│   └── generate.py      ← POST /api/generate   (generates all PDFs → ZIP download)
└── public/
    └── index.html       ← the web app UI
```

---

## Deploy to Vercel (One Time Setup)

### Step 1 — Create a GitHub repo
1. Go to [github.com](https://github.com) → **New repository**
2. Name it `idealz-payslip`
3. Upload all files from this folder into the repo (keep the folder structure exactly)

### Step 2 — Deploy to Vercel
1. Go to [vercel.com](https://vercel.com) and sign up (free)
2. Click **"Add New Project"**
3. Import your GitHub repo `idealz-payslip`
4. Vercel auto-detects the Python functions — click **Deploy**
5. Done! Your app is live at `https://idealz-payslip.vercel.app`

### Step 3 — Share with HR
- Send the URL to your KHR team
- No installation needed — works in any browser, on any device
- Upload Excel → click Generate → ZIP downloads automatically

---

## How HR Uses It Every Month

1. Open the URL in any browser
2. Upload the updated `PAYROLL_SHEET.xlsx`
3. Set the pay period (e.g. `APR 2026`)
4. Click **Generate & Download All PDFs**
5. Extract the ZIP — one PDF per employee — ready to send

---

## Vercel Free Plan Limits

| Limit | Free Tier | Your Usage |
|---|---|---|
| Serverless function timeout | 10 seconds | ~3-4 sec for 30 employees ✓ |
| Bandwidth | 100 GB/month | ~1 MB per run ✓ |
| Deployments | Unlimited | ✓ |
| Custom domain | Yes | Optional |

---

## Custom Domain (Optional)

In Vercel dashboard → **Settings → Domains** → add `payslip.idealz.lk`
Requires a DNS CNAME record at your domain registrar.

---

*iDealz Lanka (Pvt) Ltd — HR Systems*
