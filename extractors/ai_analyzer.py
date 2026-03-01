"""
AI Analyzer Module — Powered by Groq API (Free)
...
"""

import os
from groq import Groq
import json
import re
# ── CONFIGURE ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"


def safe_json(text):
    """Extract JSON from response safely"""
    try:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        # Find JSON object in text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text.strip())
    except Exception:
        return None


def groq_call(prompt, max_tokens=2048):
    """Call Groq API and return text response"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"


# ── DOMAIN DETECTION ─────────────────────────────────────────────────────────
def detect_domain(text):
    """Detect document domain: Medical, Legal, Banking, or General"""
    sample = text[:2000]
    prompt = f"""Analyze this document excerpt and classify it into exactly ONE domain.
Return ONLY a JSON object like this:
{{"domain": "Medical", "confidence": 95, "reason": "Contains patient diagnosis and medication"}}

Domains: Medical, Legal, Banking, Academic, Technical, General

Document excerpt:
{sample}"""

    result = groq_call(prompt, max_tokens=200)
    data = safe_json(result)
    if data:
        return data
    return {"domain": "General", "confidence": 50, "reason": "Could not determine domain"}


# ── SMART SUMMARY ─────────────────────────────────────────────────────────────
def smart_summary(text, domain="General"):
    """Generate intelligent AI summary based on domain"""
    sample = text[:6000]

    domain_instructions = {
        "Medical": "Focus on: patient condition, diagnosis, treatment plan, medications, and doctor recommendations.",
        "Legal": "Focus on: parties involved, case type, key arguments, verdict/outcome, and important dates.",
        "Banking": "Focus on: account details, transaction summary, amounts, dates, and any flagged activities.",
        "Academic": "Focus on: research topic, methodology, key findings, and conclusions.",
        "General": "Focus on: main topic, key points, and important conclusions."
    }

    instruction = domain_instructions.get(domain, domain_instructions["General"])

    prompt = f"""You are an expert document analyst. Analyze this {domain} document and provide a structured summary.
{instruction}

Return ONLY a valid JSON object with no extra text:
{{
  "executive_summary": "2-3 sentence overview",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "important_findings": "Most critical finding in one sentence",
  "document_type": "Specific type of document",
  "language": "Language of document",
  "urgency_level": "High/Medium/Low",
  "word_count_estimate": 1000
}}

Document:
{sample}"""

    result = groq_call(prompt, max_tokens=1000)
    data = safe_json(result)
    if data:
        return data
    return {
        "executive_summary": result[:500] if result else "Summary unavailable",
        "key_points": [],
        "important_findings": "",
        "document_type": "Unknown",
        "language": "English",
        "urgency_level": "Medium"
    }


# ── MEDICAL ANALYZER ──────────────────────────────────────────────────────────
def analyze_medical(text):
    """Extract structured medical information"""
    sample = text[:6000]
    prompt = f"""You are a medical document analyst. Extract all medical information from this document.

Return ONLY a valid JSON object:
{{
  "patient": {{
    "name": "Patient name or Unknown",
    "age": "Age or Unknown",
    "gender": "Gender or Unknown",
    "id": "Patient ID or Unknown"
  }},
  "diagnosis": ["diagnosis 1", "diagnosis 2"],
  "symptoms": ["symptom 1", "symptom 2"],
  "medications": [
    {{"name": "Drug name", "dosage": "dosage", "frequency": "frequency"}}
  ],
  "lab_results": [
    {{"test": "test name", "value": "value", "normal_range": "range", "status": "Normal/Abnormal"}}
  ],
  "doctor": "Doctor name or Unknown",
  "hospital": "Hospital name or Unknown",
  "date": "Report date or Unknown",
  "follow_up": "Follow up instructions or None",
  "severity": "Critical/Serious/Moderate/Mild",
  "summary": "One sentence medical summary"
}}

