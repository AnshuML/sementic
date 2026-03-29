
# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import os, json, re
# import numpy as np
# from sentence_transformers import SentenceTransformer, CrossEncoder
# import faiss
# from datetime import datetime
# import difflib

# # ================================
# # CONFIG
# # ================================
# USE_QDRANT = True
# try:
#     from qdrant_client import QdrantClient
#     from qdrant_client.http import models as qmodels
# except Exception:
#     USE_QDRANT = False

# # ================================
# # LLM (QUERY REWRITER ONLY)
# # ================================
# from langchain_ollama import ChatOllama

# try:
#     rewriter_llm = ChatOllama(
#         model="llama3:70b",
#         base_url="http://localhost:11434",
#         temperature=0.3
#     )

#     rewriter_llm.invoke("ping")
#     print(" Ollama is running")

# except Exception as e:
#     print(" Ollama is not running")


# # ================================
# # REGEX
# # ================================
# YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

# # ================================
# # HELPERS
# # ================================
# def clean_text(t):
#     t = (t or "").lower()
#     t = re.sub(r"[^a-z0-9\s]", " ", t)
#     return re.sub(r"\s+", " ", t).strip()

# def normalize_confidence(scores, min_conf=50, max_conf=95):
#     if not scores:
#         return []
#     mn, mx = min(scores), max(scores)
#     if mn == mx:
#         return [min_conf] * len(scores)
#     return [round(min_conf + (s - mn)/(mx - mn)*(max_conf - min_conf), 2) for s in scores]



# #########
# BASE_YEAR_PATTERN = re.compile(r"(20\d{2})")

# def detect_base_year(query):
#     q = query.lower()

#     if "base year" or " base" in q:
#         m = BASE_YEAR_PATTERN.search(q)
#         if m:
#             return int(m.group(1))

#     return None


# # def resolve_cpi_conflict(results, query):
# #     """
# #     Only when CPI and CPI2 both present in top results
# #     """
# #     datasets = [r["parent"] for r in results]

# #     if "CPI" not in datasets or "CPI2" not in datasets:
# #         return results  # kuch mat chhedo

# #     base_year = detect_base_year(query)

# #     # ---------- case 1: user ne base year bola ----------
# #     if base_year:
# #         if base_year >= 2024:
# #             # CPI2 rakho
# #             return [r for r in results if r["parent"] != "CPI"]
# #         else:
# #             # CPI rakho
# #             return [r for r in results if r["parent"] != "CPI2"]

# #     # ---------- case 2: base year nahi bola ----------
# #     return [r for r in results if r["parent"] != "CPI"]



# #################### new ###############

# def extract_cpi_intent(query: str):
#     prompt = f"""
# You are an intent classifier for CPI datasets.

# Query: {query}

# Return JSON only with keys:
# cpi_intent: true/false
# base_year: number or null
# wants_back_series: true/false
# has_year: number or null

# Rules:
# - CPI intent includes: CPI, inflation, price index
# - If user mentions base year → fill base_year
# - If user mentions past historical/back → wants_back_series true
# - If user mentions a year like 2021 → has_year = 2021
# """

#     try:
#         res = rewriter_llm.invoke(prompt).content.strip()
#         return json.loads(res)
#     except:
#         return {
#             "cpi_intent": False,
#             "base_year": None,
#             "wants_back_series": False,
#             "has_year": None
#         }


# def resolve_cpi_conflict(results, query):

#     intent = extract_cpi_intent(query)

#     # run only if CPI intent
#     if not intent["cpi_intent"]:
#         return results

#     datasets = [r["parent"] for r in results]
#     if "CPI" not in datasets or "CPI2" not in datasets:
#         return results

#     base_year = intent["base_year"]
#     year = intent["has_year"]
#     wants_back = intent["wants_back_series"]

#     # -------------------------------------------------
#     # 1️⃣ explicit base year mentioned
#     # -------------------------------------------------
#     if base_year:
#         if base_year >= 2024:
#             # new base → CPI2
#             return [r for r in results if r["parent"] != "CPI"]
#         else:
#             # old base → CPI
#             return [r for r in results if r["parent"] != "CPI2"]

#     # -------------------------------------------------
#     # 2️⃣ explicit back series intent
#     # -------------------------------------------------
#     if wants_back:
#         # always CPI2 back
#         return [r for r in results if r["parent"] != "CPI"]

#     # -------------------------------------------------
#     # 3️⃣ user mentioned year but NOT base year
#     # -------------------------------------------------
#     if year:

#         # year >= 2024 → new CPI2 current
#         if year >= 2024:
#             return [r for r in results if r["parent"] != "CPI"]

#         # year < 2024 → CPI (2012 base)
#         return [r for r in results if r["parent"] != "CPI2"]

#     # -------------------------------------------------
#     # 4️⃣ generic inflation query
#     # -------------------------------------------------
#     # default = latest CPI2
#     return [r for r in results if r["parent"] != "CPI"]





# # ================================
# # LLM QUERY REWRITE
# # ================================
# def rewrite_query_with_llm(user_query):
#     prompt =  f"""
# You are a QUERY NORMALIZATION ENGINE for a data analytics system.

# Task:
# Rewrite the user query safely with controlled semantic normalization.

# STRICT RULES:
# 1. DO NOT add any new information
# 2. DO NOT infer missing filters
# 3. DO NOT assume any category
# 4. DO NOT enrich meaning
# 5. ONLY rewrite words that already exist in the query
# 6. NEVER inject new concepts
# 7. NEVER add sector/gender/state unless explicitly present
# 8. Output ONLY rewritten query
# 9. No explanation
# 10. If the query contains a known dataset short form (CPI, IIP, NAS, PLFS, ASI, HCES, NSS), append its full form in the rewritten query while keeping the short form unchanged (e.g., "CPI" → "CPI Consumer Price Index"), and do not expand anything not explicitly present.
# 11. Do not remove any words from the user query


# SPECIAL RULE (VERY IMPORTANT):

# If the query contains "IIP" and also contains any month name 
# (January–December or short forms like Jan, Feb, etc.), 
# then add the word "monthly" to the query.

# Examples:
# "IIP July data" → "IIP monthly July data"
# "IIP for December" → "IIP monthly December"
# "IIP Aug 2022" → "IIP monthly Aug 2022"

# DO NOT apply this rule to any other dataset.
# If query is about CPI, GDP, PLFS etc → do nothing.


# ALLOWED OPERATIONS:
# - spelling correction
# - grammar correction
# - casing normalization
# - synonym normalization
# - semantic mapping ONLY if the word exists explicitly in text

# CRITICAL RULE (VERY IMPORTANT):
# - If the user query is ONLY a dataset or product name
#   (examples: IIP, CPI, CPIALRL, HCES, ASI,NAS, PLFS,CPI2,ASI,),
#   then RETURN THE QUERY EXACTLY AS IT IS.
# - Dataset names must NEVER be replaced with normal English words.


# STRICT SEMANTIC MAP (ONLY IF WORD EXISTS):
# - gao, gaon, village → rural
# - shehar, city, metro → urban
# - purush, aadmi, mard, man, men → male
# - mahila, aurat, lady, women → female
# - ladka → male
# - ladki → female

#  FORBIDDEN:
# - Do NOT infer urban from city names
# - Do NOT infer rural from state names
# - Do NOT infer gender from profession
# - Do NOT infer sector from geography
# - Do NOT add any category automatically

# Examples:
# RAW: "mens judge in village"
# → "male judge in rural"

# RAW: "Gini Coefficient for urban india in 2023-24"
# → "Gini Coefficient for urban in 2023-24"

# RAW: "factory output gujrat 2022"
# → "factory output Gujarat 2022"

# RAW: "men judges in delhi"
# → "male judges in Delhi"

# RAW: "factory output in gujrat for 2022 in gao"
# → "factory output in Gujarat for 2022 in rural"

# RAW: "data for mahila workers"
# → "data for female workers"

# RAW: "gaon ke factory worker"
# → "rural factory worker"

# RAW: "factory output in mumbai"
# → "factory output in Mumbai"

# User Query:
# "{user_query}"
# """
#     try:
#         out = rewriter_llm.invoke(prompt).content.strip()
#         out = out.replace('"', '').replace("\n", " ").strip()
#         return out
#     except:
#         return user_query

# # ================================
# # YEAR NORMALIZATION
# # ================================
# def normalize_year_string(s):
#     return re.sub(r"[^0-9]", "", str(s))


# def map_year_to_option(user_year, options):
#     y = int(user_year)
#     targets = [
#         f"{y}{y+1}",
#         f"{y-1}{y}",
#         str(y)
#     ]
#     norm_options = {normalize_year_string(o["option"]): o for o in options}
#     for t in targets:
#         if t in norm_options:
#             return norm_options[t]
#     return None

# # ================================
# # UNIVERSAL FILTER NORMALIZER
# # ================================
# def universal_filter_normalizer(ind_code, filters_json):
#     flat = []
#     def recurse(key, value):
#         if isinstance(value, list) and all(isinstance(x, str) for x in value):
#             for opt in value:
#                 flat.append({"parent": ind_code,"filter_name": key,"option": opt})
#         elif isinstance(value, list) and all(isinstance(x, dict) for x in value):
#             for item in value:
#                 for k, v in item.items():
#                     if k.lower() in ["name", "title", "label"]:
#                         flat.append({"parent": ind_code,"filter_name": key,"option": v})
#                     else:
#                         recurse(k, v)
#         elif isinstance(value, dict):
#             for k, v in value.items():
#                 recurse(k, v)

#     for f in filters_json:
#         if isinstance(f, dict):
#             for k, v in f.items():
#                 recurse(k, v)
#     return flat


