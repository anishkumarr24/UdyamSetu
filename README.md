# UdyamSetu (NSFDC Loan Portal)

**Problem Statement ID:** SIH26092 (MoSJE)
**Category:** Software
**Domain:** Financial Inclusion & Governance

UdyamSetu is a next-generation platform designed to bridge the gap between marginalized communities (SC, ST, OBC, Safai Karamcharis) and institutional credit (NSFDC schemes). This repository contains the complete hackathon prototype demonstrating rule-based scheme matching, intelligent EMI projections with moratorium calculations, and an automated geospatial routing engine that redirects citizens away from High-NPA bank branches.

## 🚀 The Tech Stack

- **Backend Framework:** FastAPI (Python 3.11)
- **Database Layer:** PostgreSQL 15 + PostGIS with SQLAlchemy & GeoAlchemy2
- **Frontend Framework:** React (Vite), Tailwind CSS (v4)
- **Maps & Routing:** React-Leaflet
- **Data Visualization:** Recharts
- **Document Export:** jsPDF
- **Orchestration:** Docker & Docker Compose

## ⚡ Quick Start

Boot up the entire stack using Docker. The backend database is volume-mounted so any simulated data or NPA state changes will persist across restarts.

```bash
docker-compose up -d --build
```

- **Frontend Application:** [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 📋 Demo Walkthrough for Evaluators

This prototype features an end-to-end "Citizen-to-Bank" application loop. Follow these steps to evaluate the core innovations:

### 1. The Citizen Onboarding & AI Abstraction
1. Navigate to the **Apply Now** wizard (`http://localhost:5173/apply`).
2. **Citizen Profile:** Enter demographic and business profile details (Age, Category, Income, Domain).
3. **Gap Analysis:** Observe the final "Readiness Score" which assesses documentation completeness and flags missing dependencies (e.g., missing Udyam Registration).

### 2. The Moratorium Visualizer
1. Once matched to a scheme (e.g., NSFDC Micro Finance), proceed to the **Citizen Dashboard** (`http://localhost:5173/`).
2. Adjust the **Moratorium Period** slider on the left.
3. Notice how the Recharts Stacked Bar Chart recalculates and visually shifts the "Interest-Only" repayment blocks vs standard EMI blocks, giving the citizen immediate clarity on their repayment schedule.

### 3. The Bank Officer Admin Portal & NPA Routing Loop
1. Click **Sign In / Register** in the bottom sidebar, choose **Sign up**, and select the **Bank Admin (Officer)** role (or sign in if an account was already created).
2. Navigate to the **Admin Portal** from the sidebar (`http://localhost:5173/admin/bank`).
3. Look at the **Fund Utilization / NPA Simulator** panel.
4. **The Bypass Demo:** Drag the NPA slider for a specific bank branch (e.g., "Srei Infrastructure Finance" or "Bangiya Gramin Vikash Bank") past the **8.0% threshold**.
5. A critical red alert will appear: *"Geospatial router will now bypass this branch for new citizens."*
6. **Verify the Loop:** Go back to your Citizen Dashboard tab and refresh. The map on the right will now exclude that branch from its 100km radius search, effectively halting new loan routing to underperforming branches.

### 4. Multilingual Support & Dossier Export
1. Use the **Language Toggle** at the bottom of the sidebar to switch the core UI between English and Hindi, demonstrating the accessibility layer.
2. Click **Download Bank-Ready Dossier** on the Dashboard to generate a neat, structured PDF summary that the citizen can physically carry to their routed bank branch.

---
*Built with ❤️ for the Smart India Hackathon.*
