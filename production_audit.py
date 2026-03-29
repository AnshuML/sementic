
import json
import re
from sementic import app

test_cases = [
    # 1. PLFS
    {"query": "PLFS unemployment rate in rural areas 2023", "expected_ds": "PLFS", "required_filters": ["Year", "Sector", "Frequency"]},
    {"query": "Periodic Labour Force Survey female labour force participation", "expected_ds": "PLFS", "required_filters": ["Gender", "Frequency"]},
    
    # 2. ASUSE
    {"query": "ASUSE unincorporated sector enterprises output", "expected_ds": "ASUSE", "required_filters": ["Frequency", "Sector"]},
    {"query": "Annual Survey of Unincorporated Sector Enterprises 2022-23", "expected_ds": "ASUSE", "required_filters": ["Year", "Frequency"]},
    
    # 3. ASI
    {"query": "ASI factory worker count for 2019-20", "expected_ds": "ASI", "required_filters": ["Year", "classification_year"]},
    {"query": "Annual Survey of Industries NIC 2008", "expected_ds": "ASI", "required_filters": ["classification_year"]},
    
    # 4. TUS
    {"query": "TUS time use survey participation rate", "expected_ds": "TUS", "required_filters": ["Age Group", "ICATUS Activity"]},
    {"query": "TUS hours spent on unpaid domestic work", "expected_ds": "TUS", "required_filters": ["Day Of Week"]},
    
    # 5. Gender
    {"query": "Gender statistics sex ratio at birth", "expected_ds": "Gender", "required_filters": ["Gender", "State"]},
    {"query": "women participation in parliament gender stats", "expected_ds": "Gender", "required_filters": ["Gender", "Year"]},
    
    # 6. AISHE
    {"query": "AISHE higher education enrolment for 2021-22", "expected_ds": "AISHE", "required_filters": ["University Type", "State", "Year"]},
    {"query": "All India Survey on Higher Education college density", "expected_ds": "AISHE", "required_filters": ["State"]},
    
    # 7. NSS77
    {"query": "NSS77 debt and investment survey livestock", "expected_ds": "NSS77", "required_filters": ["Sector", "State"]},
    {"query": "NSS 77th round AIDIS land holdings", "expected_ds": "NSS77", "required_filters": ["Sector"]},
    
    # 8. NSS78
    {"query": "NSS78 domestic tourism survey expenditure", "expected_ds": "NSS78", "required_filters": ["Sector", "State"]},
    {"query": "NSS 78th round tourism visits", "expected_ds": "NSS78", "required_filters": ["Sector"]},
    
    # 9. ESI
    {"query": "ESI energy statistics electricity consumption", "expected_ds": "ESI", "required_filters": ["Energy Commodities"]},
    {"query": "Energy Statistics India power supply", "expected_ds": "ESI", "required_filters": ["Use of Energy Balance"]},
    
    # 10. CPIALRL
    {"query": "CPIALRL agricultural labourers index 2023", "expected_ds": "CPIALRL", "required_filters": ["Year", "Base_Year"]},
    {"query": "Consumer Price Index for rural labourers", "expected_ds": "CPIALRL", "required_filters": ["Base_Year"]},
    
    # 11. HCES
    {"query": "HCES consumption expenditure mpce 2023", "expected_ds": "HCES", "required_filters": ["Year", "Sector"]},
    {"query": "Household Consumption Expenditure Survey food expenditure", "expected_ds": "HCES", "required_filters": ["Sector", "State"]},
    
    # 12. ENVSTAT
    {"query": "ENVSTAT environment statistics forest cover", "expected_ds": "ENVSTAT", "required_filters": ["Category", "State"]},
    {"query": "ENVSTAT hazardous waste generation", "expected_ds": "ENVSTAT", "required_filters": ["Category", "Year"]},
    
    # 13. NFHS
    {"query": "NFHS family health survey immunization rate", "expected_ds": "NFHS", "required_filters": ["Indicator Category", "State"]},
    {"query": "NFHS fertility and mortality report", "expected_ds": "NFHS", "required_filters": ["Indicator Category", "Year"]},
    
    # 14. EC4 (Economic Census)
    {"query": "EC4 4th economic census establishment count", "expected_ds": "EC4", "required_filters": ["State", "Sector"]},
    {"query": "4th economic census rural enterprises", "expected_ds": "EC4", "required_filters": ["Sector", "Establishment Type"]},
    
    # 15. IIP
    {"query": "IIP industrial production manufacturing index", "expected_ds": "IIP", "required_filters": ["Base_Year", "Frequency"]},
    {"query": "IIP monthly mining index June 2024", "expected_ds": "IIP", "required_filters": ["Frequency"]},
    
    # 16. WPI
    {"query": "WPI wholesale price index inflation", "expected_ds": "WPI", "required_filters": ["Base_Year", "Major Group"]},
    {"query": "WPI index for primary articles", "expected_ds": "WPI", "required_filters": ["Group"]},
    
    # 17. CPI
    {"query": "CPI consumer price index rural 2023", "expected_ds": ["CPI", "CPI2"], "required_filters": ["Base_Year", "Series", "Division"]},
    {"query": "CPI inflation current series", "expected_ds": ["CPI", "CPI2"], "required_filters": ["Series"]},
    
    # 18. NAS
    {"query": "NAS national accounts gdp growth rate 2023-24", "expected_ds": "NAS", "required_filters": ["Series", "Frequency", "Year"]},
    {"query": "NAS national accounts statistics gva", "expected_ds": "NAS", "required_filters": ["Series"]},
    
    # 19. RBI
    {"query": "RBI bank lending rates banking statistics", "expected_ds": "RBI", "required_filters": ["Bank Name", "Frequency"]},
    {"query": "RBI deposit rates monthly", "expected_ds": "RBI", "required_filters": ["Frequency"]},
    
    # 20. NSS79
    {"query": "NSS79 modular survey cams 2023", "expected_ds": ["NSS79", "NSS79C"], "required_filters": ["Sector", "State"]},
    {"query": "Comprehensive Annual Modular Survey NSS", "expected_ds": ["NSS79", "NSS79C"], "required_filters": ["Sector"]},
    
    # 21. NSS79C
    {"query": "NSS79C cams survey indicators", "expected_ds": ["NSS79", "NSS79C"], "required_filters": ["Sector", "State"]},
    {"query": "NSS 79th round cams", "expected_ds": ["NSS79", "NSS79C"], "required_filters": ["Sector"]},
    
    # 22. UDISE
    {"query": "UDISE school education management", "expected_ds": "UDISE", "required_filters": ["Management", "School Category", "State"]},
    {"query": "UDISE higher secondary schools in Bihar", "expected_ds": "UDISE", "required_filters": ["School Category", "State"]},
]

