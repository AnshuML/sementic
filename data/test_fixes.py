"""
Quick verification of the key logic fixes in sementic.py
Tests the pure logic functions without requiring the server/models.
"""
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# =====================
# Simulate the key functions
# =====================

YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
# Broader pattern used inside Year filter (also matches 19xx)
_ANY_YEAR_PAT = re.compile(r"\b((?:19|20)\d{2})\b")

def normalize_year_string(s):
    return re.sub(r"[^0-9]", "", str(s))

def map_year_to_option(user_year, options, query=None):
    y = int(user_year)
    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]
    q_lower = (query or "").lower()
    is_jan_mar = any(m in q_lower for m in ["january", "february", "march"])
    has_long_fy = any("-" in str(o.get("option", "")) and len(re.sub(r'[^0-9]', '', str(o.get("option", "")))) >= 8
                      for o in options[:3])
    
    targets = [
        f"{y}{y+1}",
        f"{y}{str(y+1)[-2:]}",
        f"{y-1}{y}",
        f"{y-1}{str(y)[-2:]}",
        str(y)
    ]
    
    if is_jan_mar and has_long_fy:
        targets = [
            f"{y-1}{y}",
            f"{y-1}{str(y)[-2:]}",
            f"{y}{y+1}",
            f"{y}{str(y+1)[-2:]}",
            str(y)
        ]
    
    norm_options = {normalize_year_string(o["option"]): o for o in options}
    for t in targets:
        if t in norm_options:
            return norm_options[t]
    return None


# Helper to simulate filter options
def make_opts(values, parent="TEST", filter_name="Year"):
    return [{"parent": parent, "filter_name": filter_name, "option": v} for v in values]


# =====================
# TEST 1: IIP Year filter with base year + data year
# =====================
print("=" * 60)
print("TEST 1: IIP Year - base year vs data year separation")
print("=" * 60)

def test_year_extraction(query, options):
    """Simulate the Year filter logic from select_best_filter_option"""
    q_lower = query.lower()
    all_years = _ANY_YEAR_PAT.findall(q_lower)
    
    base_year_in_query = None
    data_years = []
    if all_years:
        base_pattern = re.search(r'base[_ ]?(?:year)?[:\s]*(?:of\s+)?(?:year\s+)?(\d{4})', q_lower)
        if base_pattern:
            base_year_in_query = base_pattern.group(1)
        base_paren = re.search(r'\(\s*base\s+(\d{4})', q_lower)
        if base_paren:
            base_year_in_query = base_paren.group(1)
        for y in all_years:
            if y != base_year_in_query:
                data_years.append(y)
        if not data_years:
            data_years = all_years
    
    fy_match = re.search(r'(\d{4})[-/](\d{2,4})', q_lower)
    fy_year = None
    if fy_match:
        before_fy = q_lower[:fy_match.start()].rstrip()
        if not before_fy.endswith('base') and 'base_year' not in before_fy[-15:]:
            fy_year = fy_match.group(1)
    
    # Quarter Q4 fix
    quarter_q4 = re.search(r'(?:jan(?:uary)?[\s\-]+mar(?:ch)?|q4)', q_lower)
    if quarter_q4 and data_years and not fy_year:
        qy = int(data_years[0])
        adjusted_year = str(qy - 1)
        mapped = map_year_to_option(adjusted_year, options, query=query)
        if mapped:
            return mapped["option"]
    
    if fy_year and fy_year not in (base_year_in_query or ""):
        mapped = map_year_to_option(fy_year, options, query=query)
        if mapped:
            return mapped["option"]
    
    user_year = data_years[0] if data_years else (all_years[0] if all_years else None)
    if user_year:
        mapped = map_year_to_option(user_year, options, query=query)
        if mapped:
            return mapped["option"]
    
    return "Select All"

# IIP Monthly Year options (plain years)
iip_monthly_years = make_opts(["Select All", "2025", "2024", "2023", "2022", "2021", "2020", "2019",
                               "2018", "2017", "2016", "2015", "2014", "2013", "2012", "2011",
                               "2010", "2009", "2008", "2007", "2006", "2005", "2004", "2003",
                               "2002", "2001", "2000", "1999", "1998", "1997", "1996", "1995", "1994"])

tests_iip = [
    ("Monthly IIP for Electricity in December 2010", "2010"),
    ("Monthly IIP for January 2025 using base 2011-12", "2025"),
    ("Monthly General Index for September 2022 with base year 2011-12", "2022"),
    ("Monthly Intermediate Goods index for August 2023 (Base 2011-12)", "2023"),
    ("Monthly IIP for Manufacture of Tobacco in December 2012 (Base 2004-05)", "2012"),
    ("Monthly IIP for Fabricated Metal in June 2016 (Base 2004-05)", "2016"),
    ("Monthly IIP for Electrical Equipment in July 2021 (Base 2011-12)", "2021"),
    ("Monthly General Index for December 2000 (Base 1993-94)", "2000"),
    ("Monthly IIP for Leather in May 1999 (Base 1993-94)", "1999"),
    ("Monthly IIP for Food Products in January 1995 (Base 1993-94)", "1995"),
    ("Monthly IIP for Intermediate Goods in March 2004 (Base Year 1993-94)", "2004"),
]

