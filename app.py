import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

# -----------------------------
# Configuration and local data
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / ".env")

API_BASE_URL = "https://api.crustdata.com"
API_HEADERS = {
    "Authorization": f"Bearer {os.getenv('CRUSTDATA_API_KEY', '')}",
    "Content-Type": "application/json",
    "x-api-version": "2025-11-01",
}

st.set_page_config(
    page_title="SupplyChain Intelligence",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_json(path: Path, fallback: Any) -> Any:
    """Read a JSON file and report file/format errors in Streamlit."""
    if not path.exists():
        st.error(f"Required file not found: {path}")
        return fallback
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Could not load {path.name}: {exc}")
        return fallback


bom = load_json(DATA_DIR / "bom.json", {"product": "EV Battery Pack", "components": []})
supply_data = load_json(DATA_DIR / "supply_chain.json", {"companies": [], "relationships": []})
if not isinstance(bom, dict):
    bom = {"product": "EV Battery Pack", "components": []}
if not isinstance(supply_data, dict):
    supply_data = {"companies": [], "relationships": []}
companies = supply_data.get("companies", [])
relationships = supply_data.get("relationships", [])
if not isinstance(companies, list):
    companies = []
if not isinstance(relationships, list):
    relationships = []
components = bom.get("components", [])
if not isinstance(components, list):
    components = []


# -----------------------------
# Crustdata API functions
# -----------------------------
def crustdata_post(endpoint: str, payload: Dict[str, Any]) -> Any:
    """POST to Crustdata and return parsed JSON or a readable error."""
    api_key = os.getenv("CRUSTDATA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CRUSTDATA_API_KEY is missing. Add it to .env in the project root.")

    headers = dict(API_HEADERS)
    headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            headers=headers,
            json=payload,
            timeout=45,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Crustdata: {exc}") from exc

    if not response.ok:
        raise RuntimeError(f"Crustdata HTTP {response.status_code}: {response.text[:1200]}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Crustdata returned invalid JSON.") from exc


def search_company(domain: str) -> Optional[Dict[str, Any]]:
    """Find one company using an exact primary-domain filter."""
    domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not domain:
        raise ValueError("Enter a company domain.")
    payload = {
        "filters": {
            "op": "and",
            "conditions": [{
                "field": "basic_info.primary_domain",
                "type": "=",
                "value": domain,
            }],
        },
        "fields": ["basic_info.name", "basic_info.primary_domain"],
        "limit": 1,
    }
    data = crustdata_post("/company/search", payload)
    results = data.get("companies", []) if isinstance(data, dict) else []
    if not results and isinstance(data, dict) and isinstance(data.get("data"), list):
        results = data["data"]
    return results[0] if results else None


def extract_company_id(record: Dict[str, Any]) -> Optional[int]:
    company_id = record.get("crustdata_company_id")
    if company_id is None and isinstance(record.get("basic_info"), dict):
        company_id = record["basic_info"].get("crustdata_company_id")
    try:
        return int(company_id) if company_id is not None else None
    except (TypeError, ValueError):
        return None


def enrich_company(company_id: int) -> Dict[str, Any]:
    """Fetch basic information, headcount and locations for a company ID."""
    payload = {
        "crustdata_company_ids": [int(company_id)],
        "fields": ["basic_info", "headcount", "locations"],
    }
    data = crustdata_post("/company/enrich", payload)
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and isinstance(data.get("data"), list):
        records = data["data"]
    elif isinstance(data, dict) and isinstance(data.get("companies"), list):
        records = data["companies"]
    else:
        records = [data]

    # Tested Crustdata response shape: records -> matches -> company_data.
    for record in records:
        if not isinstance(record, dict):
            continue
        matches = record.get("matches")
        if isinstance(matches, list) and matches and isinstance(matches[0], dict):
            company_data = matches[0].get("company_data")
            if isinstance(company_data, dict):
                return company_data
        company_data = record.get("company_data")
        if isinstance(company_data, dict):
            return company_data
        if any(key in record for key in ("basic_info", "headcount", "locations")):
            return record
    return data if isinstance(data, dict) else {"raw_response": data}


def discover_and_enrich(domain: str) -> Dict[str, Any]:
    search_result = search_company(domain)
    if not search_result:
        raise RuntimeError(f"No company found for domain: {domain}")
    company_id = extract_company_id(search_result)
    if company_id is None:
        raise RuntimeError("Company was found, but Crustdata did not return its company ID.")
    return {
        "search_result": search_result,
        "company_id": company_id,
        "enriched_data": enrich_company(company_id),
    }


def live_web_search(query: str) -> List[Dict[str, Any]]:
    if not query.strip():
        raise ValueError("Enter a search query.")
    data = crustdata_post("/web/search/live", {"query": query.strip(), "sources": ["web"]})
    results = data.get("results", []) if isinstance(data, dict) else []
    return results if isinstance(results, list) else []


# -----------------------------
# Relationship and BOM helpers
# -----------------------------
MATERIAL_KEYWORDS = {
    "Lithium": ["lithium"],
    "Nickel": ["nickel"],
    "Cobalt": ["cobalt"],
    "Graphite": ["graphite"],
    "Aluminium": ["aluminium", "aluminum"],
    "Steel": ["steel"],
    "Semiconductors": ["semiconductor", "semiconductors", "chip", "chips"],
    "PCBs": ["pcb", "printed circuit"],
    "Copper": ["copper"],
}
HISTORICAL_STATUSES = {"cancelled", "canceled", "expired", "dissolved", "terminated", "inactive"}


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def status_of(record: Dict[str, Any]) -> str:
    return str(record.get("status", "Unspecified")).strip()


def is_active(record: Dict[str, Any]) -> bool:
    return status_of(record).lower() == "active"


def is_historical(record: Dict[str, Any]) -> bool:
    return status_of(record).lower() in HISTORICAL_STATUSES


def keywords_for(material: str) -> List[str]:
    return MATERIAL_KEYWORDS.get(material, [material.lower()])


def candidate_companies(material: str) -> List[Dict[str, Any]]:
    keywords = keywords_for(material)
    return [
        company for company in companies
        if any(word in norm(company.get("role", "")) for word in keywords)
    ]


def supplier_records_for_material(supplier: str, material: str) -> List[Dict[str, Any]]:
    keywords = keywords_for(material)
    return [
        record for record in relationships
        if norm(record.get("supplier")) == norm(supplier)
        and any(word in norm(record.get("material", "")) for word in keywords)
    ]


def compact_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    basic = profile.get("basic_info") or {}
    headcount = profile.get("headcount") or {}
    locations = profile.get("locations") or {}
    if not isinstance(basic, dict):
        basic = {}
    if not isinstance(headcount, dict):
        headcount = {}
    if not isinstance(locations, dict):
        locations = {}
    return {
        "name": basic.get("name", "Not available"),
        "domain": basic.get("primary_domain", "Not available"),
        "description": basic.get("description", "Not available"),
        "company_type": basic.get("company_type", "Not available"),
        "year_founded": basic.get("year_founded", "Not available"),
        "employee_count_range": basic.get("employee_count_range", "Not available"),
        "headcount_total": headcount.get("total", "Not available"),
        "headquarters": locations.get("headquarters", "Not available"),
        "website": basic.get("website", ""),
        "linkedin": basic.get("professional_network_url", ""),
    }


# -----------------------------
# Page header and sidebar
# -----------------------------
st.title("🔗 SupplyChain Intelligence")
st.caption("Multi-Tier Supplier Mapping & BOM Risk Agent | EV Battery Pack demonstration")
st.write(
    "Map a product's bill of materials, discover relevant companies, inspect "
    "supplier relationship evidence, and identify gaps in the available data."
)

with st.sidebar:
    st.header("Project Overview")
    st.write(f"**Product:** {bom.get('product', 'Not specified')}")
    st.write(f"**Companies mapped:** {len(companies)}")
    st.write(f"**Relationship records:** {len(relationships)}")
    st.divider()
    if os.getenv("CRUSTDATA_API_KEY", "").strip():
        st.success("Crustdata API key detected")
    else:
        st.warning("Crustdata API key not detected")
    st.caption("Local data: data/bom.json and data/supply_chain.json")


# -----------------------------
# 1. Product overview and BOM
# -----------------------------
st.header("1. Product Overview")
all_materials = {
    str(material)
    for component in components
    for material in component.get("materials", [])
}
col1, col2, col3 = st.columns(3)
col1.metric("BOM Components", len(components))
col2.metric("Unique Materials", len(all_materials))
col3.metric("Mapped Companies", len(companies))

st.subheader("Bill of Materials (BOM)")
if components:
    bom_rows = [
        {
            "Component": component.get("component", "Not specified"),
            "Materials": ", ".join(component.get("materials", [])),
        }
        for component in components
    ]
    st.dataframe(bom_rows, use_container_width=True, hide_index=True)
else:
    st.info("No BOM components found in data/bom.json.")


# -----------------------------
# 2. Company intelligence
# -----------------------------
st.header("2. Company Intelligence")
if companies:
    company_rows = [{
        "Company": company.get("name", "Unknown"),
        "Role": company.get("role", "Not specified"),
        "Crustdata ID": company.get("crustdata_company_id", "Not available"),
        "Domain": company.get("domain", "Not available"),
    } for company in companies]
    st.dataframe(company_rows, use_container_width=True, hide_index=True)
else:
    st.info("No companies are mapped in data/supply_chain.json.")


# -----------------------------
# 3. Live supply-chain research
# -----------------------------
st.header("3. Live Supply Chain Research")
st.write("Search public web sources through Crustdata. Treat results as research leads until the original source is checked.")
query = st.text_input("Research query", value="Albemarle Ford lithium supply agreement", key="research_query")
if st.button("Search live web", key="live_search_button"):
    try:
        with st.spinner("Searching through Crustdata..."):
            st.session_state["web_results"] = live_web_search(query)
            st.session_state["web_query"] = query
    except Exception as exc:
        st.error(str(exc))

if "web_results" in st.session_state:
    st.caption(f"Results for: {st.session_state.get('web_query', '')}")
    results = st.session_state["web_results"]
    if results:
        for index, result in enumerate(results, 1):
            if not isinstance(result, dict):
                continue
            title = result.get("title") or result.get("name") or f"Search result {index}"
            snippet = result.get("snippet") or result.get("description") or result.get("content") or "No summary returned."
            url = result.get("url") or result.get("link") or result.get("original_url") or ""
            with st.container(border=True):
                st.markdown(f"**{index}. {title}**")
                st.write(snippet)
                if str(url).startswith(("http://", "https://")):
                    st.markdown(f"[Open source]({url})")
                else:
                    st.caption("No source URL returned.")
    else:
        st.info("No web results were returned.")


# -----------------------------
# 4. Supplier relationship records
# -----------------------------
st.header("4. Supplier Relationship Records")
st.write("Company capability and a commercial relationship are different things. The records below come from data/supply_chain.json.")
if relationships:
    for index, record in enumerate(relationships, 1):
        supplier = record.get("supplier", "Not specified")
        customer = record.get("customer", "Not specified")
        material = record.get("material", "Not specified")
        rel_type = record.get("relationship_type", "Not specified")
        period = record.get("period", "Not specified")
        quantity = record.get("quantity", "Not specified")
        status = status_of(record)
        source = str(record.get("source", ""))
        with st.container(border=True):
            st.markdown(f"**Relationship record {index}**")
            left, right = st.columns(2)
            left.metric("Supplier", supplier)
            right.metric("Customer", customer)
            a, b = st.columns(2)
            a.write(f"**Material / Product:** {material}")
            a.write(f"**Relationship type:** {rel_type}")
            b.write(f"**Agreement period:** {period}")
            b.write(f"**Quantity:** {quantity}")
            if is_active(record):
                st.success(f"Status: {status}")
            elif is_historical(record):
                st.warning(f"Status: {status}")
            else:
                st.info(f"Status: {status}")
            if source.startswith(("http://", "https://")):
                st.markdown(f"[View supporting evidence]({source})")
            else:
                st.caption("No supporting evidence URL recorded.")
else:
    st.info("No supplier relationship records found.")


# -----------------------------
# 5. Supplier relationship network
# -----------------------------
st.header("5. Supplier Relationship Network")
if relationships:
    graph = [
        "digraph SupplyChain {",
        'rankdir="LR";',
        'graph [bgcolor="transparent", pad="0.25", nodesep="0.55", ranksep="0.9"];',
        'node [shape=box, style="rounded,filled", fillcolor="#EAF2F8", color="#3B6C8E", fontname="Arial"];',
        'edge [fontname="Arial", fontsize="10", color="#667788"];',
    ]
    endpoints = set()
    for record in relationships:
        endpoints.add(str(record.get("supplier", "Unknown supplier")))
        endpoints.add(str(record.get("customer", "Unknown customer")))

    # Use stable generated node identifiers; escape quotes in visible labels.
    node_ids = {}
    for index, name in enumerate(sorted(endpoints)):
        node_id = f"company_{index}"
        node_ids[name] = node_id
        label = name.replace('"', "'")
        graph.append(f'"{node_id}" [label="{label}"];')

    for record in relationships:
        supplier = str(record.get("supplier", "Unknown supplier"))
        customer = str(record.get("customer", "Unknown customer"))
        edge_label = f"{record.get('material', '')} | {status_of(record)}".replace('"', "'")
        graph.append(f'"{node_ids[supplier]}" -> "{node_ids[customer]}" [label="{edge_label}"];')
    graph.append("}")
    st.graphviz_chart("\n".join(graph), use_container_width=True)
    st.caption("All recorded relationships are displayed, including cancelled, expired, and dissolved records. Check the edge status.")
else:
    st.info("Add relationship records to data/supply_chain.json to build the network.")


# -----------------------------
# 6. Supply-chain risk assessment
# -----------------------------
st.header("6. Supply Chain Risk Assessment")
active_relationships = [record for record in relationships if is_active(record)]
historical_relationships = [record for record in relationships if is_historical(record)]
other_relationships = [record for record in relationships if not is_active(record) and not is_historical(record)]

r1, r2, r3 = st.columns(3)
r1.metric("Active Relationships", len(active_relationships))
r2.metric("Historical / Inactive", len(historical_relationships))
r3.metric("Total Relationship Records", len(relationships))

st.subheader("Material Supplier Coverage")
st.caption("Candidate matches use company role descriptions. They are not proof of an actual buyer-supplier relationship.")
if components:
    for component in components:
        with st.expander(component.get("component", "Unnamed component"), expanded=True):
            for material in component.get("materials", []):
                candidates = candidate_companies(material)
                active_names, historical_names, candidate_names = [], [], []
                for company in candidates:
                    name = company.get("name", "Unknown company")
                    matched = supplier_records_for_material(name, material)
                    if any(is_active(record) for record in matched):
                        active_names.append(name)
                    elif any(is_historical(record) for record in matched):
                        historical_names.append(name)
                    else:
                        candidate_names.append(name)
                st.markdown(f"**{material}**")
                if active_names:
                    st.success("Active relationship record: " + ", ".join(active_names))
                if historical_names:
                    st.warning("Historical / inactive relationship record: " + ", ".join(historical_names))
                if candidate_names:
                    st.info("Candidate companies (relationship not confirmed): " + ", ".join(candidate_names))
                if not candidates:
                    st.error("No mapped candidate company found for this material.")
else:
    st.info("No BOM components available for material coverage analysis.")


# -----------------------------
# 7. Supplier dependency indicators
# -----------------------------
st.subheader("Supplier Dependency Indicators")
supplier_counts: Dict[str, int] = {}
for record in active_relationships:
    supplier = record.get("supplier")
    if supplier:
        supplier_counts[supplier] = supplier_counts.get(supplier, 0) + 1
if supplier_counts:
    dependency_rows = [
        {"Supplier": supplier, "Active relationship records": count}
        for supplier, count in sorted(supplier_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    st.dataframe(dependency_rows, use_container_width=True, hide_index=True)
    st.caption("This counts active records in the local dataset. It is not a market-share, spend, or volume concentration calculation.")
else:
    st.info("No active supplier relationship records are currently mapped.")


# -----------------------------
# 8. Historical relationship alerts
# -----------------------------
st.subheader("Historical Relationship Alerts")
if historical_relationships:
    for record in historical_relationships:
        st.warning(
            f"{record.get('supplier', 'Unknown supplier')} → "
            f"{record.get('customer', 'Unknown customer')}: {status_of(record)} "
            f"relationship ({record.get('material', 'material not specified')}). "
            "Do not treat this as an active supply link."
        )
else:
    st.success("No cancelled, expired, or dissolved relationship records found.")


# -----------------------------
# 9. Data coverage
# -----------------------------
st.header("7. Data Coverage")
coverage1, coverage2, coverage3, coverage4 = st.columns(4)
coverage1.metric("Companies", len(companies))
coverage2.metric("Relationship Records", len(relationships))
coverage3.metric("Active", len(active_relationships))
coverage4.metric("Historical / Inactive", len(historical_relationships))
st.write("**Relationship status breakdown**")
st.write(f"- Active: {len(active_relationships)}")
st.write(f"- Historical / inactive: {len(historical_relationships)}")
st.write(f"- Other / unspecified: {len(other_relationships)}")
if relationships:
    st.progress(len(active_relationships) / len(relationships))
    st.caption(f"{len(active_relationships)} of {len(relationships)} relationship records are marked active in the local dataset.")
else:
    st.caption("No relationship records are available to calculate coverage.")


# -----------------------------
# 10. Automated company discovery
# -----------------------------
st.header("8. Automated Company Discovery")
st.write("Enter a company's primary domain. The app searches Crustdata and then requests an enriched company profile.")
domain_input = st.text_input("Company domain", placeholder="e.g. albemarle.com", key="company_domain")
if st.button("Discover and enrich company", key="discover_enrich_button"):
    if not domain_input.strip():
        st.warning("Enter a company domain first.")
    else:
        try:
            with st.spinner("Searching and enriching company data..."):
                result = discover_and_enrich(domain_input)
            st.session_state["last_discovery"] = {
                "company_id": result["company_id"],
                "profile": compact_profile(result["enriched_data"]),
                "raw": result["enriched_data"],
            }
        except Exception as exc:
            st.error(str(exc))

if "last_discovery" in st.session_state:
    discovered = st.session_state["last_discovery"]
    profile = discovered["profile"]
    st.subheader("Discovered Company Profile")
    st.write(f"**Crustdata Company ID:** {discovered['company_id']}")
    left, right = st.columns(2)
    with left:
        st.write(f"**Company:** {profile['name']}")
        st.write(f"**Domain:** {profile['domain']}")
        st.write(f"**Company type:** {profile['company_type']}")
        st.write(f"**Year founded:** {profile['year_founded']}")
        st.write(f"**Employee range:** {profile['employee_count_range']}")
    with right:
        st.write(f"**Enriched headcount:** {profile['headcount_total']}")
        st.write(f"**Headquarters:** {profile['headquarters']}")
        if profile["website"].startswith("http"):
            st.markdown(f"[Company website]({profile['website']})")
        if profile["linkedin"].startswith("http"):
            st.markdown(f"[LinkedIn profile]({profile['linkedin']})")
    with st.expander("Company description"):
        st.write(profile["description"])
    with st.expander("Raw Crustdata enrichment response"):
        st.json(discovered["raw"])


# -----------------------------
# Footer and limitations
# -----------------------------
st.divider()
st.subheader("Important Data Notes")
st.markdown(
    """
    - Company profiles and role descriptions help identify potential supply-chain participants; they do not independently establish a buyer-supplier relationship.
    - Relationship status is read from the local records in `data/supply_chain.json`.
    - Mark a relationship active only when supporting evidence establishes that it is currently active.
    - Cancelled, expired, and dissolved records are retained for historical context and are not current supplier links.
    - Live web search results are research leads. Review the original source before changing relationship records.
    - The risk indicators are based on the available dataset; they are not a complete quantitative assessment of real-world supply-chain risk.
    """
)
st.caption("SupplyChain Intelligence | ContextCon Agentic Services Hackathon")