# #############LLM 
# # ================================
# # SMART FILTER ENGINE
# # ================================
# def select_best_filter_option(query, filter_name, options, cross_encoder):
#     q_lower = query.lower()
#     fname_lower = filter_name.lower()

#     # =========================
#     # YEAR FILTER
#     # =========================
#     if "year" in fname_lower and "base" not in fname_lower:
#         year_match = YEAR_PATTERN.search(q_lower)

#         # user ne year nahi bola → Select All
#         if not year_match:
#             return {
#                 "parent": options[0]["parent"],
#                 "filter_name": filter_name,
#                 "option": "Select All"
#             }

#         user_year = year_match.group(1)

#         mapped = map_year_to_option(user_year, options)
#         if mapped:
#             return mapped

#         pairs = [(query, f"{filter_name} {o['option']}") for o in options]
#         scores = cross_encoder.predict(pairs)
#         return options[int(np.argmax(scores))]

#     # =========================
#     # BASE YEAR FILTER (FINAL FIX)
#     # =========================
#     if "base" in fname_lower and "year" in fname_lower:

#         # 🔹 check if user explicitly mentioned base year
#         for opt in options:
#             opt_text = str(opt["option"]).lower()
#             if opt_text in q_lower:
#                 return opt

#         # 🔹 user ne base year nahi bola → latest base year pick karo
#         def extract_start_year(opt):
#             m = re.search(r"\d{4}", str(opt["option"]))
#             return int(m.group(0)) if m else 0

#         latest = max(options, key=lambda o: extract_start_year(o))
#         return latest

#     # =========================
#     # OTHER FILTERS
#     # =========================
#     mentioned = []

#     for opt in options:
#         opt_text = str(opt.get("option", "")).lower().strip()
#         if not opt_text:
#             continue

#         if opt_text in q_lower:
#             mentioned.append(opt)
#             continue

#         for word in q_lower.split():
#             if difflib.SequenceMatcher(None, opt_text, word).ratio() > 0.80:
#                 mentioned.append(opt)
#                 break

#     if mentioned:
#         pairs = [(query, f"{filter_name} {o['option']}") for o in mentioned]
#         scores = cross_encoder.predict(pairs)
#         return mentioned[int(np.argmax(scores))]

#     return {
#         "parent": options[0]["parent"],
#         "filter_name": filter_name,
#         "option": "Select All"
#     }


# # ================================
# # LOAD PRODUCTS
# # ================================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PRODUCTS_FILE = os.path.join(BASE_DIR, "products", "products.json")

# with open(PRODUCTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
#     raw_products = json.load(f)

# DATASETS, INDICATORS, FILTERS = [], [], []

# for ds_name, ds_info in raw_products.get("datasets", {}).items():
#     DATASETS.append({"code": ds_name, "name": ds_name})

#     for ind in ds_info.get("indicators", []):
#         ind_code = f"{ds_name}_{ind['name']}"
#         INDICATORS.append({
#             "code": ind_code,
#             "name": ind["name"],
#             "desc": ind.get("description", ""),
#             "parent": ds_name
#         })

#         flat = universal_filter_normalizer(ind_code, ind.get("filters", []))
#         FILTERS.extend(flat)

# print(f"[INFO] DATASETS={len(DATASETS)}, INDICATORS={len(INDICATORS)}, FILTERS={len(FILTERS)}")

# # ================================
# # MODELS
# # ================================
# bi_encoder = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
# cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")

# # ================================
# # VECTOR DB
# # ================================
# VECTOR_DIM = bi_encoder.get_sentence_embedding_dimension()
# COLLECTION = "indicators_collection"

# qclient = None
# faiss_index = None

# if USE_QDRANT:
#     try:
#         qclient = QdrantClient(url="http://localhost:6333")
#         if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
#             qclient.recreate_collection(
#                 collection_name=COLLECTION,
#                 vectors_config=qmodels.VectorParams(size=VECTOR_DIM,distance=qmodels.Distance.COSINE)
#             )
#         print("[INFO] Qdrant ready")
#     except Exception as e:
#         USE_QDRANT = False
#         print("[WARN] Qdrant failed, using FAISS:", e)

# names = [clean_text(i["name"]) for i in INDICATORS]
# descs = [clean_text(i.get("desc", "")) for i in INDICATORS]

# embeddings = (0.4 * bi_encoder.encode(names, convert_to_numpy=True) + 0.6 * bi_encoder.encode(descs, convert_to_numpy=True))
# embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

# if USE_QDRANT and qclient:
#     qclient.upsert(
#         collection_name=COLLECTION,
#         points=[qmodels.PointStruct(id=i,vector=embeddings[i].tolist(),payload=INDICATORS[i]) for i in range(len(INDICATORS))]
#     )
# else:
#     faiss_index = faiss.IndexFlatL2(embeddings.shape[1])
#     faiss_index.add(embeddings.astype("float32"))

# # ================================
# # SEARCH
# # ================================
# def search_indicators(query, top_k=25, max_products=3):
#     q_vec = bi_encoder.encode([clean_text(query)], convert_to_numpy=True)
#     q_vec /= np.linalg.norm(q_vec, axis=1, keepdims=True)

#     if USE_QDRANT and qclient:
#         hits = qclient.search(collection_name=COLLECTION,query_vector=q_vec[0].tolist(),limit=top_k)
#         candidates = [h.payload for h in hits]
#     else:
#         _, I = faiss_index.search(q_vec.astype("float32"), top_k)
#         candidates = [INDICATORS[i] for i in I[0] if i >= 0]

#     scores = cross_encoder.predict([(query, c["name"] + " " + c.get("desc", "")) for c in candidates])
#     for i, c in enumerate(candidates):
#         c["score"] = float(scores[i])

#     candidates.sort(key=lambda x: x["score"], reverse=True)

#     # CPI conflict resolve ONLY if both present
#     candidates = resolve_cpi_conflict(candidates, query)

#     seen, final = set(), []
#     for c in candidates:

#         if c["parent"] not in seen:
#             seen.add(c["parent"])
#             final.append(c)
#         if len(final) == max_products:
#             break


#     return final




# ###################query capture 


# import uuid
# from datetime import datetime

# LOG_FILE = os.path.join(BASE_DIR, "logs", "queries.jsonl")

# def save_query_log(raw_query, rewritten_query, response_json):
#     os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

#     record = {
#         "id": str(uuid.uuid4()),
#         "timestamp": datetime.utcnow().isoformat(),
#         "raw_query": raw_query,
#         "rewritten_query": rewritten_query,
#         "response": response_json
#     }

#     with open(LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(json.dumps(record, ensure_ascii=False) + "\n")


# # ================================
# # FLASK
# # ================================
# app = Flask(__name__, template_folder="templates")
# CORS(app)

# @app.route("/")
# def home():
#     return render_template("index.html")

# @app.route("/predict", methods=["POST"])
# def predict():
#     raw_q = request.json.get("query", "").strip()
#     if not raw_q:
#         return jsonify({"error": "query required"}), 400

#     #  LLM rewrite
#     q = rewrite_query_with_llm(raw_q)

#     print("RAW :", raw_q)
#     print("LLM :", q)

#     top_results = search_indicators(q)
#     confidences = normalize_confidence([r["score"] for r in top_results])

#     results = []

#     for ind, conf in zip(top_results, confidences):
#         dataset = next(d for d in DATASETS if d["code"] == ind["parent"])
#         related_filters = [f for f in FILTERS if f["parent"] == ind["code"]]

#         grouped = {}
#         for f in related_filters:
#             grouped.setdefault(f["filter_name"], []).append(f)

#         best_filters = []
#         for fname, opts in grouped.items():
#             best_opt = select_best_filter_option(
#                 query=q,
#                 filter_name=fname,
#                 options=opts,
#                 cross_encoder=cross_encoder
#             )
#             best_filters.append({
#                 "filter_name": fname,
#                 "option": best_opt["option"]
#             })

#         results.append({
#             "dataset": dataset["name"],
#             "indicator": ind["name"],
#             "confidence": conf,
#             "filters": best_filters
#         })
#     response = {"results": results}
#         #  SAVE OUTPUT
#     save_query_log(
#         raw_query=raw_q,
#         rewritten_query=q,
#         response_json=response
#     )

#     #return jsonify(response)

#     return jsonify({"results": results})

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5009)






# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import os, json, re
# import numpy as np
# from sentence_transformers import SentenceTransformer, CrossEncoder
# import faiss
# from datetime import datetime
# import difflib

# # ================================
# # CONFIG
# # ================================
# USE_QDRANT = True
# try:
#     from qdrant_client import QdrantClient
#     from qdrant_client.http import models as qmodels
# except Exception:
#     USE_QDRANT = False

# # ================================
# # LLM (QUERY REWRITER ONLY)
# # ================================
# from langchain_ollama import ChatOllama

# try:
#     rewriter_llm = ChatOllama(
#         model="llama3:70b",
#         base_url="http://localhost:11434",
#         temperature=0.3
#     )

#     rewriter_llm.invoke("ping")
#     print(" Ollama is running")

# except Exception as e:
#     print(" Ollama is not running")


# # ================================
# # REGEX
# # ================================
# YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

# # ================================
# # HELPERS
# # ================================
# def clean_text(t):
#     t = (t or "").lower()
#     t = re.sub(r"[^a-z0-9\s]", " ", t)
#     return re.sub(r"\s+", " ", t).strip()

# def normalize_confidence(scores, min_conf=50, max_conf=95):
#     if not scores:
#         return []
#     mn, mx = min(scores), max(scores)
#     if mn == mx:
#         return [min_conf] * len(scores)
#     return [round(min_conf + (s - mn)/(mx - mn)*(max_conf - min_conf), 2) for s in scores]



