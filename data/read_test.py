import openpyxl
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'c:\Users\DELL\OneDrive\Desktop\sementic_sewarch\products.json', 'r', encoding='utf-8', errors='ignore') as f:
    products = json.load(f)

datasets = products.get("datasets", {})
print("=== ALL DATASETS ===")
for ds_name in datasets:
    indicators = datasets[ds_name].get("indicators", [])
    print(f"\n{ds_name}: {len(indicators)} indicators")
    # Show first indicator's filter names
    if indicators:
        ind = indicators[0]
        filter_names = []
        for flt in ind.get("filters", []):
            if isinstance(flt, dict):
                filter_names.extend(flt.keys())
        print(f"  Filters: {filter_names}")

# Check NSS77 filters specifically
print("\n\n=== NSS77 FILTER DETAILS ===")
if "NSS77" in datasets:
    ind = datasets["NSS77"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                if isinstance(v, list):
                    print(f"  {k}: {v[:5]}...")
                else:
                    print(f"  {k}: {v}")

# Check NSS78 filters
print("\n\n=== NSS78 FILTER DETAILS ===")  
if "NSS78" in datasets:
    ind = datasets["NSS78"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                if isinstance(v, list):
                    print(f"  {k}: {v[:5]}...")
                else:
                    print(f"  {k}: {v}")

# ASI classification_year options
print("\n\n=== ASI classification_year OPTIONS ===")
if "ASI" in datasets:
    ind = datasets["ASI"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                if "classif" in k.lower() or "year" in k.lower() or "base" in k.lower():
                    print(f"  {k}: {v}")

# NAS Base_Year options
print("\n\n=== NAS filters ===")
if "NAS" in datasets:
    ind = datasets["NAS"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                print(f"  {k}: {v}")

# CPI filters
print("\n\n=== CPI filters ===")
if "CPI" in datasets:
    ind = datasets["CPI"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                print(f"  {k}: {v}")

# IIP filters
print("\n\n=== IIP filters ===")
if "IIP" in datasets:
    ind = datasets["IIP"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                print(f"  {k}: {v}")

# CPIALRL filters 
print("\n\n=== CPIALRL filters ===")
if "CPIALRL" in datasets:
    ind = datasets["CPIALRL"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                if isinstance(v, list) and len(v) > 10:
                    print(f"  {k}: [{v[0]}, {v[1]}, ... {v[-1]}] ({len(v)} options)")
                else:
                    print(f"  {k}: {v}")

# PLFS filters  
print("\n\n=== PLFS Frequency options ===")
if "PLFS" in datasets:
    ind = datasets["PLFS"]["indicators"][0]
    for flt in ind.get("filters", []):
        if isinstance(flt, dict):
            for k, v in flt.items():
                if "freq" in k.lower():
                    print(f"  {k}: {v}")
