"""
Financial Analyzer Module
Handles: Bank Statements, Invoices, Financial Reports
Powered by Groq AI + Local Pattern Matching
"""

import re, os, json
from datetime import datetime
from collections import defaultdict
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

def groq_call(prompt, max_tokens=2048):
    try:
        r = client.chat.completions.create(model=MODEL, messages=[{"role":"user","content":prompt}], max_tokens=max_tokens, temperature=0.2)
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def safe_json(text):
    try:
        text = re.sub(r'```json\s*','',text); text = re.sub(r'```\s*','',text)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(text.strip())
    except: return None

def extract_transactions_ai(text):
    sample = text[:8000]
    prompt = f"""You are a financial document analyst. Extract ALL transactions from this bank statement.

Return ONLY a valid JSON object:
{{
  "account_holder": "Full name or Unknown",
  "account_number": "Masked like XXXX1234 or Unknown",
  "bank_name": "Bank name or Unknown",
  "account_type": "Savings/Current/Credit/Unknown",
  "currency": "INR/USD/EUR/etc",
  "statement_period": "From date to date or Unknown",
  "opening_balance": 0.00,
  "closing_balance": 0.00,
  "transactions": [
    {{
      "date": "DD/MM/YYYY",
      "description": "Transaction description",
      "amount": 1000.00,
      "type": "Credit",
      "balance": 5000.00,
      "category": "Salary/Food/Bills/Transfer/ATM/Shopping/Medical/Education/Other"
    }}
  ]
}}

Rules: amount must be a number, type must be Credit or Debit exactly, extract every transaction.

Document:
{sample}"""
    return safe_json(groq_call(prompt, max_tokens=3000))

def calculate_stats(transactions):
    if not transactions: return {}
    credits = [t for t in transactions if t.get('type')=='Credit']
    debits  = [t for t in transactions if t.get('type')=='Debit']
    total_cr = sum(t.get('amount',0) for t in credits)
    total_db = sum(t.get('amount',0) for t in debits)

    categories = defaultdict(float)
    for t in debits:
        categories[t.get('category','Other')] += t.get('amount',0)

    monthly = defaultdict(lambda: {'credit':0,'debit':0})
    for t in transactions:
        for fmt in ['%d/%m/%Y','%d-%m-%Y','%Y-%m-%d','%d/%m/%y']:
            try:
                d = datetime.strptime(t.get('date',''), fmt)
                mk = d.strftime('%b %Y')
                monthly[mk]['credit' if t.get('type')=='Credit' else 'debit'] += t.get('amount',0)
                break
            except: continue

    avg_db = total_db/len(debits) if debits else 0
    risk_flags = [{'transaction':t.get('description',''),'amount':t.get('amount',0),'reason':f"Large: {t.get('amount',0):.2f} vs avg {avg_db:.2f}"} for t in debits if t.get('amount',0) > avg_db*3]

    desc_count = defaultdict(int)
    for t in transactions: desc_count[t.get('description','')] += 1
    duplicates = [d for d,c in desc_count.items() if c > 2]

    return {
        'total_transactions': len(transactions),
        'total_credits': len(credits),
        'total_debits': len(debits),
        'total_credit_amount': round(total_cr,2),
        'total_debit_amount': round(total_db,2),
        'net_balance': round(total_cr-total_db,2),
        'avg_credit': round(total_cr/len(credits),2) if credits else 0,
        'avg_debit': round(total_db/len(debits),2) if debits else 0,
        'largest_credit': max((t.get('amount',0) for t in credits), default=0),
        'largest_debit': max((t.get('amount',0) for t in debits), default=0),
        'category_breakdown': dict(categories),
        'monthly_breakdown': {k: dict(v) for k,v in monthly.items()},
        'top_expenses': sorted(debits, key=lambda x: x.get('amount',0), reverse=True)[:5],
        'risk_flags': risk_flags,
        'duplicate_merchants': duplicates[:5],
        'savings_rate': round((total_cr-total_db)/total_cr*100,1) if total_cr>0 else 0
    }