passed, failed = 0, 0
for query, expected in tests_iip:
    result = test_year_extraction(query, iip_monthly_years)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  IIP Year: {passed}/{passed+failed} passed")


# =====================
# TEST 2: CPIALRL Year mapping with months
# =====================
print("\n" + "=" * 60)
print("TEST 2: CPIALRL Year - month-aware fiscal year mapping")
print("=" * 60)

cpialrl_years = make_opts(["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021",
                           "2019-2020", "2018-2019", "2017-2018", "2016-2017", "2015-2016",
                           "2014-2015", "2013-2014", "2012-2013", "2011-2012", "2010-2011",
                           "2009-2010", "2008-2009", "2007-2008", "2006-2007", "2005-2006",
                           "2004-2005", "2003-2004", "2002-2003", "2001-2002", "2000-2001",
                           "1999-2000"])

tests_cpialrl = [
    ("CPI-AL value for Madhya Pradesh in February 2011", "2010-2011"),
    ("Clothing inflation in Assam, March 2023", "2022-2023"),
    ("General Index in Tamil Nadu during April 2020", "2020-2021"),
    ("Food inflation in Bihar, December 1999", "1999-2000"),
    ("Fuel costs in Rajasthan, September 2019", "2019-2020"),
]

passed, failed = 0, 0
for query, expected in tests_cpialrl:
    result = test_year_extraction(query, cpialrl_years)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  CPIALRL Year: {passed}/{passed+failed} passed")


# =====================
# TEST 3: CPI Year extraction (plain years)
# =====================
print("\n" + "=" * 60)
print("TEST 3: CPI Year - plain year extraction")
print("=" * 60)

cpi_years = make_opts(["Select All", "2011", "2012", "2013", "2014", "2015", "2016",
                       "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"])

tests_cpi = [
    ("Cost of LPG in Ladakh for April 2024", "2024"),
    ("Spices subgroup index for Rural Lakshadweep in December 2024", "2024"),
    ("Household Goods and Services index for Urban Kerala in August 2024", "2024"),
    ("Urban Clothing index in Andhra Pradesh for June 2024", "2024"),
    ("Cost of Tuition Fees in Rural Madhya Pradesh for July 2024", "2024"),
    ("Fuel and Light in Tamil Nadu for 2011", "2011"),
    ("Retail inflation for Vegetables in Urban Delhi for July 2024", "2024"),
    ("Price of Wheat/Atta in Sikkim for August 2024", "2024"),
    ("Cost of Mobile Phone in Mizoram for November 2024", "2024"),
    ("Urban Miscellaneous index for Andaman in April 2021", "2021"),
]

passed, failed = 0, 0
for query, expected in tests_cpi:
    result = test_year_extraction(query, cpi_years)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  CPI Year: {passed}/{passed+failed} passed")


# =====================
# TEST 4: PLFS Quarter → Fiscal Year mapping
# =====================
print("\n" + "=" * 60)
print("TEST 4: PLFS Quarter-aware fiscal year")
print("=" * 60)

plfs_years = make_opts(["2025-26", "2025", "2024-25", "2023-24", "2022-23", "2021-22",
                        "2020-21", "2019-20", "2018-19", "2017-18"])

tests_plfs = [
    ("WPR for youth in urban J&K for Jan-Mar 2024", "2023-24"),
    ("Unemployment rate in urban Delhi for the Jan-Mar quarter of 2025", "2024-25"),
    ("LFPR for rural Bihar in 2023", "2023-24"),
]

passed, failed = 0, 0
for query, expected in tests_plfs:
    result = test_year_extraction(query, plfs_years)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  PLFS Year: {passed}/{passed+failed} passed")


# =====================
# TEST 5: NAS Base_Year defaults
# =====================
print("\n" + "=" * 60)
print("TEST 5: NAS Base_Year smart defaults")
print("=" * 60)