Medical Document:
{sample}"""

    result = groq_call(prompt, max_tokens=1500)
    data = safe_json(result)
    if data:
        return data
    return {"error": "Could not parse medical data", "raw": result[:500]}


# ── LEGAL ANALYZER ────────────────────────────────────────────────────────────
def analyze_legal(text):
    """Extract structured legal information"""
    sample = text[:6000]
    prompt = f"""You are a legal document analyst. Extract all legal information from this document.

Return ONLY a valid JSON object:
{{
  "case_number": "Case number or Unknown",
  "case_type": "Criminal/Civil/Family/Corporate/Unknown",
  "court": "Court name or Unknown",
  "judge": "Judge name or Unknown",
  "date_filed": "Date or Unknown",
  "date_decided": "Date or Unknown",
  "plaintiff": "Plaintiff name or Unknown",
  "defendant": "Defendant name or Unknown",
  "lawyers": ["lawyer 1", "lawyer 2"],
  "charges": ["charge 1", "charge 2"],
  "verdict": "Verdict or Pending",
  "sentence": "Sentence or N/A",
  "key_arguments": ["argument 1", "argument 2"],
  "cited_laws": ["law 1", "law 2"],
  "outcome": "Brief outcome description",
  "summary": "One sentence legal summary"
}}

Legal Document:
{sample}"""

    result = groq_call(prompt, max_tokens=1500)
    data = safe_json(result)
    if data:
        return data
    return {"error": "Could not parse legal data", "raw": result[:500]}


# ── BANKING ANALYZER ──────────────────────────────────────────────────────────
def analyze_banking(text):
    """Extract structured banking/financial information"""
    sample = text[:6000]
    prompt = f"""You are a financial document analyst. Extract all banking and financial information.

Return ONLY a valid JSON object:
{{
  "account_holder": "Name or Unknown",
  "account_number": "Masked number or Unknown",
  "bank_name": "Bank name or Unknown",
  "account_type": "Savings/Current/Unknown",
  "period": "Statement period or Unknown",
  "opening_balance": "Amount or Unknown",
  "closing_balance": "Amount or Unknown",
  "total_credits": "Total amount credited",
  "total_debits": "Total amount debited",
  "transactions": [
    {{"date": "date", "description": "desc", "amount": "amount", "type": "Credit/Debit"}}
  ],
  "large_transactions": [
    {{"date": "date", "description": "desc", "amount": "amount", "flag": "reason"}}
  ],
  "currency": "Currency code",
  "summary": "One sentence financial summary",
  "risk_flags": ["flag 1", "flag 2"]
}}

Financial Document:
{sample}"""

    result = groq_call(prompt, max_tokens=2000)
    data = safe_json(result)
    if data:
        return data
    return {"error": "Could not parse banking data", "raw": result[:500]}


# ── DOCUMENT Q&A ──────────────────────────────────────────────────────────────
def ask_document(text, question):
    """Answer a question about the document"""
    sample = text[:8000]
    prompt = f"""You are a document analyst. Answer the following question based ONLY on the document provided.
If the answer is not in the document, say "This information is not found in the document."
Be concise and accurate.

Question: {question}

Document:
{sample}

Answer:"""

    return groq_call(prompt, max_tokens=500)


# ── FULL AI ANALYSIS ──────────────────────────────────────────────────────────
def full_analysis(text):
    """Run complete AI analysis pipeline on a document"""
    if not text or len(text.strip()) < 50:
        return {"error": "Document too short or empty for analysis"}

    # Step 1: Detect domain
    domain_info = detect_domain(text)
    domain = domain_info.get("domain", "General")

    # Step 2: Smart summary
    summary_info = smart_summary(text, domain)

    # Step 3: Domain-specific analysis
    domain_analysis = {}
    if domain == "Medical":
        domain_analysis = analyze_medical(text)
    elif domain == "Legal":
        domain_analysis = analyze_legal(text)
    elif domain == "Banking":
        domain_analysis = analyze_banking(text)

    return {
        "domain": domain_info,
        "summary": summary_info,
        "domain_analysis": domain_analysis,
        "powered_by": "Groq — Llama 3.3 70B"
    }
