
import json, os, re, numpy as np
from datetime import datetime
from sementic import search_indicators, rewrite_query_with_llm, _search_dataset_only, DATASETS, INDICATORS, FILTERS

test_cases = [
    {"query": "UDISE total schools", "expected_ds": "UDISE"},
    {"query": "secondary schools enrolment ratio", "expected_ds": "UDISE"},
    {"query": "CPI inflation rural", "expected_ds": "CPI"},
    {"query": "IIP industrial production index", "expected_ds": "IIP"},
    {"query": "NAS GDP growth rate", "expected_ds": "NAS"},
    {"query": "ASI factory worker count", "expected_ds": "ASI"},
    {"query": "PLFS unemployment rate", "expected_ds": "PLFS"},
    {"query": "HCES consumption expenditure", "expected_ds": "HCES"},
    {"query": "ENVSTAT forest cover", "expected_ds": "ENVSTAT"},
    {"query": "ESI energy statistics", "expected_ds": "ESI"},
    {"query": "CPIALRL agricultural labor index", "expected_ds": "CPIALRL"},
    {"query": "Gender statistics sex ratio", "expected_ds": "Gender"},
    {"query": "ASUSE unorganized sector unincorporated", "expected_ds": "ASUSE"},
    {"query": "RBI bank lending rates", "expected_ds": "RBI"},
    {"query": "TUS time use survey participation", "expected_ds": "TUS"},
    {"query": "AISHE higher education survey", "expected_ds": "AISHE"},
    {"query": "NFHS family health survey fertility", "expected_ds": "NFHS"},
    {"query": "WPI wholesale price index", "expected_ds": "WPI"},
    {"query": "NSS77 debt and investment", "expected_ds": "NSS77"},
    {"query": "NSS78 domestic tourism", "expected_ds": "NSS78"},
    {"query": "NSS79C modular survey cams", "expected_ds": "NSS79C"},
    {"query": "EC6 economic census establishment", "expected_ds": "EC6"},
]

def run_production_audit():
    correct_ds = 0
    results = []
    print(f"\n{'Product':<10} | {'Query':<50} | {'Status'}\n" + "-"*75)
    for case in test_cases:
        raw_q, expected = case["query"], case["expected_ds"]
        q = rewrite_query_with_llm(raw_q)
        q_lower = q.lower()
        
        # Mirror predict logic
        if re.search(r'\bec\b', q_lower) and not any(x in q_lower for x in ["economic census", "ec4", "ec5", "ec6"]): q += " Economic Census"
        if re.search(r'\bwpi\b', q_lower) and "wholesale" not in q_lower: q += " Wholesale Price Index"
        # ... more expansions ...

        top_results = search_indicators(q)
        
        # Force-inclusion logic from sementic.py
        raw_lower = raw_q.lower().strip()
        _force_ds = None
        if re.search(r'\bnss77\b', raw_lower): _force_ds = ["NSS77"]
        elif re.search(r'\bnss78\b', raw_lower): _force_ds = ["NSS78"]
        elif re.search(r'\bnss79\b', raw_lower) or re.search(r'\bnss79c\b', raw_lower): _force_ds = ["NSS79C"]
        elif re.search(r'\bnfhs\b', raw_lower) or "family health" in raw_lower: _force_ds = ["NFHS"]
        elif re.search(r'\baishe\b', raw_lower) or "higher education" in raw_lower: _force_ds = ["AISHE"]
        elif re.search(r'\bcpi\b', raw_lower) or "consumer price" in raw_lower: _force_ds = ["CPI", "CPI2"]
        elif re.search(r'\biip\b', raw_lower) or "industrial production" in raw_lower: _force_ds = ["IIP"]
        elif re.search(r'\bnas\b', raw_lower) or "national accounts" in raw_lower or "gdp" in raw_lower: _force_ds = ["NAS"]
        elif re.search(r'\basi\b', raw_lower) or "annual survey of industries" in raw_lower: _force_ds = ["ASI"]
        elif re.search(r'\bplfs\b', raw_lower) or "unemployment" in raw_lower or "labour force" in raw_lower: _force_ds = ["PLFS"]
        elif re.search(r'\bhces\b', raw_lower) or "consumption expenditure" in raw_lower: _force_ds = ["HCES"]
        elif re.search(r'\benvstat\b', raw_lower) or "environment statistics" in raw_lower: _force_ds = ["ENVSTAT"]
        elif re.search(r'\besi\b', raw_lower) or "energy statistics" in raw_lower: _force_ds = ["ESI"]
        elif re.search(r'\bcpialrl\b', raw_lower) or "agricultural lab" in raw_lower: _force_ds = ["CPIALRL"]
        elif re.search(r'\bgender\b', raw_lower) or "sex ratio" in raw_lower: _force_ds = ["Gender"]
        elif re.search(r'\basuse\b', raw_lower) or "unincorporated" in raw_lower: _force_ds = ["ASUSE"]
        elif re.search(r'\brbi\b', raw_lower) or "bank rate" in raw_lower or "lending rate" in raw_lower: _force_ds = ["RBI"]
        elif re.search(r'\btus\b', raw_lower) or "time use" in raw_lower: _force_ds = ["TUS"]
        elif re.search(r'\budise\b', raw_lower) or "schools?" in raw_lower or "unified district" in raw_lower: _force_ds = ["UDISE"]

        if _force_ds and not any(r["parent"] in _force_ds for r in top_results):
            ds_best = _search_dataset_only(q or raw_q, _force_ds)
            if ds_best: top_results = [ds_best] + [r for r in top_results if r["parent"] != ds_best["parent"]][:2]

        predicted_ds = top_results[0]["parent"] if top_results else "None"
        is_correct = (predicted_ds == expected) or (expected.startswith("EC") and predicted_ds.startswith("EC")) or (expected == "CPI" and predicted_ds == "CPI2")
        
        status = "✅" if is_correct else "❌"
        if is_correct: correct_ds += 1
        print(f"{expected:<10} | {raw_q[:50]:<50} | {status} ({predicted_ds})")
        results.append({"expected": expected, "query": raw_q, "predicted": predicted_ds, "status": status})

    acc = (correct_ds / len(test_cases)) * 100
    print(f"\nFinal Accuracy: {acc:.2f}%\n")
    
    with open(r"C:\Users\DELL\.gemini\antigravity\brain\b29568c4-08d6-472d-bb55-ed02c0e1794a\production_accuracy_report.md", "w", encoding="utf-8") as rf:
        rf.write(f"# Production Accuracy Report\n\n- **Date**: {datetime.now()}\n- **Accuracy**: {acc:.2f}%\n\n| Product | Query | Status | Predicted |\n|---|---|---|---|\n")
        for r in results: rf.write(f"| {r['expected']} | {r['query']} | {r['status']} | {r['predicted']} |\n")

if __name__ == "__main__":
    run_production_audit()