def test_base_year(query, options, parent_code="NAS"):
    """Simulate Base_Year filter logic"""
    q_lower = query.lower()
    fname_lower = "base_year"
    
    # Explicit base year mention
    base_explicit = re.search(r'base[_ ]?(?:year)?[:\s]*(\d{4}(?:[-/]\d{2,4})?)', q_lower)
    if base_explicit:
        base_val = base_explicit.group(1)
        for opt in options:
            opt_text = str(opt.get("option", "")).lower().strip()
            if base_val in opt_text or opt_text in base_val:
                return opt["option"]
            norm_base = re.sub(r'[^0-9]', '', base_val)
            norm_opt = re.sub(r'[^0-9]', '', opt_text)
            if norm_base and norm_opt and (norm_base.startswith(norm_opt) or norm_opt.startswith(norm_base)):
                return opt["option"]
    
    # Standalone match
    for opt in options:
        opt_text = str(opt.get("option", "")).lower().strip()
        if opt_text in q_lower:
            return opt["option"]
    
    # Smart defaults
    if parent_code == "NAS":
        data_year_match = _ANY_YEAR_PAT.search(q_lower)
        data_year = int(data_year_match.group(1)) if data_year_match else 0
        target_base = "2022-23" if data_year >= 2023 else "2011-12"
        for opt in options:
            if target_base in str(opt.get("option", "")):
                return opt["option"]
    
    if parent_code == "IIP":
        data_year_match = _ANY_YEAR_PAT.search(q_lower)
        if data_year_match:
            dy = int(data_year_match.group(1))
            if dy < 2005:
                target = "1993-94"
            elif dy < 2012:
                target = "2004-05"
            else:
                target = "2011-12"
            for opt in options:
                if target in str(opt.get("option", "")):
                    return opt["option"]
        for opt in options:
            if "2011" in str(opt.get("option", "")):
                return opt["option"]
    
    def extract_start_year(opt):
        m = re.search(r"\d{4}", str(opt.get("option", "")))
        return int(m.group(0)) if m else 0
    return max(options, key=lambda o: extract_start_year(o))["option"]


nas_base = make_opts(["2011-12", "2022-23"], parent="NAS_GVA", filter_name="Base_Year")
tests_nas = [
    ("Net taxes on products in 2020-21", "NAS", "2011-12"),
    ("Net Domestic Product in 2021-22", "NAS", "2011-12"),
    ("Financial services GVA at current prices 2021-22", "NAS", "2011-12"),
    ("Back series GDP for 2005-06", "NAS", "2011-12"),
    ("GDP data for 2024-25", "NAS", "2022-23"),
]

passed, failed = 0, 0
for query, ds, expected in tests_nas:
    result = test_base_year(query, nas_base, ds)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  NAS Base_Year: {passed}/{passed+failed} passed")


# IIP Base_Year
iip_base = make_opts(["2011-12", "2004-05", "1993-94"], parent="IIP_Monthly", filter_name="Base_Year")
tests_iip_base = [
    ("Annual IIP for Basic Goods in 1994-95", "IIP", "1993-94"),
    ("Monthly IIP for Mining in June 1998", "IIP", "1993-94"),
    ("Annual IIP for Cotton Textiles for 2002-03", "IIP", "1993-94"),
    ("Annual Capital Goods during 2005-06", "IIP", "2004-05"),
    ("Monthly IIP for Electricity in December 2010", "IIP", "2004-05"),
    ("Monthly IIP for Pharmaceuticals in May 2024 (Base 2011-12)", "IIP", "2011-12"),
    ("Annual IIP for Printing in 2011-12 (Base 2004-05)", "IIP", "2004-05"),
]

passed, failed = 0, 0
for query, ds, expected in tests_iip_base:
    result = test_base_year(query, iip_base, ds)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  IIP Base_Year: {passed}/{passed+failed} passed")


# =====================
# TEST 6: ASI classification_year
# =====================
print("\n" + "=" * 60)
print("TEST 6: ASI Classification Year defaults")
print("=" * 60)

asi_class = make_opts(["2008", "2004", "1998", "1987"], filter_name="classification_year")

def test_classification_year(query, options):
    q_lower = query.lower()
    nic_match = re.search(r'nic[\s\-_]*(\d{4})', q_lower)
    if nic_match:
        nic_year = nic_match.group(1)
        for opt in options:
            if str(opt.get("option", "")).strip() == nic_year:
                return opt["option"]
    for opt in options:
        opt_text = str(opt.get("option", "")).strip()
        if opt_text in q_lower:
            idx = q_lower.find(opt_text)
            after = q_lower[idx + len(opt_text):idx + len(opt_text) + 1] if idx + len(opt_text) < len(q_lower) else ""
            if after not in ("-", "/"):
                return opt["option"]
    def _extract_year(opt):
        m = re.search(r"\d{4}", str(opt.get("option", "")))
        return int(m.group(0)) if m else 0
    return max(options, key=lambda o: _extract_year(o))["option"]

tests_asi = [
    ("What is the factory output in Gujarat for 2022-23?", "2008"),  # Default
    ("Show employment in textile industry for 2022-23", "2008"),     # Default
    ("Industrial data under NIC 2004", "2004"),                      # Explicit NIC
    ("Industrial data under NIC 2008", "2008"),                      # Explicit NIC
    ("Total employment in industries for 2022-23", "2008"),          # Default (not matching 2022 as class year)
]

passed, failed = 0, 0
for query, expected in tests_asi:
    result = test_classification_year(query, asi_class)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        print(f"  {status}: '{query}' → Got: {result}, Expected: {expected}")
        failed += 1
    else:
        passed += 1
print(f"  ASI classification_year: {passed}/{passed+failed} passed")


print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