def run_audit():
    client = app.test_client()
    results = []
    correct_ds = 0
    correct_filters = 0
    
    print("\n" + "="*80)
    print(f"{'EXPECTED':<10} | {'QUERY':<40} | {'DS'} | {'FILTERS'}")
    print("-" * 80)
    
    for case in test_cases:
        response = client.post("/search/predict", json={"query": case["query"]})
        data = response.get_json()
        
        if not data or "results" not in data or not data["results"]:
            print(f"{str(case['expected_ds']):<10} | {case['query'][:40]:<40} | ❌ | ❌ (No Results)")
            results.append({**case, "predicted": "None", "ds_ok": False, "filters_ok": False})
            continue
            
        top = data["results"][0]
        predicted_ds = top["product"].upper()
        
        # Dataset check
        expected_ds = case["expected_ds"]
        if isinstance(expected_ds, list):
            ds_ok = predicted_ds in expected_ds
        else:
            ds_ok = predicted_ds == expected_ds
            
        # Filter check
        present_filters = [f["filter_name"] for f in top["filters"]]
        missing_filters = [rf for rf in case["required_filters"] if rf not in present_filters]
        filters_ok = len(missing_filters) == 0
        
        ds_status = "✅" if ds_ok else "❌"
        filters_status = "✅" if filters_ok else f"❌(Miss:{','.join(missing_filters)})"
        
        if ds_ok: correct_ds += 1
        if filters_ok: correct_filters += 1
        
        print(f"{str(case['expected_ds']):<10} | {case['query'][:40]:<40} | {ds_status} | {filters_status}")
        results.append({**case, "predicted": predicted_ds, "ds_ok": ds_ok, "filters_ok": filters_ok, "missing": missing_filters})
        
    ds_acc = (correct_ds / len(test_cases)) * 100
    filter_acc = (correct_filters / len(test_cases)) * 100
    
    print("-" * 80)
    print(f"Dataset Accuracy: {ds_acc:.2f}% (Target: 100%)")
    print(f"Filter Accuracy:  {filter_acc:.2f}% (Target: 95%)")
    print("=" * 80 + "\n")
    
    report_path = r"C:\Users\DELL\.gemini\antigravity\brain\b29568c4-08d6-472d-bb55-ed02c0e1794a\production_accuracy_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Production Accuracy Report (22 Products)\n\n")
        f.write(f"- **Dataset Identification Accuracy**: {ds_acc:.2f}% (Golden Rule: 100%)\n")
        f.write(f"- **Essential Filter Accuracy**: {filter_acc:.2f}% (Target: 95%+)\n\n")
        f.write("| Product | Query | DS Status | Filter Status | Predicted | Missing Filters |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in results:
            ds_icon = "✅" if r["ds_ok"] else "❌"
            f_icon = "✅" if r["filters_ok"] else "❌"
            f.write(f"| {r['expected_ds']} | {r['query']} | {ds_icon} | {f_icon} | {r['predicted']} | {', '.join(r['missing'])} |\n")

if __name__ == "__main__":
    run_audit()
