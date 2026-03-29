<div align="center">

<img src="https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Powered by Google Gemini"/>
<img src="https://img.shields.io/badge/Google%20ADK-Multi--Agent-34A853?style=for-the-badge&logo=google&logoColor=white" alt="Google ADK"/>
<img src="https://img.shields.io/badge/Cloud%20Run-Serverless-F57C00?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Cloud Run"/>
<img src="https://img.shields.io/badge/YOLOv8-Computer%20Vision-FF6F00?style=for-the-badge&logo=opencv&logoColor=white" alt="YOLOv8"/>
<img src="https://img.shields.io/badge/Precision-99.9%25-1A4D2E?style=for-the-badge" alt="99.9% Precision"/>
<img src="https://img.shields.io/badge/License-Proprietary-555555?style=for-the-badge" alt="Proprietary"/>

<br/><br/>

# 🌾 AgriBusiness OS AI

### *The Multilingual Agentic Ecosystem for Precision Agribusiness*

**Transforming raw farm data into high-yield commercial roadmaps — in Malayalam, Hindi, and English.**

<br/>

---

</div>

## 📌 Overview

**AgriBusiness OS AI** is a proprietary, end-to-end intelligence platform that answers the three critical questions every farmer faces:

<div align="center">

| 🌱 **What** to grow | 📅 **When** to sell | 💰 **How** to maximise ROI |
|:---:|:---:|:---:|
| Soil & climate-matched crop selection | Weather-correlated market timing | Resource optimisation & scheme access |

</div>

<br/>

Built on **Google Gemini** and the **Google Agent Development Kit (ADK)**, the system orchestrates a network of specialised AI agents that reason in parallel — combining real-time web grounding, geospatial intelligence, and multi-agent synthesis into a single, actionable roadmap.

Designed for **regional inclusivity**, the platform ensures advanced agricultural intelligence is accessible to every stakeholder through seamless support for **Malayalam**, **Hindi**, and **English**.

<br/>

---

## 🚨 The Problem We're Solving

<div align="center">

> **India feeds a billion people. But the farmers who make that possible remain among the poorest.**

</div>

<br/>

India's agricultural sector employs over **40% of the workforce** and is the backbone of the national economy — yet the average Indian farmer lives below the poverty line. The root cause is not a lack of hard work. It is a lack of business intelligence.

**Farming in India is practised as a tradition, not a business.**

Most farmers make decisions based on generational habit — growing the same crops their parents grew, selling at the same local mandis, with no visibility into market prices, government entitlements, or optimal timing. The result is a systemic value trap:

<div align="center">

| The Gap | The Consequence |
|:---|:---|
| No data on what crop earns the most for their soil | Low-yield or low-value harvests |
| No knowledge of when and where to sell | Forced distress sales at harvest time |
| No access to government subsidies & insurance | Avoidable losses from weather and disease |
| No connection to buyers, integrators, or cold storage | Middlemen capture most of the margin |
| No crop health monitoring | Disease goes undetected until significant losses occur |

</div>

<br/>

### 💡 Our Answer: Farm Like a Business

**AgriBusiness OS AI** — built by the **HNT AI** team — gives every farmer access to the same decision-making tools available to large agribusinesses, delivered in their native language, at the moment they need it.

We don't just provide information. We provide a **complete operating system for the farm as a business** — from seed selection to final sale.

<div align="center">

| Farmer Question | AgriBusiness OS Answer |
|:---|:---|
| *"What should I grow this season?"* | Best-fit crop for your soil, location & current market demand |
| *"How do I cultivate it correctly?"* | Step-by-step agronomic guidance with local context |
| *"Is my crop healthy?"* | YOLOv8 computer vision scan — disease detected in seconds |
| *"When is the best time to sell?"* | Weather + market timing analysis with price trend signals |
| *"Who should I sell to?"* | Direct connections to integrators, mandis & cold storage |
| *"What government support can I access?"* | Real-time scheme discovery with application steps |

</div>

<br/>

---

## 🤖 Agentic Pipeline

The platform runs a sequential + parallel multi-agent pipeline under the hood. Each agent is a specialist; the **Final Consolidator** fuses their outputs into one cited, production-ready report.

```
Field Image (optional)           Farm Data (location, soil, capital)
        │                                      │
        ▼                                      │
┌─────────────────────┐                        │
│  YOLOv8 CV Module   │  → Crop health signals │
│  99.9% precision    │    injected as          │
│  77% mAP            │    structured inputs ───┤
└─────────────────────┘                        │
                                               ▼
                              User Input (enriched farm profile)
                                               │
                                               ▼
                              ┌─────────────────────┐
                              │    Cultivator        │  → Builds detailed farmer profile
                              └──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Location Check     │  → Validates soil & regional context   [🔍 Web-grounded]
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Crop for Soil      │  → Recommends best-fit crops
└──────────┬──────────┘
           ▼
    ┌──────┴──────────────────────────────────────┐
    │              Parallel Agents                 │
    │  ┌──────────────┐  ┌──────────────────────┐ │
    │  │ Weather       │  │  Market Timing        │ │  [🔍 Web-grounded]
    │  │ Analysis      │  │                      │ │
    │  └──────────────┘  └──────────────────────┘ │
    │  ┌──────────────┐  ┌──────────────────────┐ │
    │  │ Sales         │  │  Storage Proximity   │ │  [🔍 Web-grounded]
    │  │ Channels      │  │                      │ │
    │  └──────────────┘  └──────────────────────┘ │
    └──────┬──────────────────────────────────────┘
           ▼
┌─────────────────────┐
│  Perishability Risk  │  → Risk synthesis across all reports
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Final Consolidator  │  → Cited, multilingual agribusiness roadmap
└─────────────────────┘
```

