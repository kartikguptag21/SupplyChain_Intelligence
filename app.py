import os
import requests
from dotenv import load_dotenv
import json
import streamlit as st
from pathlib import Path

load_dotenv()
API_KEY = os.getenv("CRUSTDATA_API_KEY")

def search_company(domain):

    url = "https://api.crustdata.com/company/search"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "x-api-version": "2025-11-01"
    }

    payload = {
        "filters": {
            "op": "and",
            "conditions": [
                {
                    "field": "basic_info.primary_domain",
                    "type": "=",
                    "value": domain
                }
            ]
        },
        "fields": [
            "basic_info.name",
            "basic_info.primary_domain"
        ],
        "limit": 1
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()

def enrich_company(company_id):

    url = "https://api.crustdata.com/company/enrich"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "x-api-version": "2025-11-01"
    }

    payload = {
        "crustdata_company_ids": [company_id],
        "fields": [
            "basic_info",
            "headcount",
            "locations"
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    enriched_companies = []

    for result in data:
        for match in result.get("matches", []):
            company = match.get("company_data", {})

            basic = company.get("basic_info", {})
            headcount = company.get("headcount", {})

            enriched_companies.append({
                "name": basic.get("name"),
                "domain": basic.get("primary_domain"),
                "headcount": headcount.get("total"),
                "company_data": company
            })

    return enriched_companies

def discover_and_enrich(domain):

    search_result = search_company(domain)

    companies_found = search_result.get("companies", [])

    if not companies_found:
        return []

    enriched_results = []

    for company in companies_found:

        company_id = company.get("crustdata_company_id")

        if company_id:

            profiles = enrich_company(company_id)

            enriched_results.extend(profiles)

    return enriched_results

# -----------------------------
# PAGE CONFIGURATION
# -----------------------------

st.set_page_config(
    page_title="SupplyChain Intelligence",
    page_icon="🔗",
    layout="wide"
)

# -----------------------------
# LOAD DATA
# -----------------------------

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "data" / "bom.json", "r", encoding="utf-8") as f:
    bom = json.load(f)

with open(BASE_DIR / "data" / "supply_chain.json", "r", encoding="utf-8") as f:
    supply_data = json.load(f)

companies = supply_data["companies"]
relationships = supply_data["relationships"]

# -----------------------------
# HEADER
# -----------------------------

st.title("🔗 SupplyChain Intelligence")
st.caption(
    "Multi-tier supplier mapping and Bill of Materials risk intelligence"
)

st.divider()

# -----------------------------
# PRODUCT OVERVIEW
# -----------------------------

st.subheader("Product Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Product", bom["product"])
col2.metric("Components", len(bom["components"]))
col3.metric("Identified Companies", len(companies))

# -----------------------------
# BILL OF MATERIALS
# -----------------------------

st.divider()
st.header("1. Bill of Materials")

for component in bom["components"]:
    with st.expander(component["component"], expanded=True):
        st.write("Materials:")
        st.write(", ".join(component["materials"]))


# -----------------------------
# LIVE SUPPLY CHAIN RESEARCH
# -----------------------------

st.divider()
st.header("Live Supply Chain Research")

st.write(
    "Enter a product or material to discover relevant "
    "companies and supply-chain information."
)

with st.form("research_form"):

    research_query = st.text_input(
        "What do you want to research?",
        placeholder="e.g. Lithium suppliers for EV battery manufacturers"
    )

    domains_input = st.text_input(
        "Candidate company domains (comma separated)",
        placeholder="e.g. albemarle.com, ford.com"
    )

    submitted = st.form_submit_button("Run Research")

if submitted:
    if not research_query.strip():
        st.warning("Please enter a research query.")

    elif not API_KEY:
        st.error("Crustdata API key not found. Check your .env file.")

    else:
        with st.spinner("Researching supply chain..."):

            url = "https://api.crustdata.com/web/search/live"

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "x-api-version": "2025-11-01"
            }

            payload = {
                "query": research_query,
                "sources": ["web"]
            }

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )

                st.write(
                    "Credits used:",
                    response.headers.get("X-Credits-Used", "Not reported")
                )

                response.raise_for_status()

                results = response.json().get("results", [])

                st.subheader("Research Results")

                if not results:
                    st.info("No results found.")

                for i, item in enumerate(results, start=1):
                    with st.container(border=True):
                        st.write(f"**{i}. {item.get('title', 'Untitled')}**")
                        st.write(item.get("snippet", "No description available."))

                        result_url = item.get("url")

                        if result_url:
                            st.markdown(
                                f"[Open original source]({result_url})"
                            )

                st.caption(
                    "Search results are research leads. "
                    "Supplier relationships require separate verification."
                )

                # Discover and enrich candidate companies

                domains = [
                    d.strip()
                    for d in domains_input.split(",")
                    if d.strip()
                    ]

                if domains:

                    st.subheader("Discovered Company Profiles")

                    for domain in domains:

                        try:
                            profiles = discover_and_enrich(domain)

                            if profiles:

                                for company in profiles:

                                    st.markdown("---")
                                    st.subheader(company["name"])

                                    col1, col2 = st.columns(2)

                                    col1.metric(
                                        "Headcount",
                                        company["headcount"] or "Not available"
                                    )

                                    col2.write("**Domain:**")
                                    col2.write(company["domain"])

                                    st.write(
                                        company["company_data"]
                                        .get("basic_info", {})
                                        .get("description", "No description available.")
                                    )

                            else:
                                st.warning(f"No company found for {domain}")

                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to enrich {domain}: {e}")

            except requests.exceptions.RequestException as e:
                st.error(f"Research request failed: {e}")