# #########
# BASE_YEAR_PATTERN = re.compile(r"(20\d{2})")

# def detect_base_year(query):
#     q = query.lower()

#     if "base year" or " base" in q:
#         m = BASE_YEAR_PATTERN.search(q)
#         if m:
#             return int(m.group(1))

#     return None


# def resolve_cpi_conflict(results, query):
#     """
#     Only when CPI and CPI2 both present in top results
#     """
#     datasets = [r["parent"] for r in results]

#     if "CPI" not in datasets or "CPI2" not in datasets:
#         return results  # kuch mat chhedo

#     base_year = detect_base_year(query)

#     # ---------- case 1: user ne base year bola ----------
#     if base_year:
#         if base_year >= 2024:
#             # CPI2 rakho
#             return [r for r in results if r["parent"] != "CPI"]
#         else:
#             # CPI rakho
#             return [r for r in results if r["parent"] != "CPI2"]

#     # ---------- case 2: base year nahi bola ----------
#     return [r for r in results if r["parent"] != "CPI"]


# # ================================
# # LLM QUERY REWRITE
# # ================================
# def rewrite_query_with_llm(user_query):
#     prompt =  f"""
# You are a QUERY NORMALIZATION ENGINE for a data analytics system.

# Task:
# Rewrite the user query safely with controlled semantic normalization.

# STRICT RULES:
# 1. DO NOT add any new information
# 2. DO NOT infer missing filters
# 3. DO NOT assume any category
# 4. DO NOT enrich meaning
# 5. ONLY rewrite words that already exist in the query
# 6. NEVER inject new concepts
# 7. NEVER add sector/gender/state unless explicitly present
# 8. Output ONLY rewritten query
# 9. No explanation
# 10. If the query contains a known dataset short form (CPI, IIP, NAS, PLFS, ASI, HCES, NSS), append its full form in the rewritten query while keeping the short form unchanged (e.g., "CPI" → "CPI Consumer Price Index"), and do not expand anything not explicitly present.



# SPECIAL RULE (VERY IMPORTANT):

# If the query contains "IIP" and also contains any month name 
# (January–December or short forms like Jan, Feb, etc.), 
# then add the word "monthly" to the query.

# If the query contain Q1 or Q2 or Q3 or Q4 then add quarterly but do not remove Q1 or Q2 or Q3 or Q4 

# Examples:
# "IIP July data" → "IIP monthly July data"
# "IIP for December" → "IIP monthly December"
# "IIP Aug 2022" → "IIP monthly Aug 2022"

# DO NOT apply this rule to any other dataset.
# If query is about CPI, GDP, PLFS etc → do nothing.


# ALLOWED OPERATIONS:
# - spelling correction
# - grammar correction
# - casing normalization
# - synonym normalization
# - semantic mapping ONLY if the word exists explicitly in text

# CRITICAL RULE (VERY IMPORTANT):
# - If the user query is ONLY a dataset or product name
#   (examples: IIP, CPI, CPIALRL, HCES, ASI,NAS, PLFS,CPI2,ASI,),
#   then RETURN THE QUERY EXACTLY AS IT IS.
# - Dataset names must NEVER be replaced with normal English words.
# SPECIAL RULE:
# If query contains both "year" and "base year", clearly separate them:
# - "gdp for year 2023-24 base year 2022-23" → "gdp year:2023-24 base_year:2022-23"



# STRICT SEMANTIC MAP (ONLY IF WORD EXISTS):
# - gao, gaon, village → rural
# - shehar, city, metro → urban
# - purush, aadmi, mard, man, men → male
# - mahila, aurat, lady, women → female
# - ladka → male
# - ladki → female

# ❌ FORBIDDEN:
# - Do NOT infer urban from city names
# - Do NOT infer rural from state names
# - Do NOT infer gender from profession
# - Do NOT infer sector from geography
# - Do NOT add any category automatically

# Examples:
# RAW: "mens judge in village"
# → "male judge in rural"

# RAW: "Gini Coefficient for urban india in 2023-24"
# → "Gini Coefficient for urban in 2023-24"

# RAW: "factory output gujrat 2022"
# → "factory output Gujarat 2022"

# RAW: "men judges in delhi"
# → "male judges in Delhi"

# RAW: "factory output in gujrat for 2022 in gao"
# → "factory output in Gujarat for 2022 in rural"

# RAW: "data for mahila workers"
# → "data for female workers"

# RAW: "gaon ke factory worker"
# → "rural factory worker"

# RAW: "factory output in mumbai"
# → "factory output in Mumbai"

# User Query:
# "{user_query}"
# """
#     try:
#         out = rewriter_llm.invoke(prompt).content.strip()
#         out = out.replace('"', '').replace("\n", " ").strip()
#         return out
#     except:
#         return user_query

# # ================================
# # YEAR NORMALIZATION
# # ================================
# def normalize_year_string(s):
#     return re.sub(r"[^0-9]", "", str(s))


# def map_year_to_option(user_year, options):
#     y = int(user_year)
#     targets = [
#          f"{y}{y+1}",            # → "20232024"
#         f"{y}{str(y+1)[-2:]}",  # → "202324"  ← NEW!
#         f"{y-1}{y}",            # → "20222023"
#         f"{y-1}{str(y)[-2:]}",  # → "202223"  ← NEW!
#         str(y)                   # → "2023"
#     ]
#     norm_options = {normalize_year_string(o["option"]): o for o in options}
#     for t in targets:
#         if t in norm_options:
#             return norm_options[t]
#     return None

# # ================================
# # UNIVERSAL FILTER NORMALIZER
# # ================================
# def universal_filter_normalizer(ind_code, filters_json):
#     flat = []
#     def recurse(key, value):
#         if isinstance(value, list) and all(isinstance(x, str) for x in value):
#             for opt in value:
#                 flat.append({"parent": ind_code,"filter_name": key,"option": opt})
#         elif isinstance(value, list) and all(isinstance(x, dict) for x in value):
#             for item in value:
#                 for k, v in item.items():
#                     if k.lower() in ["name", "title", "label"]:
#                         flat.append({"parent": ind_code,"filter_name": key,"option": v})
#                     else:
#                         recurse(k, v)
#         elif isinstance(value, dict):
#             for k, v in value.items():
#                 recurse(k, v)

#     for f in filters_json:
#         if isinstance(f, dict):
#             for k, v in f.items():
#                 recurse(k, v)
#     return flat


# #############LLM 
# # ================================
# # SMART FILTER ENGINE
# # ================================
# def select_best_filter_option(query, filter_name, options, cross_encoder):
#     q_lower = query.lower()
#     fname_lower = filter_name.lower()

#     # =========================
#     # YEAR FILTER
#     # =========================
#     if "year" in fname_lower and "base" not in fname_lower:
#         year_match = YEAR_PATTERN.search(q_lower)
#         use_year=year_match.group(1)
#         mapped=map_year_to_option(use_year,options)

#         # user ne year nahi bola → Select All
#         if not year_match:
#             return {
#                 "parent": options[0]["parent"],
#                 "filter_name": filter_name,
#                 "option": "Select All"
#             }

#         user_year = year_match.group(1)

#         mapped = map_year_to_option(user_year, options)
#         if mapped:
#             return mapped

#         pairs = [(query, f"{filter_name} {o['option']}") for o in options]
#         scores = cross_encoder.predict(pairs)
#         return options[int(np.argmax(scores))]

#     # =========================
#     # BASE YEAR FILTER (FINAL FIX)
#     # =========================
#     if "base" in fname_lower and "year" in fname_lower:

#         # 🔹 check if user explicitly mentioned base year
#         for opt in options:
#             opt_text = str(opt["option"]).lower()
#             if opt_text in q_lower:
#                 return opt

#         # 🔹 user ne base year nahi bola → latest base year pick karo
#         def extract_start_year(opt):
#             m = re.search(r"\d{4}", str(opt["option"]))
#             return int(m.group(0)) if m else 0

#         latest = max(options, key=lambda o: extract_start_year(o))
#         return latest

#     # =========================
#     # OTHER FILTERS
#     # =========================
#     mentioned = []

#     for opt in options:
#         opt_text = str(opt.get("option", "")).lower().strip()
#         if not opt_text:
#             continue

#         if opt_text in q_lower:
#             mentioned.append(opt)
#             continue

#         for word in q_lower.split():
#             if difflib.SequenceMatcher(None, opt_text, word).ratio() > 0.70:
#                 mentioned.append(opt)
#                 break

#     if mentioned:
#         pairs = [(query, f"{filter_name} {o['option']}") for o in mentioned]
#         scores = cross_encoder.predict(pairs)
#         return mentioned[int(np.argmax(scores))]

#     return {
#         "parent": options[0]["parent"],
#         "filter_name": filter_name,
#         "option": "Select All"
#     }


# # ================================
# # LOAD PRODUCTS
# # ================================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PRODUCTS_FILE = os.path.join(BASE_DIR, "products", "products.json")

# with open(PRODUCTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
#     raw_products = json.load(f)

# DATASETS, INDICATORS, FILTERS = [], [], []

# for ds_name, ds_info in raw_products.get("datasets", {}).items():
#     DATASETS.append({"code": ds_name, "name": ds_name})

#     for ind in ds_info.get("indicators", []):
#         ind_code = f"{ds_name}_{ind['name']}"
#         INDICATORS.append({
#             "code": ind_code,
#             "name": ind["name"],
#             "desc": ind.get("description", ""),
#             "parent": ds_name
#         })

#         flat = universal_filter_normalizer(ind_code, ind.get("filters", []))
#         FILTERS.extend(flat)

