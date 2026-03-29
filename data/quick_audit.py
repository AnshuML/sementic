
import openpyxl
import json
import re
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from sementic import app, ESSENTIAL_FILTERS_BY_DATASET

# Helper to find indicators for synthetic queries
with open('products.json', 'r', encoding='utf-8') as f:
    ALL_DATA = json.load(f).get('datasets', {})

def get_accuracy_metrics(row_data, prediction):
    prompt, exp_ds, exp_ind, exp_f, exp_ess_f = row_data
    if not prediction or "results" not in prediction or not prediction["results"]:
        return 0, 0, 0, 0
    top = prediction["results"][0]
    pred_ds = top["product"].upper()
    pred_ind = top["indicator_name"].lower()
    pred_filters = [f["filter_name"].lower() for f in top.get("filters", [])]
    ds_acc = 100 if pred_ds == exp_ds.upper() else 0
    if not ds_acc and exp_ds.upper() == "CPI" and pred_ds == "CPI2": ds_acc = 100
    if not ds_acc and exp_ds.upper() == "NSS79C" and pred_ds == "NSS79": ds_acc = 100
    ind_acc = 100 if (exp_ind.lower() in pred_ind or pred_ind in exp_ind.lower()) else 0
    mandatory = ["year", "sector", "gender", "state"]
    match_count = sum(1 for m in mandatory if any(m in pf for pf in pred_filters))
    f_acc = (match_count / 4) * 100
    ess_list = [e.lower() for e in ESSENTIAL_FILTERS_BY_DATASET.get(exp_ds.upper(), [])]
    if not ess_list:
        ess_acc = 100
    else:
        match_ess = sum(1 for e in ess_list if any(e in pf for pf in pred_filters))
        ess_acc = (match_ess / len(ess_list)) * 100
    return ds_acc, ind_acc, f_acc, ess_acc

def main():
    client = app.test_client()
    report_path = 'data/Semantic Search Test Report_new.xlsx'
    wb = openpyxl.load_workbook(report_path, data_only=True)
    
    # Just test 5 representative products for quick result
    test_products = ['PLFS', 'CPI', 'WPI', 'IIP', 'ASI']
    
    summary_data = []
    print(f"\n{'PRODUCT':<10} | {'TOTAL':<5} | {'DS ACC':<8} | {'IND ACC':<8} | {'FLT ACC':<8} | {'ESS ACC':<8}")
    print("-" * 65)

    for prod in test_products:
        sheet = wb[prod]
        rows = list(sheet.iter_rows(values_only=True))
        test_cases = []
        for row in rows[1:11]: # Just 10 cases per product
            if row[0]:
                test_cases.append((row[0], str(row[2] or prod), str(row[5] or ""), "", ""))
        
        results = []
        for case in test_cases:
            resp = client.post("/search/predict", json={"query": case[0]})
            metrics = get_accuracy_metrics(case, resp.get_json())
            results.append(metrics)
        
        if results:
            avg_ds = sum(r[0] for r in results) / len(results)
            avg_ind = sum(r[1] for r in results) / len(results)
            avg_f = sum(r[2] for r in results) / len(results)
            avg_ess = sum(r[3] for r in results) / len(results)
            print(f"{prod:<10} | {len(results):<5} | {avg_ds:>7.2f}% | {avg_ind:>7.2f}% | {avg_f:>7.2f}% | {avg_ess:>7.2f}%")

if __name__ == "__main__":
    main()
