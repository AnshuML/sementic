import json

def check_datasets(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    datasets = data.get("datasets", {})
    
    targets = {
        "CPI": {
            "indicators": ["Division"],
            "filters": ["Division", "Base_Year", "Series"]
        },
        "IIP": {
            "indicators": ["Monthly", "Annually"],
            "filters": ["Frequency", "Base_Year", "Type", "Category"]
        },
        "TUS": {
            "filters": ["Age Group", "ICATUS Activity"]
        },
        "WPI": {
            "filters": ["Major Group", "Sub Group"]
        },
        "ESI": {
            "filters": ["Use of Energy Balance", "Energy Commodities", "End Use Sector"]
        }
    }
    
    for ds_name, expected in targets.items():
        print(f"\nChecking {ds_name}:")
        if ds_name not in datasets:
            print(f"  [ERROR] Dataset {ds_name} missing!")
            continue
            
        ds = datasets[ds_name]
        indicators = ds.get("indicators", [])
        print(f"  Total Indicators: {len(indicators)}")
        
        if "indicators" in expected:
            actual_inds = [i["name"] for i in indicators]
            for exp_ind in expected["indicators"]:
                if exp_ind in actual_inds:
                    print(f"  [OK] Indicator '{exp_ind}' found.")
                else:
                    print(f"  [ERROR] Indicator '{exp_ind}' NOT found! Actual: {actual_inds[:5]}...")
        
        if "filters" in expected and indicators:
            # Check filters of the first indicator
            first_ind = indicators[0]
            actual_filters = []
            for f in first_ind.get("filters", []):
                 actual_filters.extend(f.keys())
            
            for exp_filt in expected["filters"]:
                if exp_filt in actual_filters:
                    print(f"  [OK] Filter '{exp_filt}' found.")
                else:
                    print(f"  [ERROR] Filter '{exp_filt}' NOT found! Actual: {actual_filters}")

if __name__ == "__main__":
    check_datasets(r'c:\Users\DELL\OneDrive\Desktop\sementic_sewarch\products.json')
