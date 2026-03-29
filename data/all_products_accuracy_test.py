import sys
import os
import re
import json
import csv
import numpy as np
import difflib
from unittest.mock import MagicMock

# 1. Mock problematic modules to ensure script runs in any environment
sys.modules["flask"] = MagicMock()
sys.modules["flask_cors"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()

# 2. Add root directory to path to import sementic
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

import sementic

# 3. Suppress LLM rewriting to isolate semantic search performance
sementic.rewrite_query_with_llm = lambda x: x

def get_mandatory_filters_for_indicator(ind_code):
    """Returns the names of the 4 mandatory filters (Year, Sector, Gender, State) actually present for an indicator."""
    ind_filters = [f for f in sementic.FILTERS if f["parent"] == ind_code]
    found = set()
    for f in ind_filters:
        if f["filter_name"].lower() in ["year", "sector", "gender", "state", "state/ut"]:
            found.add(f["filter_name"])
    return found

def evaluate_accuracy():
    results = []
    total = len(sementic.INDICATORS)
    print(f"[INFO] Starting accuracy audit for {total} indicators...")

    for i, ind in enumerate(sementic.INDICATORS):
        # Progress log
        if i % 100 == 0:
            print(f"[PROGRESS] Evaluated {i}/{total} indicators...")

        actual_ds = ind["parent"]
        ind_name = ind["name"]
        ind_code = ind["code"]
        
        # Generate synthetic query: "Indicator Name DatasetCode"
        query = f"{ind_name} {actual_ds}"
        
        # Full prediction logic replication (simplified but accurate to sementic.py)
        raw_q = query
        q = raw_q # mock rewrite
        
        # Priority mapping from predict() — MUST MIRROR sementic.py predict() exactly
        _raw_lower = raw_q.lower().strip()
        _force_ds = None
        # Specific codes first (nss77 before nss, cpialrl before cpi, etc.)
        if re.search(r'\bnss77\b', _raw_lower): _force_ds = ["NSS77"]
        elif re.search(r'\bnss78\b', _raw_lower): _force_ds = ["NSS78"]
        elif re.search(r'\bnss79c\b', _raw_lower) or "cams" in _raw_lower: _force_ds = ["NSS79C"]
        elif re.search(r'\bnss79\b', _raw_lower) or "ayush" in _raw_lower: _force_ds = ["NSS79"]
        elif re.search(r'\bnss\b', _raw_lower): _force_ds = ["NSS77", "NSS78", "NSS79C"]
        elif re.search(r'\bnfhs\b', _raw_lower) or re.search(r'nfhs[-\s]?\d', _raw_lower) or "family health survey" in _raw_lower: _force_ds = ["NFHS"]
        elif re.search(r'\baishe\b', _raw_lower): _force_ds = ["AISHE"]
        elif re.search(r'\bcpialrl\b', _raw_lower) or ("consumer price" in _raw_lower and ("agricultural" in _raw_lower or "rural labour" in _raw_lower)): _force_ds = ["CPIALRL"]
        elif re.search(r'\bcpi\b', _raw_lower) or "retail" in _raw_lower or "potatoes" in _raw_lower or "onions" in _raw_lower or "electricity cost" in _raw_lower or "subgroup index" in _raw_lower: _force_ds = ["CPI"]
        elif re.search(r'\bplfs\b', _raw_lower) or re.search(r'\blfpr\b', _raw_lower): _force_ds = ["PLFS"]
        elif re.search(r'\bnas\b', _raw_lower) or "national accounts" in _raw_lower: _force_ds = ["NAS"]
        elif re.search(r'\btus\b', _raw_lower) or "time use" in _raw_lower or "icatus" in _raw_lower: _force_ds = ["TUS"]
        elif re.search(r'\bwpi\b', _raw_lower) or ("wholesale" in _raw_lower and "price" in _raw_lower): _force_ds = ["WPI"]
        elif re.search(r'\biip\b', _raw_lower): _force_ds = ["IIP"]
        elif re.search(r'\basi\b', _raw_lower) or "annual survey of industries" in _raw_lower: _force_ds = ["ASI"]
        elif re.search(r'\basuse\b', _raw_lower): _force_ds = ["ASUSE"]
        elif re.search(r'\besi\b', _raw_lower) or "energy statistics" in _raw_lower: _force_ds = ["ESI"]
        elif re.search(r'\bhces\b', _raw_lower) or "consumption expenditure" in _raw_lower: _force_ds = ["HCES"]
        elif re.search(r'\benvstat\b', _raw_lower) or "environment statistics" in _raw_lower: _force_ds = ["ENVSTAT"]
        elif re.search(r'\brbi\b', _raw_lower): _force_ds = ["RBI"]
        elif re.search(r'\bec4\b', _raw_lower): _force_ds = ["EC4"]
        elif re.search(r'\bec5\b', _raw_lower): _force_ds = ["EC5"]
        elif re.search(r'\bec6\b', _raw_lower): _force_ds = ["EC6"]
        elif re.search(r'\bec\b', _raw_lower) or ("economic" in _raw_lower and "census" in _raw_lower): _force_ds = ["EC4", "EC5", "EC6"]
        
        top_results = sementic.search_indicators(q)
        
        # Force-include logic
        if _force_ds and not any(r["parent"] in _force_ds for r in top_results):
            ds_best = sementic._search_dataset_only(q, _force_ds)
            if ds_best:
                top_results = [ds_best] + [r for r in top_results if r["parent"] not in _force_ds][:2]
        
        if not top_results:
            results.append([ind_name, actual_ds, 0, 0, 0, 0, "No Result", "No Result"])
            continue
            
        pred_ind = top_results[0]
        pred_ds = pred_ind["parent"]
        
        # 1. Dataset Accuracy
        ds_acc = 1.0 if pred_ds == actual_ds else 0.0
        if not ds_acc and actual_ds == "CPI2" and pred_ds == "CPI":
            ds_acc = 1.0  # CPI2 merged into CPI
            
        # 2. Indicator Accuracy
        ind_acc = 1.0 if pred_ind["name"].lower() == ind_name.lower() else 0.0
        
        # 3. Filter Accuracy (Mandatory 4: Year, Sector, Gender, State)
        expected_filters = get_mandatory_filters_for_indicator(ind_code)
        
        # Run full filter selection + ensure_required_filters_present (same as production)
        related_filters = [f for f in sementic.FILTERS if f["parent"] == pred_ind["code"]]
        grouped = {}
        for f in related_filters:
            grouped.setdefault(f["filter_name"], []).append(f)

        best_filters_list = []
        for fname, opts in grouped.items():
            best_opt = sementic.select_best_filter_option(q, fname, opts, sementic.cross_encoder)
            best_filters_list.append({"filter_name": fname, "option": best_opt["option"]})

        # Call the real ensure_required_filters_present so essential filters are added
        best_filters_list = sementic.ensure_required_filters_present(
            best_filters_list, pred_ds, grouped, q, sementic.cross_encoder
        )
        pred_filter_names = {f["filter_name"] for f in best_filters_list} # sementic.ensure_required_filters_present returns a list of objects, we just need names
        
        if expected_filters:
            match_count = sum(1 for ef in expected_filters if any(ef.lower() in pf.lower() for pf in pred_filter_names))
            filter_acc = match_count / len(expected_filters)
        else:
            filter_acc = 1.0 # No mandatory filters expected
            
        # 4. Essential Filter Accuracy
        essential_list = sementic.ESSENTIAL_FILTERS_BY_DATASET.get(actual_ds, [])
        if essential_list:
            ess_match = sum(1 for ef in essential_list if any(ef.lower() in pf.lower() for pf in pred_filter_names))
            essential_acc = ess_match / len(essential_list)
        else:
            essential_acc = 1.0
            
        results.append([
            ind_name, 
            actual_ds, 
            ds_acc * 100, 
            ind_acc * 100, 
            filter_acc * 100, 
            essential_acc * 100,
            pred_ds,
            pred_ind["name"]
        ])

    return results

def main():
    output_file = os.path.join(BASE_DIR, "data", "accuracy_audit_results.csv")
    headers = [
        "Product Name", "Actual Dataset", "Dataset Accuracy (%)", 
        "Indicator Accuracy (%)", "Filter Accuracy (%)", 
        "Essential Filter Accuracy (%)", "Predicted Dataset", "Predicted Indicator"
    ]
    
    audit_data = evaluate_accuracy()
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(audit_data)
        
    print(f"\n[SUCCESS] Audit complete! Results saved to: {output_file}")
    
    # Calculate global averages
    avg_ds = np.mean([r[2] for r in audit_data])
    avg_ind = np.mean([r[3] for r in audit_data])
    avg_fil = np.mean([r[4] for r in audit_data])
    avg_ess = np.mean([r[5] for r in audit_data])
    
    print("-" * 50)
    print(f"GLOBAL AGGREGATE SCORES:")
    print(f"Dataset Accuracy:   {avg_ds:.2f}%")
    print(f"Indicator Accuracy: {avg_ind:.2f}%")
    print(f"Filter Accuracy:    {avg_fil:.2f}%")
    print(f"Essential Filter:   {avg_ess:.2f}%")
    print("-" * 50)

if __name__ == "__main__":
    main()
