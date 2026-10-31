
# SupplyChain Intelligence

### Multi-Tier Supplier Mapping & BOM Risk Analysis

SupplyChain Intelligence is a supply-chain research and analysis dashboard designed to help users understand the supplier ecosystem behind manufactured products.

It combines Bill of Materials (BOM) mapping, company discovery, company enrichment and evidence-based supplier relationship mapping.

## Problem

Modern products depend on complex, multi-tier supply chains. Identifying suppliers, understanding business relationships and assessing potential supply-chain dependencies can be difficult when information is scattered across multiple sources.

## Solution

SupplyChain Intelligence helps users:

- Explore the Bill of Materials of a product.
- Research suppliers and companies using live web search.
- Discover and enrich company profiles using Crustdata.
- Map supplier-customer relationships.
- View supporting evidence for identified relationships.
- Assess relationship coverage and potential supply-chain visibility gaps.

## Current Demonstration

The current demonstration uses an EV Battery Pack as its sample product.

It includes:
- Battery cells
- Battery casing
- Battery Management System
- Cooling system

A verified example relationship is Albemarle Corporation supplying battery-grade lithium hydroxide to Ford Motor Company, supported by Albemarle's official announcement.

The dashboard distinguishes company discovery from verified supplier relationships. Company profiles alone do not establish a supplier-customer relationship.

## Technology Stack

- Python
- Streamlit
- Crustdata API
- NetworkX
- Graphviz
- Pandas
- Requests
- Python-dotenv

## Architecture

1. User enters a product or research query.
2. BOM information provides the product's component and material structure.
3. Crustdata APIs support company discovery and enrichment.
4. Live web research retrieves relevant public information.
5. Supplier relationships are mapped using supporting evidence.
6. Streamlit presents company profiles, relationship graphs and risk indicators.

## Setup and Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd supplyChain_Contextcon
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
CRUSTDATA_API_KEY=your_api_key_here
```

Run the application:

```bash
streamlit run app.py
```

## Future Scope

- Automated extraction and verification of supplier relationships.
- Multi-tier supplier dependency mapping.
- Geographic risk and supplier concentration analysis.
- Alternative supplier identification.
- Automated risk alerts and continuous supply-chain monitoring.
- Support for multiple products and industries.

## Data and Verification

Company information is retrieved through Crustdata. Public web sources provide supporting evidence for supplier relationships.

The current implementation includes a curated, evidence-backed relationship example. Risk indicators are preliminary and depend on the coverage and quality of available data.

## Team

Add your team name and member details here.