# print(f"[INFO] DATASETS={len(DATASETS)}, INDICATORS={len(INDICATORS)}, FILTERS={len(FILTERS)}")

# # ================================
# # MODELS
# # ================================
# bi_encoder = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
# cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")

# # ================================
# # VECTOR DB
# # ================================
# VECTOR_DIM = bi_encoder.get_sentence_embedding_dimension()
# COLLECTION = "indicators_collection"

# qclient = None
# faiss_index = None

# if USE_QDRANT:
#     try:
#         qclient = QdrantClient(url="http://localhost:6333")
#         if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
#             qclient.recreate_collection(
#                 collection_name=COLLECTION,
#                 vectors_config=qmodels.VectorParams(size=VECTOR_DIM,distance=qmodels.Distance.COSINE)
#             )
#         print("[INFO] Qdrant ready")
#     except Exception as e:
#         USE_QDRANT = False
#         print("[WARN] Qdrant failed, using FAISS:", e)

# names = [clean_text(i["name"]) for i in INDICATORS]
# descs = [clean_text(i.get("desc", "")) for i in INDICATORS]

# embeddings = (0.4 * bi_encoder.encode(names, convert_to_numpy=True) + 0.6 * bi_encoder.encode(descs, convert_to_numpy=True))
# embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

# if USE_QDRANT and qclient:
#     qclient.upsert(
#         collection_name=COLLECTION,
#         points=[qmodels.PointStruct(id=i,vector=embeddings[i].tolist(),payload=INDICATORS[i]) for i in range(len(INDICATORS))]
#     )
# else:
#     faiss_index = faiss.IndexFlatL2(embeddings.shape[1])
#     faiss_index.add(embeddings.astype("float32"))

# # ================================
# # SEARCH
# # ================================
# def search_indicators(query, top_k=25, max_products=3):
#     q_vec = bi_encoder.encode([clean_text(query)], convert_to_numpy=True)
#     q_vec /= np.linalg.norm(q_vec, axis=1, keepdims=True)

#     if USE_QDRANT and qclient:
#         hits = qclient.search(collection_name=COLLECTION,query_vector=q_vec[0].tolist(),limit=top_k)
#         candidates = [h.payload for h in hits]
#     else:
#         _, I = faiss_index.search(q_vec.astype("float32"), top_k)
#         candidates = [INDICATORS[i] for i in I[0] if i >= 0]

#     scores = cross_encoder.predict([(query, c["name"] + " " + c.get("desc", "")) for c in candidates])
#     for i, c in enumerate(candidates):
#         c["score"] = float(scores[i])

#     candidates.sort(key=lambda x: x["score"], reverse=True)

#     # CPI conflict resolve ONLY if both present
#     candidates = resolve_cpi_conflict(candidates, query)

#     seen, final = set(), []
#     for c in candidates:

#         if c["parent"] not in seen:
#             seen.add(c["parent"])
#             final.append(c)
#         if len(final) == max_products:
#             break


#     return final




# ###################query capture 


# import uuid
# from datetime import datetime

# LOG_FILE = os.path.join(BASE_DIR, "logs", "queries.jsonl")

# def save_query_log(raw_query, rewritten_query, response_json):
#     os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

#     record = {
#         "id": str(uuid.uuid4()),
#         "timestamp": datetime.utcnow().isoformat(),
#         "raw_query": raw_query,
#         "rewritten_query": rewritten_query,
#         "response": response_json
#     }

#     with open(LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(json.dumps(record, ensure_ascii=False) + "\n")


# # ================================
# # FLASK
# # ================================
# app = Flask(__name__, template_folder="templates")
# CORS(app)

# @app.route("/")
# def home():
#     return render_template("index.html")

# @app.route("/predict", methods=["POST"])
# def predict():
#     raw_q = request.json.get("query", "").strip()
#     if not raw_q:
#         return jsonify({"error": "query required"}), 400

#     #  LLM rewrite
#     q = rewrite_query_with_llm(raw_q)

#     print("RAW :", raw_q)
#     print("LLM :", q)

#     top_results = search_indicators(q)
#     confidences = normalize_confidence([r["score"] for r in top_results])

#     results = []

#     for ind, conf in zip(top_results, confidences):
#         dataset = next(d for d in DATASETS if d["code"] == ind["parent"])
#         related_filters = [f for f in FILTERS if f["parent"] == ind["code"]]

#         grouped = {}
#         for f in related_filters:
#             grouped.setdefault(f["filter_name"], []).append(f)

#         best_filters = []
#         for fname, opts in grouped.items():
#             best_opt = select_best_filter_option(
#                 query=q,
#                 filter_name=fname,
#                 options=opts,
#                 cross_encoder=cross_encoder
#             )
#             best_filters.append({
#                 "filter_name": fname,
#                 "option": best_opt["option"]
#             })

#         results.append({
#             "dataset": dataset["name"],
#             "indicator": ind["name"],
#             "confidence": conf,
#             "filters": best_filters
#         })
#     response = {"results": results}
#         #  SAVE OUTPUT
#     save_query_log(
#         raw_query=raw_q,
#         rewritten_query=q,
#         response_json=response
#     )

#     #return jsonify(response)

#     return jsonify({"results": results})

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5009)






from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os, json, re
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss
from datetime import datetime
import difflib

# ================================
# CONFIG
# ================================
USE_QDRANT = True
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:
    USE_QDRANT = False

# ================================
# LLM (QUERY REWRITER ONLY)
# ================================
from langchain_ollama import ChatOllama

try:
    rewriter_llm = ChatOllama(
        model="llama3:70b",
        base_url="http://localhost:11434",
        temperature=0.3
    )
    rewriter_llm.invoke("ping")
    OLLAMA_IS_RUNNING = True
    print(" Ollama is running")
except Exception as e:
    OLLAMA_IS_RUNNING = False
    print(" Ollama is not running")


# ================================
# REGEX
# ================================
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

# ================================
# HELPERS
# ================================
def clean_text(t):
    """Text ko lowercase karke special chars hatao, sirf a-z 0-9 space rakho. Embedding/search ke liye normalize."""
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def normalize_confidence(scores, min_conf=50, max_conf=95):
    """Scores ko min_conf se max_conf range mein scale karo. Sab indicators ko 50-95% confidence range mein map."""
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mn == mx:
        return [min_conf] * len(scores)
    return [round(min_conf + (s - mn)/(mx - mn)*(max_conf - min_conf), 2) for s in scores]



#########
BASE_YEAR_PATTERN = re.compile(r"(20\d{2})")

def detect_base_year(query):
    """Query mein base year (20xx) detect karo. CPI/CPI2 conflict resolve ke liye use hota hai."""
    q = query.lower()

    if "base year" or " base" in q:
        m = BASE_YEAR_PATTERN.search(q)
        if m:
            return int(m.group(1))

    return None


def resolve_cpi_conflict(results, query):
    """Jab CPI aur CPI2 dono top results mein hon: base year 2024+ → CPI2 rakho, else CPI rakho. Default: CPI2."""
    # Only when CPI and CPI2 both present in top results
    datasets = [r["parent"] for r in results]

    if "CPI" not in datasets or "CPI2" not in datasets:
        return results  # kuch mat chhedo

    base_year = detect_base_year(query)

    # ---------- case 1: user ne base year bola ----------
    if base_year:
        if base_year >= 2024:
            # CPI2 rakho
            return [r for r in results if r["parent"] != "CPI"]
        else:
            # CPI rakho
            return [r for r in results if r["parent"] != "CPI2"]

    # ---------- case 2: base year nahi bola ----------
    return [r for r in results if r["parent"] != "CPI"]


# ================================
# LLM QUERY REWRITE
# ================================
def rewrite_query_with_llm(user_query):
    """Ollama LLM se query normalize/rewrite karo (spelling, synonyms, dataset full form). Fail → raw query return."""
    prompt =  f"""
You are a QUERY NORMALIZATION ENGINE for a data analytics system.

Task:
Rewrite the user query safely with controlled semantic normalization.

STRICT RULES:
1. DO NOT add any new information
2. DO NOT infer missing filters
3. DO NOT assume any category
4. DO NOT enrich meaning
5. ONLY rewrite words that already exist in the query
6. NEVER inject new concepts
7. NEVER add sector/gender/state unless explicitly present
8. Output ONLY rewritten query
9. No explanation
10. If the query contains a known dataset short form (CPI, IIP, NAS, PLFS, ASI, HCES, NSS, EC, WPI, UDISE, ASUSE, Gender, AISHE, ESI, CPIALRL, ENVSTAT, NFHS, RBI, NSS79, NSS79C, EC4, EC5, EC6, NSS77, NSS78), append its full form in the rewritten query while keeping the short form unchanged (e.g., "CPI" → "CPI Consumer Price Index", "EC" → "EC Economic Census", "WPI" → "WPI Wholesale Price Index", "UDISE" → "UDISE Unified District Information System for Education Plus"), and do not expand anything not explicitly present.



SPECIAL RULE (VERY IMPORTANT):

If the query contains "IIP" and also contains any month name 
(January–December or short forms like Jan, Feb, etc.), 
then add the word "monthly" to the query.

If query contains both "year" and "base year", clearly separate them:


Examples:
"IIP July data" → "IIP monthly July data"
"IIP for December" → "IIP monthly December"
"IIP Aug 2022" → "IIP monthly Aug 2022"
"gdp for year 2023-24 base year 2022-23" → "gdp year:2023-24 base_year:2022-23"

DO NOT apply this rule to any other dataset.
If query is about CPI, GDP, PLFS etc → do nothing.


ALLOWED OPERATIONS:
- spelling correction
- grammar correction
- casing normalization
- synonym normalization
- semantic mapping ONLY if the word exists explicitly in text

CRITICAL RULE (VERY IMPORTANT):
- If the user query is ONLY a dataset or product name
  (examples: IIP, CPI, CPIALRL, HCES, ASI, NAS, PLFS, CPI2, EC, EC4, EC5, EC6, WPI, UDISE, ASUSE, Gender, AISHE, ESI, ENVSTAT, NFHS, RBI, NSS79, NSS79C, NSS77, NSS78),
  then: RETURN THE QUERY WITH ITS FULL FORM APPENDED (e.g. "EC4" -> "EC4 4th Economic Census").
- Dataset names must NEVER be replaced with normal English words.


STRICT SEMANTIC MAP (ONLY IF WORD EXISTS):
- gao, gaon, village → rural
- shehar, city, metro → urban
- purush, aadmi, mard, man, men → male
- mahila, aurat, lady, women → female
- ladka → male
- ladki → female

❌ FORBIDDEN:
- Do NOT infer urban from city names
- Do NOT infer rural from state names
- Do NOT infer gender from profession
- Do NOT infer sector from geography
- Do NOT add any category automatically

Examples:
RAW: "mens judge in village"
→ "male judge in rural"

RAW: "Gini Coefficient for urban india in 2023-24"
→ "Gini Coefficient for urban in 2023-24"

RAW: "factory output gujrat 2022"
→ "factory output Gujarat 2022"

RAW: "men judges in delhi"
→ "male judges in Delhi"

RAW: "factory output in gujrat for 2022 in gao"
→ "factory output in Gujarat for 2022 in rural"

RAW: "data for mahila workers"
→ "data for female workers"

RAW: "gaon ke factory worker"
→ "rural factory worker"

RAW: "factory output in mumbai"
→ "factory output in Mumbai"

User Query:
"{user_query}"
"""
    if not OLLAMA_IS_RUNNING:
        return user_query
    
    try:
        out = rewriter_llm.invoke(prompt).content.strip()
        out = out.replace('"', '').replace("\n", " ").strip()
        return out
    except:
        return user_query