def ai_financial_summary(text, stats):
    prompt = f"""You are a financial advisor. Analyze this financial data and provide insights.

Stats:
- Total Income: {stats.get('total_credit_amount',0)}
- Total Expenses: {stats.get('total_debit_amount',0)}
- Net Balance: {stats.get('net_balance',0)}
- Savings Rate: {stats.get('savings_rate',0)}%
- Transactions: {stats.get('total_transactions',0)}
- Category Breakdown: {json.dumps(stats.get('category_breakdown',{}))}
- Risk Flags: {len(stats.get('risk_flags',[]))}

Return ONLY valid JSON:
{{
  "financial_health": "Good/Fair/Poor",
  "health_score": 75,
  "executive_summary": "2-3 sentence overview",
  "key_insights": ["insight 1","insight 2","insight 3","insight 4"],
  "recommendations": ["rec 1","rec 2","rec 3"],
  "spending_pattern": "spending behavior description",
  "savings_analysis": "savings rate analysis",
  "risk_assessment": "Low/Medium/High",
  "top_concern": "most important concern"
}}"""
    data = safe_json(groq_call(prompt, max_tokens=1000))
    return data or {"financial_health":"Unknown","health_score":0,"executive_summary":"Analysis unavailable","key_insights":[],"recommendations":[],"risk_assessment":"Unknown"}

def analyze_invoice(text):
    prompt = f"""Extract all information from this invoice or bill.

Return ONLY valid JSON:
{{
  "invoice_number": "number or Unknown",
  "invoice_date": "date or Unknown",
  "due_date": "due date or Unknown",
  "vendor_name": "vendor name",
  "customer_name": "customer name or Unknown",
  "line_items": [{{"description":"item","quantity":1,"unit_price":100.00,"total":100.00}}],
  "subtotal": 0.00,
  "tax_amount": 0.00,
  "tax_rate": "18%",
  "discount": 0.00,
  "total_amount": 0.00,
  "currency": "INR",
  "payment_status": "Paid/Unpaid/Pending",
  "payment_method": "Cash/Card/UPI/Bank Transfer/Unknown"
}}

Invoice:
{text[:5000]}"""
    data = safe_json(groq_call(prompt, max_tokens=1500))
    return data or {"error":"Could not parse invoice"}

def analyze_financial_document(text, doc_type="auto"):
    if not text or len(text.strip()) < 30:
        return {"error": "Document too short or empty"}

    tl = text.lower()
    if doc_type == "auto":
        if any(w in tl for w in ['invoice','bill','receipt','gst','tax invoice']):
            doc_type = "invoice"
        elif any(w in tl for w in ['statement','account','balance','transaction','debit','credit']):
            doc_type = "bank_statement"
        else:
            doc_type = "general_financial"

    result = {"document_type": doc_type, "powered_by": "Groq — Llama 3.3 70B"}

    if doc_type == "invoice":
        result["invoice_data"] = analyze_invoice(text)
        result["analysis_type"] = "Invoice Analysis"

    elif doc_type == "bank_statement":
        ai_data = extract_transactions_ai(text)
        if ai_data and ai_data.get('transactions'):
            transactions = ai_data.get('transactions', [])
            result["account_info"] = {
                "account_holder": ai_data.get('account_holder','Unknown'),
                "account_number": ai_data.get('account_number','Unknown'),
                "bank_name": ai_data.get('bank_name','Unknown'),
                "account_type": ai_data.get('account_type','Unknown'),
                "currency": ai_data.get('currency','INR'),
                "statement_period": ai_data.get('statement_period','Unknown'),
                "opening_balance": ai_data.get('opening_balance',0),
                "closing_balance": ai_data.get('closing_balance',0),
            }
        else:
            transactions = []
            result["account_info"] = {"note": "Could not extract transactions"}

        result["transactions"] = transactions
        result["statistics"] = calculate_stats(transactions)
        result["ai_summary"] = ai_financial_summary(text, result["statistics"])
        result["analysis_type"] = "Bank Statement Analysis"
        result["total_transactions_found"] = len(transactions)
    else:
        result["ai_summary"] = groq_call(f"Analyze this financial document and provide key insights in 3-4 sentences:\n\n{text[:3000]}", max_tokens=500)
        result["analysis_type"] = "General Financial Analysis"

    return result