# -----------------------------
# COMPANY PROFILES
# -----------------------------

st.divider()
st.header("2. Identified Companies")

for company in companies:
    with st.container(border=True):
        st.subheader(company["name"])
        col1, col2 = st.columns(2)

        col1.write("**Role:** " + company["role"])
        col1.write("**Domain:** " + company["domain"])
        col2.write("**Company ID:** " + str(company["id"]))
        col2.write("**Headquarters:** " + company["headquarters"])

# -----------------------------
# VERIFIED SUPPLIER RELATIONSHIPS
# -----------------------------

st.subheader("Verified Supplier Relationships")

if relationships:
    for relationship in relationships:
        col1, col2 = st.columns(2)

        col1.metric("Supplier", relationship["supplier"])
        col2.metric("Customer", relationship["customer"])

        st.write("**Material:**", relationship["material"])
        st.write("**Agreement period:**", relationship["period"])
        st.write("**Quantity:**", relationship["quantity"])

        st.success("Status: " + relationship["status"])

        st.markdown(
            f"[View official evidence]({relationship['source']})"
        )
# -----------------------------
# SUPPLIER RELATIONSHIP GRAPH
# -----------------------------

st.divider()
st.header("3. Supplier Network")

if relationships:
    graph = """
    digraph SupplyChain {
        rankdir=LR;
        node [shape=box, style=rounded, fontname="Arial"];

    """

    for company in companies:
        graph += f'"{company["name"]}" [label="{company["name"]}\\n{company["role"]}"];'

    for relation in relationships:
        supplier = relation["supplier"]
        customer = relation["customer"]
        material = relation["material"]

        graph += (
            f'"{supplier}" -> "{customer}" '
            f'[label="{material}\\n{relation["status"]}"];'
        )

    graph += "}"

    st.graphviz_chart(graph, use_container_width=True)

    # Relationship details
    st.subheader("Relationship Evidence")

    for relation in relationships:
        with st.container(border=True):
            st.write(
                f'**{relation["supplier"]} → {relation["customer"]}**'
            )
            st.write("Material:", relation["material"])
            st.write("Status:", relation["status"])
            st.write("Agreement period:", relation["period"])
            st.write("Quantity:", relation["quantity"])

            st.link_button(
                "View Original Source",
                relation["source"]
            )

else:
    st.info("No supplier relationships identified yet.")

# -----------------------------
# RISK ANALYSIS
# -----------------------------

st.divider()
st.header("4. Supply Chain Risk Assessment")

verified_relationships = [
    r for r in relationships
    if r.get("status", "").lower() == "verified"
]

total_relationships = len(relationships)
total_verified = len(verified_relationships)

col1, col2, col3 = st.columns(3)

col1.metric("Companies Identified", len(companies))
col2.metric("Mapped Relationships", total_relationships)
col3.metric("Verified Relationships", total_verified)

if total_relationships == 0:
    st.warning("No supplier relationships mapped. Supply chain visibility is low.")

elif total_verified < total_relationships:
    st.warning("Some supplier relationships still need verification.")

if total_relationships == 1:
    st.warning(
        "Single mapped supplier relationship. "
        "Alternative sourcing has not yet been established."
    )

if total_verified == total_relationships and total_relationships > 0:
    st.success("All currently mapped relationships have supporting verification status.")

st.info(
    "Risk assessment is currently based on relationship coverage. "
    "Supplier concentration, geographic exposure and alternative sourcing "
    "require additional verified supplier data."
)

# -----------------------------
# DATA COVERAGE
# -----------------------------

st.divider()
st.header("5. Data Coverage")

col1, col2, col3 = st.columns(3)

col1.metric("Companies Identified", len(companies))
col2.metric("Relationships Mapped", len(relationships))
col3.metric("Verified Relationships", len(verified_relationships))

unverified = len(relationships) - len(verified_relationships)

st.write("### Relationship Verification")

st.progress(
    total_verified / total_relationships if total_relationships else 0
)

st.write(f"Verified: {total_verified}")
st.write(f"Unverified: {unverified}")

st.caption(
    "Company profiles are enriched using Crustdata. "
    "Relationship verification is based on supporting external evidence."
)

st.success("Supply chain analysis loaded successfully.")

st.divider()
st.header("Automated Company Discovery")

domain = st.text_input(
    "Enter company domain",
    placeholder="e.g. albemarle.com"
)

if st.button("Discover Company"):

    if not domain.strip():
        st.warning("Please enter a domain.")

    else:
        with st.spinner("Searching and enriching company..."):

            try:
                results = discover_and_enrich(domain.strip())

                if results:

                    st.success("Company successfully discovered!")

                    for company in results:

                        st.subheader(company["name"])

                        col1, col2, col3 = st.columns(3)

                        col1.metric(
                            "Headcount",
                            company["headcount"] or "Not available"
                        )

                        col2.write("**Domain**")
                        col2.write(company["domain"])

                        col3.write("**Company**")
                        col3.write(company["name"])

                        st.write(
                            company["company_data"]
                            .get("basic_info", {})
                            .get("description", "No description available.")
                        )

                else:
                    st.warning("No matching company found.")

            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {e}")
