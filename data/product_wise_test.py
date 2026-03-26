import sys
import os
import re
import json
from unittest.mock import MagicMock

# Mock web and LLM modules to avoid ImportErrors and side effects
sys.modules["flask"] = MagicMock()
sys.modules["flask_cors"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()

# Add the parent directory to sys.path to import sementic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sementic
# Mock the rewriter to return the input string
sementic.rewrite_query_with_llm = lambda x: x

def run_test_case(query):
    """
    Simulates the FULL logic in sementic.predict()
    """
    raw_q = query
    q = sementic.rewrite_query_with_llm(raw_q)
    
    # Fallback expansions
    q_lower = q.lower()
    if re.search(r'\bec\b', q_lower) and not any(x in q_lower for x in ["economic census", "ec4", "ec5", "ec6"]):
        q = q + " Economic Census"
    if re.search(r'\bwpi\b', q_lower) and not any(x in q_lower for x in ["wholesale price", "wholesale price index"]):
        q = q + " Wholesale Price Index"
    # ... other expansions from predict() ...

    top_results = sementic.search_indicators(q)

    # Force-include Logic (Mirrored from predict)
    # WPI
    _wpi_like = re.search(r'\bwpi\b', raw_q.lower()) or ("wholesale" in raw_q.lower() and "price" in raw_q.lower())
    if _wpi_like and not any(r["parent"] == "WPI" for r in top_results):
        wpi_best = sementic._search_wpi_only(q or raw_q)
        if wpi_best:
            top_results = [wpi_best] + [r for r in top_results if r["parent"] != "WPI"][:2]
            top_results[0]["score"] = 9.9 # Boost

    # Forced Dataset names
    _raw_lower = raw_q.lower().strip()
    _force_ds = None
    if re.search(r'\btus\b', _raw_lower) or "time use" in _raw_lower:
        _force_ds = ["TUS"]
    elif re.search(r'\bplfs\b', _raw_lower) or "lfpr" in _raw_lower:
        _force_ds = ["PLFS"]
    elif re.search(r'\bcpi\b', _raw_lower):
        _force_ds = ["CPI", "CPI2"]
    elif re.search(r'\biip\b', _raw_lower):
        _force_ds = ["IIP"]
        
    if _force_ds and not any(r["parent"] in _force_ds for r in top_results):
        ds_best = sementic._search_dataset_only(q or raw_q, _force_ds)
        if ds_best:
            top_results = [ds_best] + [r for r in top_results if r["parent"] not in _force_ds][:2]
            top_results[0]["score"] = 9.9
            
    # Priority Order (Simplified for test)
    if _force_ds:
        for i, r in enumerate(top_results):
            if r["parent"] in _force_ds:
                if i > 0:
                    top_results = [r] + [x for x in top_results if x["parent"] != r["parent"]][:2]
                break

    if not top_results: return None
    
    best_ind = top_results[0]
    confidences = sementic.normalize_confidence([r["score"] for r in top_results])
    
    # Filter selection
    related_filters = [f for f in sementic.FILTERS if f["parent"] == best_ind["code"]]
    grouped = {}
    for f in related_filters:
        grouped.setdefault(f["filter_name"], []).append(f)

    best_filters = []
    for fname, opts in grouped.items():
        best_opt = sementic.select_best_filter_option(q, fname, opts, sementic.cross_encoder)
        best_filters.append({"filter_name": fname, "option": best_opt["option"]})
    
    best_filters = sementic.ensure_required_filters_present(best_filters, best_ind["parent"], grouped, q, sementic.cross_encoder)
    
    return {
        "dataset": best_ind["parent"],
        "indicator": best_ind["name"],
        "filters": {f["filter_name"]: f["option"] for f in best_filters},
        "confidence": confidences[0]
    }

def main():
    test_cases = [
        {
            "name": "CPI Rural Index",
            "query": "CPI Rural General Index 2024",
            "expected": {
                "dataset": "CPI",
                "indicator": "General Index / Division",
                "filters": ["Division", "Base_Year", "Series"]
            }
        },
        {
            "name": "IIP Monthly Manufacturing",
            "query": "Monthly IIP for Manufacturing sector in 2023",
            "expected": {
                "dataset": "IIP",
                "indicator": "Monthly",
                "filters": ["Frequency", "Type", "Category"]
            }
        },
        {
            "name": "TUS Average Time",
            "query": "TUS 2019 Average time spent per person ICATUS male 15-29",
            "expected": {
                "dataset": "TUS",
                "indicator": "Percentage of persons and minutes spent in a day on an average per person /per participant in unpaid activities",
                "filters": ["Age Group", "Gender", "ICATUS Activity"]
            }
        },
        {
            "name": "WPI Rubber Tube",
            "query": "WPI of rubber tube in 2022",
            "expected": {
                "dataset": "WPI",
                "indicator": "rubber tube",
                "filters": ["Major Group", "Sub Group", "Year"]
            }
        },
        {
            "name": "ESI Energy Balance",
            "query": "ESI Energy Balance Coal 2023",
            "expected": {
                "dataset": "ESI",
                "indicator": "Energy Balance",
                "filters": ["Energy Commodities", "Use of Energy Balance"]
            }
        },
        {
            "name": "PLFS LFPR",
            "query": "LFPR 15-29 years 2023-24",
            "expected": {
                "dataset": "PLFS",
                "indicator": "LFPR",
                "filters": ["Age Group", "Year"]
            }
        },
        {
            "name": "NAS GVA",
            "query": "Gross Value Added 2022-23",
            "expected": {
                "dataset": "NAS",
                "indicator": "Gross Value Added",
                "filters": ["Base_Year", "Year"]
            }
        }
    ]

    print(f"{'TEST NAME':<25} | {'DS':<5} | {'IND':<5} | {'FILTERS':<5} | {'RESULT'}")
    print("-" * 80)
    
    for tc in test_cases:
        res = run_test_case(tc["query"])
        if not res:
            print(f"{tc['name']:<25} | FAIL (No results)")
            continue
            
        ds_ok = res["dataset"] == tc["expected"]["dataset"]
        ind_ok = tc["expected"]["indicator"].lower() in res["indicator"].lower()
        missing_f = [f for f in tc["expected"]["filters"] if f not in res["filters"]]
        f_ok = len(missing_f) == 0
        
        status = "PASS" if (ds_ok and ind_ok and f_ok) else "FAIL"
        print(f"{tc['name']:<25} | {'OK' if ds_ok else 'ERR'} | {'OK' if ind_ok else 'ERR'} | {'OK' if f_ok else 'ERR'} | {status}")
        if not ds_ok: print(f"  Got DS: {res['dataset']}, Expected: {tc['expected']['dataset']}")
        if not ind_ok: print(f"  Got IND: {res['indicator']}")
        if missing_f: print(f"  Missing filters: {missing_f}. Got: {list(res['filters'].keys())}")

if __name__ == "__main__":
    main()
