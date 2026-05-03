"""
Generate the sample evaluation PDF: ClimateCore Platform Technical Overview.

The document has 5 pages with distinct, fact-dense content so that each of the
5 valid test queries has a clear, grounded answer and the 3 invalid queries are
provably absent.

Usage (standalone):
    python tests/generate_pdf.py
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF — already in requirements.txt


# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------

PAGES: list[dict] = [
    {
        "title": "ClimateCore Platform — Introduction",
        "lines": [
            "ClimateCore is a cloud-based climate analytics platform designed",
            "for research institutions and environmental agencies worldwide.",
            "",
            "Key Facts:",
            "  • Founded in 2019 by Dr. Elena Marchetti",
            "  • Headquarters: Geneva, Switzerland",
            "  • Processes 2 terabytes of satellite data daily",
            "  • Serves over 3,400 organisations across 89 countries",
            "",
            "Mission: To make high-resolution climate data accessible and",
            "actionable for scientists, governments, and NGOs at every scale.",
        ],
    },
    {
        "title": "Core Modules",
        "lines": [
            "ClimateCore is organised into three primary modules:",
            "",
            "1. DataVault",
            "   Integrates data from 47 climate monitoring sources worldwide,",
            "   including satellite feeds, ocean buoys, and ground stations.",
            "   Updated in real time with a 15-minute ingestion lag.",
            "",
            "2. ModelEngine",
            "   Runs 12 distinct climate prediction models in parallel, with",
            "   forecast horizons ranging from 7 days to 50 years.",
            "   All models are ensemble-averaged before delivery.",
            "",
            "3. ReportBuilder",
            "   Generates automated reports in 8 supported languages with",
            "   customisable templates for policy and scientific audiences.",
        ],
    },
    {
        "title": "Technical Architecture",
        "lines": [
            "Technology Stack:",
            "  • Backend services: Python 3.11 and Go 1.21",
            "  • Cloud provider: AWS with multi-region redundancy across",
            "    5 availability zones (us-east-1, eu-west-1, ap-southeast-1,",
            "    ap-northeast-1, sa-east-1)",
            "  • Primary database: PostgreSQL 15 for structured data",
            "  • Cache layer: Redis 7.2 with a 99.97 % hit ratio",
            "",
            "Performance Metrics (trailing 12 months):",
            "  • Median API response time: 127 milliseconds",
            "  • P99 API response time: 412 milliseconds",
            "  • System uptime: 99.95 %",
            "  • Maximum concurrent users tested: 25,000",
        ],
    },
    {
        "title": "Pricing and Subscription Plans",
        "lines": [
            "ClimateCore offers three subscription tiers:",
            "",
            "Starter Plan — $49 per month",
            "  • Up to 10 users",
            "  • 100 GB data storage",
            "  • Access to DataVault and ReportBuilder",
            "  • Email support only",
            "",
            "Professional Plan — $249 per month",
            "  • Up to 50 users",
            "  • 1 TB data storage",
            "  • Full access to all three modules",
            "  • Priority email and live-chat support",
            "",
            "Enterprise Plan — Custom pricing",
            "  • Unlimited users and dedicated infrastructure",
            "  • Custom SLAs negotiated directly with the account team",
            "  • 24/7 dedicated support engineer",
        ],
    },
    {
        "title": "Security and Compliance",
        "lines": [
            "ClimateCore maintains the following certifications:",
            "",
            "  • SOC 2 Type II — audited annually by Deloitte",
            "  • GDPR compliant for all EU data subjects",
            "  • ISO 27001 certified since March 2021",
            "",
            "Encryption standards:",
            "  • Data at rest: AES-256",
            "  • Data in transit: TLS 1.3",
            "",
            "Additional controls:",
            "  • Penetration testing every 6 months by NCC Group",
            "  • Bug bounty programme managed via HackerOne",
            "  • Data residency options: EU, US, and APAC regions",
        ],
    },
]

# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

FONT = "helv"
MARGIN_X = 72
MARGIN_Y_TOP = 72
LINE_HEIGHT = 18
TITLE_SIZE = 15
BODY_SIZE = 11


def create_sample_pdf(output_path: str | Path = "tests/fixtures/climatecore_overview.pdf") -> Path:
    """Write the sample PDF to *output_path* and return the resolved Path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()

    for page_data in PAGES:
        page: fitz.Page = doc.new_page(width=595, height=842)  # A4
        y = MARGIN_Y_TOP

        # Title
        page.insert_text(
            (MARGIN_X, y),
            page_data["title"],
            fontname=FONT,
            fontsize=TITLE_SIZE,
            color=(0.1, 0.1, 0.5),
        )
        y += LINE_HEIGHT + 6

        # Horizontal rule (thin rectangle)
        page.draw_line((MARGIN_X, y), (595 - MARGIN_X, y), color=(0.6, 0.6, 0.6), width=0.5)
        y += 12

        # Body lines
        for line in page_data["lines"]:
            page.insert_text(
                (MARGIN_X, y),
                line,
                fontname=FONT,
                fontsize=BODY_SIZE,
                color=(0.05, 0.05, 0.05),
            )
            y += LINE_HEIGHT

    doc.save(str(output_path))
    doc.close()

    print(f"Sample PDF written to: {output_path.resolve()}")
    return output_path.resolve()


if __name__ == "__main__":
    create_sample_pdf()
