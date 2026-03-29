import json

with open("products.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Define dataset aliases mapped directly to their code
aliases = {
    "EC4": "Total Establishments, Total Workers, 4th economic census",
    "EC5": "Total Establishments, Total Workers, 5th economic census",
    "EC6": "Total Establishments, Total Workers, 6th economic census",
    "ASI": "fixed capital, gross output, workers in factory, profit, net value added, invested capital, employees, wages, factories, annual survey of industries",
    "PLFS": "worker population ratio, participation rate, unemployment rate, urban rural, labour force, earnings, wages, ur, wpr, lfpr",
    "CPI": "retail inflation, general index, consumer price, inflation rate, items, food and beverages, rural urban, cpi",
    "TUS": "unpaid caregiving, domestic services, time spent, participation rate, time use survey, tus",
    "IIP": "manufacturing index, electricity index, mining index, industrial production",
    "RBI": "lending rate, exchange rate, forex, external debt, rupee vis-a-vis",
    "NFHS": "family health, immunization, antenatal care, stunted, wasted, anemia",
    "NAS": "national accounts, gdp, gva, constant prices, current prices",
    "CPIALRL": "agricultural labourer, rural labourer, base year 1986",
    "ASUSE": "unincorporated enterprises, gross value added, workers, asuse",
    "WPI": "wholesale price, wpi, primary articles"
}

# Go through each dataset and append to the 'desc' field of its indicators
for dcode, dstr in aliases.items():
    ds_obj = data["datasets"].get(dcode)
    if not ds_obj:
        continue
    inds = ds_obj.get("indicators", [])
    for i in inds:
        # If no desc, create it
        if "desc" not in i:
            i["desc"] = ""
        # Don't add if already added
        if dstr not in i["desc"]:
            i["desc"] = (i["desc"] + " " + dstr).strip()

with open("products.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("Patch applied to products.json! FAISS embeddings will automatically update on next run.")