# ================================
# YEAR NORMALIZATION
# ================================
def normalize_year_string(s):
    """String se sirf digits nikalo (e.g. '2023-24' → '202324'). Year matching ke liye."""
    return re.sub(r"[^0-9]", "", str(s))


def map_year_to_option(user_year, options, query=None):
    """User year (e.g. 2023) ko options (2023-24, 2022-23, etc.) mein map karo.
    Also handles CPIALRL 'YYYY-YYYY' format and month-aware fiscal year mapping.
    Match nahi → None."""
    y = int(user_year)
    
    # --- Month-aware fiscal year mapping for CPIALRL ---
    # If query has a month and the options are in "YYYY-YYYY" format (CPIALRL),
    # months Jan-Mar belong to previous fiscal year
    # e.g., "February 2011" → fiscal year "2010-2011"
    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]
    q_lower = (query or "").lower()
    is_jan_mar = any(m in q_lower for m in ["january", "february", "march"])
    
    # Check if options use "YYYY-YYYY" format (CPIALRL style)
    has_long_fy = any("-" in str(o.get("option", "")) and len(re.sub(r'[^0-9]', '', str(o.get("option", "")))) >= 8
                      for o in options[:3])
    
    targets = [
        f"{y}{y+1}",            # → "20232024"  (CPIALRL: "2023-2024")
        f"{y}{str(y+1)[-2:]}",  # → "202324"    (IIP: "2023-24")
        f"{y-1}{y}",            # → "20222023"  (CPIALRL: "2022-2023")
        f"{y-1}{str(y)[-2:]}",  # → "202223"    (IIP: "2022-23")
        str(y)                   # → "2023"      (CPI, IIP Monthly plain year)
    ]
    
    # For CPIALRL with Jan-Mar months, prioritize previous fiscal year
    if is_jan_mar and has_long_fy:
        targets = [
            f"{y-1}{y}",            # → "20102011" for Feb 2011
            f"{y-1}{str(y)[-2:]}",  # → "201011"
            f"{y}{y+1}",            # fallback
            f"{y}{str(y+1)[-2:]}",
            str(y)
        ]
    
    norm_options = {normalize_year_string(o["option"]): o for o in options}
    for t in targets:
        if t in norm_options:
            return norm_options[t]
    return None

# ================================
# FILTER ACCURACY & ESSENTIAL FILTERS (Moth criteria)
# Filter Accuracy = 4 filters only: Year, Sector, Gender, State (when present, must appear first)
# Essential Filters Accuracy = CPI: Series, Base Year; IIP: Base Year; ASI: Classification Year;
#                             NAS: Series, Frequency; CPIALRL: Base Year (when present, must appear)
# ================================
# 4 filters - Filter Accuracy basis
MANDATORY_4 = ["Year", "Sector", "Gender", "State"]

# Essential filters per dataset - Essential Filters Accuracy basis
ESSENTIAL_FILTERS_BY_DATASET = {
    "CPI": ["Series", "Base_Year", "Division"],
    "CPI2": ["Series", "Base_Year", "Division"],
    "IIP": ["Base_Year", "Frequency", "Type", "Category"],
    "ASI": ["classification_year"],
    "NAS": ["Series", "Frequency"],
    "CPIALRL": ["Base_Year"],
    "PLFS": ["Frequency"],
    "TUS": ["Age Group", "ICATUS Activity", "Day Of Week"],
    "WPI": ["Base_Year", "Major Group", "Group"],
    "ESI": ["Use of Energy Balance", "Energy Commodities"],
    "ASUSE": ["Frequency", "Sector"],
    "Gender": ["Gender", "State"],
    "AISHE": ["University Type", "State"],
    "NSS77": ["Sector", "State"],
    "NSS78": ["Sector", "State"],
    "HCES": ["Sector", "State"],
    "ENVSTAT": ["Category", "State"],
    "NFHS": ["Indicator Category", "State"],
    "EC4": ["State", "Sector", "Establishment Type"],
    "EC5": ["State", "Sector", "Establishment Type"],
    "EC6": ["State", "Sector", "Establishment Type"],
    "RBI": ["Bank Name", "Frequency"],
    "NSS79": ["Sector", "State"],
    "NSS79C": ["Sector", "State"],
    "UDISE": ["Management", "School Category", "State"],
}

# Datasets where Year/financial_Year filter should NOT be forced
_SKIP_YEAR_FILTER_DATASETS = {"NSS77", "NSS78", "EC4", "EC5", "EC6"}


def _priority_order_for_dataset(parent_code):
    """Filter ka priority order banao: Year,Sector,Gender,State pehle, phir dataset essential (Series,Base_Year,etc.), phir rest."""
    order = ["Year", "financial_Year", "Sector", "Gender", "State"]
    essential = ESSENTIAL_FILTERS_BY_DATASET.get(parent_code, [])
    for e in essential:
        if e not in order:
            order.append(e)
    for k in ["Base_Year", "Series", "classification_year", "Frequency"]:
        if k not in order:
            order.append(k)
    return order


def ensure_mandatory_filter_order(best_filters, parent_code):
    """best_filters ko Moth criteria ke hisaab se reorder: 4 filters first, phir essential, phir baaki. Sirf reorder, kuch add/remove nahi."""
    if not best_filters:
        return best_filters
    by_name = {f["filter_name"]: f for f in best_filters}
    ordered = []
    priority = _priority_order_for_dataset(parent_code)
    for key in priority:
        if key in by_name:
            ordered.append(by_name.pop(key))
    for f in best_filters:
        if f["filter_name"] in by_name:
            ordered.append(by_name.pop(f["filter_name"]))
    for v in by_name.values():
        ordered.append(v)
    return ordered


def ensure_required_filters_present(best_filters, parent_code, grouped, query, cross_encoder):
    """Jo required filters (4 + essential) grouped mein hain lekin best_filters mein nahi, unko add karo. Phir sahi order apply karo."""
    required = list(MANDATORY_4)
    required.extend(ESSENTIAL_FILTERS_BY_DATASET.get(parent_code, []))
    required = list(dict.fromkeys(required))
    out_names = {f["filter_name"]: f for f in best_filters}
    for r in required:
        if r in out_names:
            continue
        # Golden rule: Skip Year/financial_Year for datasets that don't have it
        if r in ("Year", "financial_Year") and parent_code in _SKIP_YEAR_FILTER_DATASETS:
            continue
        if r not in grouped:
            continue
        opts = grouped[r]
        if not opts:
            continue
        best_opt = select_best_filter_option(query, r, opts, cross_encoder)
        best_filters.append({"filter_name": r, "option": best_opt["option"]})
        out_names[r] = best_filters[-1]
    # Golden rule: For _SKIP_YEAR_FILTER_DATASETS, REMOVE Year if it was added by generic filter loop
    if parent_code in _SKIP_YEAR_FILTER_DATASETS:
        best_filters = [f for f in best_filters if f["filter_name"] not in ("Year", "financial_Year")]
    best_filters = ensure_mandatory_filter_order(best_filters, parent_code)
    # Golden rule: CPI-only. Series+Base_Year valid combos: (Current,2012), (Back,2010)
    best_filters = ensure_cpi_series_base_year_consistent(best_filters, parent_code, grouped, query)
    return best_filters