<br/>

---

## 🧩 Core Modules

### 1. 🗺️ Roadmap Engine — Agentic AI

A sophisticated interface where farmers input land metrics, soil profiles, available tools, capital constraints, and geo-location. The engine reasons across the full agent network to produce a comprehensive, prioritised action plan.

**Outputs include:**
- ✅ Crop selection tailored to soil type, region, and real-time climate data
- ✅ Optimal planting and harvest windows with weather-correlated timing
- ✅ Resource optimisation strategies calibrated to available capital
- ✅ Step-by-step agribusiness roadmap with actionable milestones and inline citations

<br/>

### 2. 🏛️ Government Scheme Discovery

A dedicated search agent that scans central and state databases in real time to surface schemes directly relevant to each farmer's profile — with eligibility checks, application steps, and official source links.

| Category | Coverage |
|---|---|
| **Subsidies & Grants** | Land-size and crop-specific eligibility |
| **Loans & Credit** | NABARD, Kisan Credit Card, state-level schemes |
| **Insurance & Risk Cover** | PMFBY and allied crop-protection programmes |
| **Real-time Discovery** | Schemes farmers can access and apply for immediately |

<br/>

### 3. 🎬 Integrated Video Ecosystem

A curated content library bridging the gap between agricultural knowledge creators and field operations.

- 📹 Expert educational content on sustainable farming practices and tool usage
- 🌐 Curated channels from agronomists, extension officers, and successful farmers
- 🤝 Community knowledge network linking influencers with on-the-ground operators

<br/>

### 4. 👁️ Computer Vision — Real-Time Crop Health Detection

A dedicated computer vision module powered by a custom-trained **YOLOv8** model that processes uploaded field images to extract real-time crop health signals — before the agribusiness pipeline executes.

<div align="center">

| Metric | Result |
|:---:|:---:|
| **Precision** | 🟢 ~99.9% |
| **mAP (mean Average Precision)** | 🟡 ~77% |
| **Detection Mode** | Real-time, field conditions |

</div>

**How it works:**
- 📸 Farmers upload field images directly through the platform
- 🔬 The YOLOv8 model — trained on annotated grapevine datasets with preprocessing and augmentation — detects diseases including **scab**, **rust**, and **leaf defects** with high precision across varying field conditions
- 🔁 Visual detections are converted into structured inputs and **injected directly into the agribusiness pipeline**, where agents dynamically adjust yield forecasts, risk assessments, and market strategies
- 🎯 This tight coupling between real-world crop conditions and agentic reasoning enables more accurate predictions, reduced crop losses, and optimised farm profitability

```
Field Image Upload
        │
        ▼
 YOLOv8 Detection Model
 (trained on grapevine datasets)
        │
        ├─→ Disease detected: Scab / Rust / Leaf defects
        ├─→ Severity score
        └─→ Structured health signal
                │
                ▼
      Agribusiness Pipeline
      (agents adjust yield, risk & market strategies)
```

<br/>

---

## ⚙️ Technical Architecture

| Layer | Technology |
|---|---|
| **Orchestration** | Google Agent Development Kit (ADK) — multi-agent reasoning & coordination |
| **Intelligence** | Google Gemini — multimodal, multilingual LLM with web-search grounding |
| **Computer Vision** | YOLOv8 — custom-trained crop disease detection (99.9% precision, 77% mAP) |
| **Hosting** | Google Cloud Run — serverless, auto-scaling, cloud-native |
| **Backend** | Python · Flask REST API · SSE streaming · SQLAlchemy |
| **Languages** | Malayalam · Hindi · English *(extensible)* |
| **Roadmap** | Native mobile application — iOS & Android *(in development)* |

<br/>

### API Surface

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/plan` | Submit farm data → spawns background agent job |
| `GET` | `/api/plan/<id>/stream` | SSE stream for real-time agent progress |
| `POST` | `/api/followup` | Ask follow-up questions against a completed report |
| `GET` | `/api/trace/<id>` | Inspect per-step agent trace & timing metrics |
| `GET/POST` | `/policies` | Government scheme discovery form |
| `GET` | `/health` | Health check |

<br/>

---

## 🌐 Multilingual Support

All agent outputs, reports, and follow-up responses are delivered in the user's chosen language.

```python
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
}
```

Language selection is applied uniformly across every agent in the pipeline — from the initial cultivator profile through to the final consolidated roadmap.

<br/>

---

## 👥 Team

| Name | Role | Focus |
|---|---|---|
| **Chandrachood** | Product Manager / Developer | Platform architecture, product vision & full-stack development |
| **Pritpal S Arora** | Strategy & Operations | Go-to-market strategy, partnerships & operational scaling |
| **Nithya Kannan** | Product Design | UX research, interface design & accessibility |
| **Lekha** | Lead Data Scientist / Developer | AI pipeline engineering, model tuning & data architecture |

<br/>

---

## 📄 Licensing

**Proprietary — All Rights Reserved**

This software is the exclusive intellectual property of **Chandrachood** and the **AgriBusiness OS AI Team**. Unauthorized distribution, modification, or reverse engineering of the agentic roadmap logic, multilingual prompt structures, or any component of this platform is strictly prohibited without prior written consent.

<br/>

---

<div align="center">

*Built for the future of sustainable, data-driven farming.*

**🌾 AgriBusiness OS AI**

</div>
