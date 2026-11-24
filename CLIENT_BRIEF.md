# Client Brief — HDB Resale Price Intelligence

> **Disclosure: this is a simulated freelance engagement.** The client, brief
> and commercial framing in this document were created for portfolio purposes
> to demonstrate how a real engagement of this kind would be scoped and
> delivered. There is no actual client. The data, methods and results in this
> project are entirely real.

## Client context (simulated)

A Singapore-based proptech startup is building a home-valuation tool for HDB
resale buyers and sellers. Before committing engineering time to a production
valuation engine, the product team wants an independent data analyst to
establish, from official transaction records:

- what the market actually looks like,
- which flat attributes move prices and by how much,
- how accurate an automated valuation can realistically be, and
- where the model systematically disagrees with the market.

## Business questions

1. **Price drivers.** Which factors drive HDB resale prices most strongly:
   town, flat type, floor area, storey, flat model, or remaining lease?
2. **Valuation prototype.** How accurate is a price-prediction model trained
   on historical transactions when it is asked to price future transactions
   it has never seen? What error should the product promise users, overall
   and per flat type?
3. **Market movement.** Which towns and segments appreciated fastest between
   2017 and 2026, and how large has the "million-dollar flat" phenomenon
   become?
4. **Lease decay and value segments.** How does price respond as the
   remaining lease on a 99-year HDB lease shrinks, and which town × flat-type
   segments transacted below (or above) what the model predicts in 2026?

## Scope

- Single data source: data.gov.sg, "Resale flat prices based on registration
  date from Jan-2017 onwards" (dataset `d_8b84c4ee58e3cfc0ece0d773c8ca6abc`),
  all transactions registered January 2017 – November 2026.
- Analysis, modelling and visual deliverables as listed below.
- Out of scope: private condominium / landed property, rental market, BTO
  (new flat) pricing, geospatial enrichment (MRT distance, schools), and any
  production deployment of the model.

## Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | This brief and engagement framing | `CLIENT_BRIEF.md` |
| 2 | Executive summary with product recommendations | `README.md` |
| 3 | Reproducible analysis pipeline (download → clean → analyse → model → charts → dashboard) | `scripts/01–07` |
| 4 | Cleaned transaction dataset | `data/processed/` |
| 5 | Result tables (town league table, monthly series, million-dollar tables, lease decay, model metrics, value segments) | `data/results/` |
| 6 | Charts for stakeholder use | `charts/` |
| 7 | Static client dashboard | `dashboard/index.html` |
| 8 | Automated consistency tests | `tests/test_project.py` |

## Acceptance criteria used for this delivery

- Every headline number in the README can be recomputed from the delivered
  result tables and is cross-checked by the automated tests.
- The model is evaluated on a time-based holdout (train ≤ Dec 2024, test
  ≥ Jan 2025), not a random split, so reported accuracy reflects pricing
  future transactions.
- Limitations and data caveats are stated in the deliverables themselves,
  not left in a separate appendix nobody reads.