def ensure_cpi_series_base_year_consistent(best_filters, parent_code, grouped, query):
    """CPI/CPI2 ke liye Series+Base_Year valid combo ensure karo: Current↔2012, Back↔2010. Mismatch ho to fix. Baaki datasets pe no-op."""
    if parent_code not in ("CPI", "CPI2"):
        return best_filters
    by_name = {f["filter_name"]: f for f in best_filters}
    if "Series" not in by_name or "Base_Year" not in by_name:
        return best_filters
    q_lower = query.lower()
    series_opt = str(by_name["Series"].get("option", "")).lower()
    base_opt = str(by_name["Base_Year"].get("option", "")).lower()
    base_year = re.search(r"20\d{2}", base_opt)
    base_year = base_year.group(0) if base_year else ""
    target_series, target_base = None, None
    if "back" in q_lower or "2010" in q_lower:
        target_series, target_base = "Back", "2010"
    elif "current" in q_lower or "2012" in q_lower:
        target_series, target_base = "Current", "2012"
    elif series_opt == "back" and base_year and base_year != "2010":
        target_series, target_base = "Back", "2010"
    elif series_opt == "current" and base_year and base_year != "2012":
        target_series, target_base = "Current", "2012"
    elif base_year == "2010" and series_opt != "back":
        target_series, target_base = "Back", "2010"
    elif base_year == "2012" and series_opt != "current":
        target_series, target_base = "Current", "2012"
    elif not base_year and series_opt == "current":
        target_base = "2012"
    elif not base_year and series_opt == "back":
        target_base = "2010"
    if not target_series and not target_base:
        return best_filters
    series_opts = grouped.get("Series", [])
    base_opts = grouped.get("Base_Year", [])
    if target_series:
        for opt in series_opts:
            if str(opt.get("option", "")).lower() == target_series.lower():
                by_name["Series"]["option"] = opt["option"]
                break
    if target_base:
        for opt in base_opts:
            if target_base in str(opt.get("option", "")):
                by_name["Base_Year"]["option"] = opt["option"]
                break
    return best_filters


# ================================
# UNIVERSAL FILTER NORMALIZER
# ================================
def universal_filter_normalizer(ind_code, filters_json):
    """products.json ke nested filters ko flat list mein convert karo: [{parent, filter_name, option}, ...]. Nested dict/list recurse karta hai."""
    flat = []
    def recurse(key, value):
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            for opt in value:
                flat.append({"parent": ind_code,"filter_name": key,"option": opt})
        elif isinstance(value, list) and all(isinstance(x, dict) for x in value):
            for item in value:
                for k, v in item.items():
                    if k.lower() in ["name", "title", "label"]:
                        flat.append({"parent": ind_code,"filter_name": key,"option": v})
                    else:
                        recurse(k, v)
        elif isinstance(value, dict):
            for k, v in value.items():
                recurse(k, v)

    for f in filters_json:
        if isinstance(f, dict):
            for k, v in f.items():
                recurse(k, v)
    return flat


