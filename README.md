# SupplyChain Intelligence

**Multi-Tier Supplier Mapping & BOM Risk Agent**

SupplyChain Intelligence is a prototype that turns a product Bill of Materials (BOM) into an exploratory supply-chain view. It combines structured BOM data, company intelligence from Crustdata, and web-based relationship research to help identify relevant companies, inspect potential supplier connections, and highlight areas that may need further investigation.

> **Important:** A company operating in a relevant industry does not automatically mean it supplies a particular customer. The project distinguishes company discovery from relationship evidence. Treat any relationship without a supporting source as unverified, and independently validate source claims before making business decisions.

## Problem

Supply chains can span multiple tiers of component makers, raw-material producers, and original equipment manufacturers. It can be difficult to understand which companies may be relevant to a product's BOM, what public evidence exists for their relationships, and where supplier visibility is incomplete.

## What the project does

Starting with an EV battery pack BOM, the application is designed to:

1. **Explore the BOM** — display product components and the materials associated with them.
2. **Discover relevant companies** — identify companies associated with selected materials or supply-chain roles.
3. **Enrich company profiles** — retrieve available company information through the Crustdata API.
4. **Research relationships** — search for public information about potential supplier-customer relationships.
5. **Visualise the network** — present recorded companies and relationships as a supply-chain network.
6. **Highlight potential risks and gaps** — surface areas such as limited supplier coverage, concentration, and missing relationship evidence.

The application is an exploratory decision-support prototype, not an automated certification of supplier relationships or a substitute for supply-chain due diligence.

## Example use case: EV battery pack

The sample BOM in `data/bom.json` contains:

| Component | Materials |
|---|---|
| Battery Cells | Lithium, Nickel, Cobalt, Graphite |
| Battery Casing | Aluminium, Steel |
| Battery Management System | Semiconductors, PCBs |
| Cooling System | Copper, Aluminium |

The sample company and relationship records are stored in `data/supply_chain.json`. They are intended to demonstrate how company profiles and relationship evidence can be brought together in one view.

## Technology

- **Python** — application logic and API integration
- **Streamlit** — interactive web application
- **Crustdata API** — company search, company enrichment, and live web search
- **JSON** — sample BOM and supply-chain data
- **Requests** — HTTP requests to the API

## Project structure

```text
SupplyChain_Intelligence/
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
└── data/
    ├── bom.json
    └── supply_chain.json
```

## Setup and run locally

### 1. Clone the repository

```bash
git clone https://github.com/kartikguptag21/SupplyChain_Intelligence.git
cd SupplyChain_Intelligence
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Crustdata API key

Create a file named `.env` in the project root:

```text
CRUSTDATA_API_KEY=your_crustdata_api_key
```

Replace the placeholder with your own API key. Do not commit or share the `.env` file.

### 5. Start the application

```bash
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) that you can open in your browser.

## API integration

The application uses Crustdata for company intelligence and live web research. API access requires a valid API key stored locally in `.env`.

The project uses API results to support company discovery and profile enrichment. Public web-search results can help locate evidence about relationships, but search-result snippets or a company's industry description alone are not proof of a direct supplier-customer relationship.

API availability, response fields, usage limits, and credit consumption are governed by Crustdata and may change. Refer to the [Crustdata documentation](https://docs.crustdata.com/) for current details.

## Data and verification approach

- The sample BOM and company records are stored as JSON so they can be inspected and modified.
- Company identity and company-to-company relationships are treated as separate pieces of information.
- Relationship claims should be linked to a specific source that supports the stated parties, product/material, and status.
- Agreement status and dates should be checked against the cited source and its publication date.
- If the evidence is incomplete, outdated, or ambiguous, mark the relationship as **unverified** rather than assuming it is active.
- Risk indicators are intended to guide further investigation; they are not formal supplier-risk ratings.

## Limitations and future scope

This is a hackathon prototype using a sample EV battery pack BOM and a limited set of company records. Its results depend on the completeness and freshness of available API data and public sources.

Possible next steps include:
- expanding the BOM and material taxonomy;
- adding more supplier tiers and geographic dependencies;
- storing source-level evidence and verification status for every relationship;
- adding confidence and freshness indicators;
- incorporating disruption, geopolitical, logistics, and commodity-risk data;
- supporting additional products and configurable risk frameworks.

## Security

- Keep API keys in `.env` or another secure secrets manager.
- Never upload `.env`, API keys, access tokens, or private credentials to GitHub.
- The repository's `.gitignore` should exclude `.env`, virtual environments, and Python cache files.

## Repository

[GitHub: SupplyChain Intelligence](https://github.com/kartikguptag21/SupplyChain_Intelligence)

---

Built for **ContextCon — IIT Bombay Agentic Services Hackathon 2026**.