#############LLM 
# ================================
# SMART FILTER ENGINE
# ================================
def select_best_filter_option(query, filter_name, options, cross_encoder):
    """Query ke hisaab se sabse sahi filter option pick karo. Year→Select All/latest, Series→Current/Back, State/Sector→match, etc."""
    if not options:
        return {"parent": "", "filter_name": filter_name, "option": "Select All"}
    q_lower = query.lower()
    fname_lower = filter_name.lower()
     
    # =========================
    # FREQUENCY FILTER
    # =========================
    if fname_lower in ["frequency"]:
        # --- Check for explicit mention ---
        for keyword in ["annually", "quarterly", "monthly", "annual"]:
            if keyword in q_lower:
                for opt in options:
                    o = str(opt.get("option", "")).lower()
                    if o.startswith(keyword) or keyword.startswith(o):
                        return opt

        # --- Month names → Monthly (full names only to avoid "may" false positive) ---
        month_names = [
            "january", "february", "march", "april", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        if any(m in q_lower for m in month_names):
            for opt in options:
                o = str(opt.get("option", "")).lower()
                if o in ["monthly", "month"]:
                    return opt

        # --- Quarter keywords → Quarterly ---
        quarter_keywords = ["quarter", "quarterly", "q1", "q2", "q3", "q4",
                            "jul-sep", "oct-dec", "jan-mar", "apr-jun"]
        if any(qk in q_lower for qk in quarter_keywords):
            for opt in options:
                if str(opt.get("option", "")).lower() in ["quarterly"]:
                    return opt

        # --- Year format "2023-24" or standalone year → Annually ---
        if re.search(r"\d{4}[-/]\d{2,4}", q_lower) or YEAR_PATTERN.search(q_lower):
            for opt in options:
                if str(opt.get("option", "")).lower() in ["annually", "annual"]:
                    return opt

        # --- No frequency clue → Select All ---
        return {
            "parent": options[0]["parent"],
            "filter_name": filter_name,
            "option": "Select All"
        }
    # =========================
    # YEAR FILTER (Year, financial_Year)
    # User mention nahi kiya → Select All (agar hai), else latest year
    # User mention kiya → exact year
    # Golden rule: When query has both "base year XXXX" and data year,
    # pick the data year, not the base year
    # =========================
    if "year" in fname_lower and "base" not in fname_lower:
        # --- Extract all years from query (include 19xx and 20xx for IIP/CPIALRL) ---
        _ANY_YEAR_PAT = re.compile(r"\b((?:19|20)\d{2})\b")
        all_years = _ANY_YEAR_PAT.findall(q_lower)

        # --- Separate base year from data year ---
        # If query contains "base" keyword, the year right after "base" is the base year
        base_year_in_query = None
        data_years = []
        if all_years:
            # Find years that appear near "base" keyword
            base_pattern = re.search(r'base[_ ]?(?:year)?[:\s]*(?:of\s+)?(?:year\s+)?(\d{4})', q_lower)
            if base_pattern:
                base_year_in_query = base_pattern.group(1)
            # Also check for "(Base XXXX-XX)" pattern like "(Base 2011-12)"
            base_paren = re.search(r'\(\s*base\s+(\d{4})', q_lower)
            if base_paren:
                base_year_in_query = base_paren.group(1)
            # Data years = all years minus the base year
            for y in all_years:
                if y != base_year_in_query:
                    data_years.append(y)
            # If no data years found (all years were base year), use all years
            if not data_years:
                data_years = all_years
        
        # --- Also handle financial year format "YYYY-YY" in query ---
        fy_match = re.search(r'(\d{4})[-/](\d{2,4})', q_lower)
        fy_year = None
        if fy_match:
            fy_str = fy_match.group(0)
            # Make sure this isn't a base year pattern
            before_fy = q_lower[:fy_match.start()].rstrip()
            if not before_fy.endswith('base') and 'base_year' not in before_fy[-15:]:
                fy_year = fy_match.group(1)

        # --- Quarter-aware fiscal year mapping (Golden rule: PLFS/other FY datasets) ---
        # Jan-Mar 2024 → FY 2023-24 (Q4 of previous FY)
        # Apr-Jun 2024 → FY 2024-25 (Q1)
        # Jul-Sep 2024 → FY 2024-25 (Q2)
        # Oct-Dec 2024 → FY 2024-25 (Q3)
        quarter_q4 = re.search(r'(?:jan(?:uary)?[\s\-]+mar(?:ch)?|q4)', q_lower)
        if quarter_q4 and data_years and not fy_year:
            qy = int(data_years[0])
            # Jan-Mar of year Y belongs to FY (Y-1)-(Y)
            adjusted_year = str(qy - 1)
            mapped = map_year_to_option(adjusted_year, options, query=query)
            if mapped:
                return mapped

        if not all_years and not fy_year:
            # User ne year nahi bola → Select All agar options mein hai, else latest year
            for opt in options:
                o = str(opt.get("option", "")).strip().lower()
                if o in ("select all", "selectall"):
                    return opt
            # Select All nahi hai → latest/current year return karo
            def _extract_year_val(o):
                m = re.search(r"20\d{2}", str(o.get("option", "")))
                return int(m.group(0)) if m else 0
            return max(options, key=lambda o: _extract_year_val(o))

        # Prefer financial year format if present and not base year
        if fy_year and fy_year not in (base_year_in_query or ""):
            mapped = map_year_to_option(fy_year, options, query=query)
            if mapped:
                return mapped

        # Use data year (excluding base year)
        user_year = data_years[0] if data_years else (all_years[0] if all_years else None)
        if user_year:
            mapped = map_year_to_option(user_year, options, query=query)
            if mapped:
                return mapped

        pairs = [(query, f"{filter_name} {o['option']}") for o in options]
        scores = cross_encoder.predict(pairs)
        return options[int(np.argmax(scores))]

    # =========================
    # SERIES FILTER (CPI, NAS - Current/Back)
    # =========================
    if fname_lower == "series":
        if "back" in q_lower or "historical" in q_lower:
            for opt in options:
                if str(opt.get("option", "")).lower() == "back":
                    return opt
        if "current" in q_lower:
            for opt in options:
                if str(opt.get("option", "")).lower() == "current":
                    return opt
        for opt in options:
            if str(opt.get("option", "")).lower() == "current":
                return opt
        return options[0] if options else {"parent": "", "filter_name": filter_name, "option": "Select All"}

    # =========================
    # CLASSIFICATION YEAR (ASI)
    # Golden rule: ASI-only. Options are NIC years: 2008, 2004, 1998, 1987
    # If user mentions "NIC 2004" or "NIC-2004" → pick 2004
    # If user mentions "NIC 2008" → pick 2008
    # Default → latest (2008)
    # =========================
    if fname_lower == "classification_year":
        # Check for explicit NIC year mention like "NIC 2004", "NIC-2004", "NIC2004"
        nic_match = re.search(r'nic[\s\-_]*(\d{4})', q_lower)
        if nic_match:
            nic_year = nic_match.group(1)
            for opt in options:
                if str(opt.get("option", "")).strip() == nic_year:
                    return opt
        # Check for explicit mention of classification year value
        for opt in options:
            opt_text = str(opt.get("option", "")).strip()
            # Only match if the year appears as "classification year XXXX" or standalone mention
            if opt_text in q_lower:
                # Avoid matching data years (e.g., "2022-23") with classification options
                # by checking it's not part of a range
                idx = q_lower.find(opt_text)
                after = q_lower[idx + len(opt_text):idx + len(opt_text) + 1] if idx + len(opt_text) < len(q_lower) else ""
                if after not in ("-", "/"):  # Not a range like "2004-05"
                    return opt
        # Default → latest classification year (2008 for NIC)
        def _extract_year(opt):
            m = re.search(r"\d{4}", str(opt.get("option", "")))
            return int(m.group(0)) if m else 0
        return max(options, key=lambda o: _extract_year(o))

    # =========================
    # BASE YEAR FILTER (FINAL FIX)
    # Golden rule: Product-specific defaults
    # NAS: default "2011-12" unless data year >= 2023 → "2022-23"
    # IIP: default based on data year range
    #   pre-2005 → "1993-94", 2005-2011 → "2004-05", 2012+ → "2011-12"
    # CPI: handled by ensure_cpi_series_base_year_consistent
    # Others: latest base year
    # =========================
    if "base" in fname_lower and "year" in fname_lower:

        # 🔹 check if user explicitly mentioned base year ("base year 2011-12" or "base 1993-94")
        base_explicit = re.search(r'base[_ ]?(?:year)?[:\s]*(\d{4}(?:[-/]\d{2,4})?)', q_lower)
        if base_explicit:
            base_val = base_explicit.group(1)
            for opt in options:
                opt_text = str(opt.get("option", "")).lower().strip()
                if base_val in opt_text or opt_text in base_val:
                    return opt
                # Normalize both and compare
                norm_base = re.sub(r'[^0-9]', '', base_val)
                norm_opt = re.sub(r'[^0-9]', '', opt_text)
                if norm_base and norm_opt and (norm_base.startswith(norm_opt) or norm_opt.startswith(norm_base)):
                    return opt

        # Check for standalone base year value in query
        for opt in options:
            opt_text = str(opt.get("option", "")).lower().strip()
            if opt_text in q_lower:
                return opt

        # 🔹 Smart defaults per dataset (Golden rule: each product isolated)
        parent_code = options[0].get("parent", "").split("_")[0] if options else ""

        def extract_start_year(opt):
            m = re.search(r"\d{4}", str(opt.get("option", "")))
            return int(m.group(0)) if m else 0

        # --- NAS: default 2011-12 unless query year >= 2023 ---
        if parent_code == "NAS":
            # Find data year from query
            data_year_match = YEAR_PATTERN.search(q_lower)
            data_year = int(data_year_match.group(1)) if data_year_match else 0
            target_base = "2022-23" if data_year >= 2023 else "2011-12"
            for opt in options:
                if target_base in str(opt.get("option", "")):
                    return opt

        # --- IIP: default based on data year range ---
        if parent_code == "IIP":
            _ANY_YEAR_PAT_IIP = re.compile(r"\b((?:19|20)\d{2})\b")
            # Get all years from query, pick the first non-base-year
            all_q_years = _ANY_YEAR_PAT_IIP.findall(q_lower)
            # Remove years that are part of "base YYYY" pattern
            base_yr_match = re.search(r'base[_ ]?(?:year)?[:\s]*(\d{4})', q_lower)
            base_yr = base_yr_match.group(1) if base_yr_match else None
            data_yr = None
            for yr in all_q_years:
                if yr != base_yr:
                    data_yr = int(yr)
                    break
            if data_yr is None and all_q_years:
                data_yr = int(all_q_years[0])
            if data_yr:
                if data_yr < 2005:
                    target = "1993-94"
                elif data_yr < 2012:
                    target = "2004-05"
                else:
                    target = "2011-12"
                for opt in options:
                    if target in str(opt.get("option", "")):
                        return opt
            # No data year → default to latest (2011-12)
            for opt in options:
                if "2011" in str(opt.get("option", "")):
                    return opt

        # 🔹 Other datasets: latest base year
        latest = max(options, key=lambda o: extract_start_year(o))
        return latest

    # =========================
    # MONTH FILTER (WPI, IIP etc - calendar month: January, February, ...)
    # =========================
    if fname_lower == "month":
        month_map = [
            ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"),
            ("may", "may"), ("june", "jun"), ("july", "jul"), ("august", "aug"),
            ("september", "sep"), ("october", "oct"), ("november", "nov"), ("december", "dec")
        ]
        for full, short in month_map:
            if full in q_lower or short in q_lower:
                for opt in options:
                    if str(opt.get("option", "")).lower() == full or str(opt.get("option", "")).lower().startswith(full[:3]):
                        return opt
        return {
            "parent": options[0]["parent"],
            "filter_name": filter_name,
            "option": "Select All"
        }

    # =========================
    # PRODUCT-SPECIFIC FILTERS (Isolation)
    # =========================
    if fname_lower in ["management", "school category"]:
        # UDISE specific
        for opt in options:
            if str(opt.get("option", "")).lower() in q_lower:
                return opt
    if fname_lower in ["university type", "name of univ type"]:
        # AISHE specific
        for opt in options:
            if str(opt.get("option", "")).lower() in q_lower:
                return opt
    if fname_lower == "indicator category":
        # ENVSTAT, NFHS specific
        for opt in options:
            if str(opt.get("option", "")).lower() in q_lower:
                return opt
    if fname_lower in ["major group", "group"]:
        # WPI specific
        for opt in options:
            if str(opt.get("option", "")).lower() in q_lower:
                return opt

    # =========================
    # OTHER FILTERS
    # =========================
    mentioned = []

    for opt in options:
        opt_text = str(opt.get("option", "")).lower().strip()
        if not opt_text:
            continue

        if opt_text in q_lower:
            mentioned.append(opt)
            continue

        for word in q_lower.split():
            if difflib.SequenceMatcher(None, opt_text, word).ratio() > 0.80:
                mentioned.append(opt)
                break

    if mentioned:
        pairs = [(query, f"{filter_name} {o['option']}") for o in mentioned]
        scores = cross_encoder.predict(pairs)
        return mentioned[int(np.argmax(scores))]

    # Golden rule: Find the best default "All" option if no specific match
    for opt in options:
        o_lower = str(opt.get("option", "")).lower().strip()
        if o_lower in ["select all", "selectall", "all", "person", "combined", "general", "total"] or o_lower.startswith("all "):
            return opt
            
    # As a last resort, just return the first available valid option instead of a fake string
    return options[0]


# ================================
# LOAD PRODUCTS
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
if not os.path.exists(PRODUCTS_FILE):
    PRODUCTS_FILE = os.path.join(BASE_DIR, "products", "products.json")
if not os.path.exists(PRODUCTS_FILE):
    raise FileNotFoundError(f"products.json not found. Tried: {BASE_DIR}/products.json and {BASE_DIR}/products/products.json")

with open(PRODUCTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
    raw_products = json.load(f)

DATASETS, INDICATORS, FILTERS = [], [], []

for ds_name, ds_info in raw_products.get("datasets", {}).items():
    DATASETS.append({"code": ds_name, "name": ds_name})

    for ind in ds_info.get("indicators", []):
        ind_code = f"{ds_name}_{ind['name']}"
        INDICATORS.append({
            "code": ind_code,
            "name": ind["name"],
            "desc": ind.get("description", ""),
            "parent": ds_name
        })

        flat = universal_filter_normalizer(ind_code, ind.get("filters", []))
        FILTERS.extend(flat)

print(f"[INFO] DATASETS={len(DATASETS)}, INDICATORS={len(INDICATORS)}, FILTERS={len(FILTERS)}")

# ================================
# MODELS
# ================================
bi_encoder = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")

# ================================
# VECTOR DB
# ================================
VECTOR_DIM = bi_encoder.get_sentence_embedding_dimension()
COLLECTION = "indicators_collection"

qclient = None
faiss_index = None

if USE_QDRANT:
    try:
        qclient = QdrantClient(url="http://localhost:6333")
        if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
            qclient.recreate_collection(
                collection_name=COLLECTION,
                vectors_config=qmodels.VectorParams(size=VECTOR_DIM,distance=qmodels.Distance.COSINE)
            )
        print("[INFO] Qdrant ready")
    except Exception as e:
        USE_QDRANT = False
        print("[WARN] Qdrant failed, using FAISS:", e)

names = [clean_text(i["name"]) for i in INDICATORS]
descs = [clean_text(i.get("desc", "")) for i in INDICATORS]

print("[INFO] Building FAISS semantic embeddings for 1360 indicators... (Takes 1-2 mins on CPU)")
embeddings_names = bi_encoder.encode(names, convert_to_numpy=True, show_progress_bar=True)
embeddings_descs = bi_encoder.encode(descs, convert_to_numpy=True, show_progress_bar=True)
embeddings = (0.4 * embeddings_names + 0.6 * embeddings_descs)
embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

if USE_QDRANT and qclient:
    qclient.upsert(
        collection_name=COLLECTION,
        points=[qmodels.PointStruct(id=i,vector=embeddings[i].tolist(),payload=INDICATORS[i]) for i in range(len(INDICATORS))]
    )
else:
    faiss_index = faiss.IndexFlatL2(embeddings.shape[1])
    faiss_index.add(embeddings.astype("float32"))

# ================================
# SEARCH
# ================================
def search_indicators(query, top_k=25, max_products=3):
    """Query ke hisaab se semantic search karo (Qdrant/FAISS). Cross-encoder rerank, CPI conflict resolve. Har dataset se max 1 indicator. Top max_products return."""
    q_vec = bi_encoder.encode([clean_text(query)], convert_to_numpy=True)
    q_vec /= np.linalg.norm(q_vec, axis=1, keepdims=True)

    if USE_QDRANT and qclient:
        hits = qclient.search(collection_name=COLLECTION,query_vector=q_vec[0].tolist(),limit=top_k)
        candidates = [h.payload for h in hits]
    else:
        _, I = faiss_index.search(q_vec.astype("float32"), top_k)
        candidates = [INDICATORS[i] for i in I[0] if i >= 0]

    scores = cross_encoder.predict([(query, c["name"] + " " + c.get("desc", "")) for c in candidates])
    for i, c in enumerate(candidates):
        c["score"] = float(scores[i])

    candidates.sort(key=lambda x: x["score"], reverse=True)

    # CPI conflict resolve ONLY if both present
    candidates = resolve_cpi_conflict(candidates, query)

    seen, final = set(), []
    for c in candidates:

        if c["parent"] not in seen:
            seen.add(c["parent"])
            final.append(c)
        if len(final) == max_products:
            break


    return final


def _search_dataset_only(query, parent_codes):
    """Sirf given dataset(s) ke indicators mein search karo. Best matching indicator return, nahi mile to None."""
    if isinstance(parent_codes, str):
        parent_codes = (parent_codes,)
    indicators = [i.copy() for i in INDICATORS if i["parent"] in parent_codes]
    if not indicators:
        return None
    pairs = [(query, c["name"] + " " + c.get("desc", "")) for c in indicators]
    scores = cross_encoder.predict(pairs)
    for i, c in enumerate(indicators):
        c["score"] = float(scores[i])
    return max(indicators, key=lambda x: x["score"])


def _search_wpi_only(query):
    """WPI dataset ke andar sirf search karo. Force-include ke liye use hota hai."""
    return _search_dataset_only(query, "WPI")


def _search_ec_only(query):
    """EC4/EC5/EC6 ke andar search karo. Economic Census force-include ke liye."""
    return _search_dataset_only(query, ("EC4", "EC5", "EC6"))


###################query capture 


import uuid
from datetime import datetime

LOG_FILE = os.path.join(BASE_DIR, "logs", "queries.jsonl")

def save_query_log(raw_query, rewritten_query, response_json):
    """Har search request ko logs/queries.jsonl mein append karo (raw query, rewritten, response). Debug/analytics ke liye."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "raw_query": raw_query,
        "rewritten_query": rewritten_query,
        "response": response_json
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ================================
# FLASK
# ================================
app = Flask(__name__, template_folder="templates")
CORS(app)

@app.route("/")
def home():
    """Home page - search UI render karo."""
    return render_template("index.html")

@app.route("/search/predict", methods=["POST"])
def predict():
    """Main API: query receive karo, LLM rewrite, semantic search, filter selection, results + filters return. Top 3 datasets."""
    raw_q = request.json.get("query", "").strip()
    if not raw_q:
        return jsonify({"error": "query required"}), 400

    #  LLM rewrite
    q = rewrite_query_with_llm(raw_q)

    # 1. Fallback Expansions for all 22 products
    dataset_expansions = {
        r'\bplfs\b': "Periodic Labour Force Survey",
        r'\basuse\b': "Annual Survey of Unincorporated Sector Enterprises",
        r'\basi\b': "Annual Survey of Industries",
        r'\btus\b': "Time Use Survey",
        r'\bgender\b': "Gender Statistics",
        r'\baishe\b': "All India Survey on Higher Education",
        r'\bnss77\b': "NSS 77th Round AIDIS",
        r'\bnss78\b': "NSS 78th Round Domestic Tourism",
        r'\besi\b': "Energy Statistics India",
        r'\bcpialrl\b': "Consumer Price Index for Agricultural and Rural Labourers",
        r'\bhces\b': "Household Consumption Expenditure Survey",
        r'\benvstat\b': "Environment Statistics India",
        r'\bnfhs\b': "National Family Health Survey",
        r'\bec4\b': "4th Economic Census",
        r'\bec5\b': "5th Economic Census",
        r'\bec6\b': "6th Economic Census",
        r'\biip\b': "Index of Industrial Production",
        r'\bwpi\b': "Wholesale Price Index",
        r'\bcpi\b': "Consumer Price Index",
        r'\bnas\b': "National Accounts Statistics",
        r'\brbi\b': "Reserve Bank of India Banking Statistics",
        r'\bnss79c?\b': "Comprehensive Annual Modular Survey CAMS",
        r'\budise\b': "Unified District Information System for Education Plus"
    }
    for pat, exp in dataset_expansions.items():
        if re.search(pat, q.lower()) and exp.lower() not in q.lower():
            q = f"{q} {exp}"

    print("RAW :", raw_q)
    print("LLM :", q)

    top_results = search_indicators(q)

    # 2. Force-Inclusion Logic (Isolation) - STRIcT CONTEXT
    _force_ds_map = {
        r'\bplfs\b|unemployment rate|labour force|lfpr|wpr|\bworker population ratio\b': ["PLFS"],
        r'\basuse\b|unincorporated|unorganized': ["ASUSE"],
        r'\basi\b|annual survey of industries|factory output|fixed capital|gross output|workers in factory': ["ASI"],
        r'\btus\b|time use survey|unpaid caregiving|domestic services': ["TUS"],
        r'\bgender\b|sex ratio': ["Gender"],
        r'\baishe\b|higher education|college|university': ["AISHE"],
        r'\bnss77\b|debt|investment|land|livestock': ["NSS77"],
        r'\bnss78\b|tourism': ["NSS78"],
        r'\besi\b|energy statistics|electricity|power supply': ["ESI"],
        r'\bcpialrl\b|agricultural labo|rural labo': ["CPIALRL"],
        r'\bhces\b|consumption expenditure|mpce': ["HCES"],
        r'\benvstat\b|environment statistics|forest cover|hazardous waste': ["ENVSTAT"],
        r'\bnfhs\b|family health|immunization|fertility|antenatal care|stunted|wasted|anemia': ["NFHS"],
        r'\bec4\b|4th economic census': ["EC4"],
        r'\bec5\b|5th economic census': ["EC5"],
        r'\bec6\b|6th economic census': ["EC6"],
        r'\biip\b|industrial production|mining index|manufacturing index|electricity index': ["IIP"],
        r'\bwpi\b|wholesale price': ["WPI"],
        r'\bcpi\b|consumer price|retail price|retail inflation': ["CPI", "CPI2"],
        r'\bnas\b|national accounts|gdp|gva': ["NAS"],
        r'\brbi\b|reserve bank|lending rate|exchange rate|forex|external debt|rupee vis-a-vis': ["RBI"],
        r'\bnss79c?\b|cams|modular survey': ["NSS79C", "NSS79"],
        r'\budise\b|school education|unified district': ["UDISE"]
    }
    
    _raw_lower = raw_q.lower().strip()
    _forced = None
    # Check for specific codes first
    for pat, codes in _force_ds_map.items():
        if re.search(pat, _raw_lower):
            _forced = codes
            break
            
    if _forced and not any(r["parent"] in _forced for r in top_results):
        ds_best = _search_dataset_only(q or raw_q, _forced)
        if ds_best:
            top_results = [ds_best] + [r for r in top_results if r["parent"] != ds_best["parent"]][:2]
            ds_best["score"] = max(r["score"] for r in top_results) + 1  # Boost to 1st

    # 3. Prioritization Logic (Isolation)
    # If the user query matches a dataset pattern, ensure it is ranked first
    _ds_priority = None
    for pat, codes in _force_ds_map.items():
        if re.search(pat, _raw_lower):
            _ds_priority = codes
            break
            
    if _ds_priority:
        for i, r in enumerate(top_results):
            if r["parent"] in _ds_priority:
                if i > 0:
                    top_results = [r] + [x for x in top_results if x["parent"] != r["parent"]][:2]
                top_results[0]["score"] = max(x["score"] for x in top_results) + 1
                break
    if _ds_priority:
        for i, r in enumerate(top_results):
            if r["parent"] in _ds_priority:
                if i > 0:
                    top_results = [r] + [x for x in top_results if x["parent"] != r["parent"]][:2]
                    r = top_results[0]
                # Boost 95% confidence (whether moved or already 1st)
                all_scores = [x["score"] for x in top_results]
                top_results[0]["score"] = max(all_scores) + 1
                break

    confidences = normalize_confidence([r["score"] for r in top_results])

    results = []

    for ind, conf in zip(top_results, confidences):
        dataset = next(d for d in DATASETS if d["code"] == ind["parent"])
        related_filters = [f for f in FILTERS if f["parent"] == ind["code"]]

        grouped = {}
        for f in related_filters:
            grouped.setdefault(f["filter_name"], []).append(f)

        best_filters = []
        for fname, opts in grouped.items():
            best_opt = select_best_filter_option(
                query=q,
                filter_name=fname,
                options=opts,
                cross_encoder=cross_encoder
            )
            best_filters.append({
                "filter_name": fname,
                "option": best_opt["option"]
            })
        # Filter Accuracy (4) + Essential (CPI/IIP/ASI/NAS/CPIALRL): ensure present & order
        best_filters = ensure_required_filters_present(best_filters, ind["parent"], grouped, q, cross_encoder)

        results.append({
            "dataset": dataset["name"],
            "product": dataset["code"].lower(),  # ec4, ec5, ec6 - for URL (macroindicators?product=ec4)
            "indicator": ind["name"],
            "confidence": conf,
            "filters": best_filters
        })
    response = {"results": results}
        #  SAVE OUTPUT
    save_query_log(
        raw_query=raw_q,
        rewritten_query=q,
        response_json=response
    )

    #return jsonify(response)

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5009)
