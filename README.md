<div align="center">

# Candis — Candidate Discovery Ranker

**A CPU-only, rule-based candidate ranking engine for the [Redrob India Runs Data & AI Challenge](https://redrob.io)**

[![Python 3.x](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](#prerequisites)
[![CPU Only](https://img.shields.io/badge/Compute-CPU%20Only-green)](#design-philosophy)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#license)

*Ranks 100,000+ candidates for a Senior AI Engineer role in under 5 minutes — no GPU, no API calls, no network access.*

</div>

---

## Table of Contents

- [Overview](#overview)
- [Design Philosophy](#design-philosophy)
- [Architecture](#architecture)
- [Scoring Pipeline](#scoring-pipeline)
- [Module Breakdown](#module-breakdown)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Output Format](#output-format)
- [Safeguards & Anti-Gaming](#safeguards--anti-gaming)
- [Tech Stack](#tech-stack)

---

## Overview

**Candis** is a deterministic, rule-based candidate ranking system built for the Redrob hackathon. Given a JSONL file of 100K+ candidate profiles, it identifies and ranks the top 100 candidates best suited for a **Senior AI Engineer** role specializing in *embeddings, vector search, ranking/IR, and production ML*.

The ranker combines four key dimensions into a single score:

| Dimension | What It Measures |
|:--|:--|
| **Skill Fit** | Trust-weighted match against 7 JD-aligned skill groups |
| **Career Trajectory** | AI/ML role depth, production experience, consulting vs. product tenure |
| **Honeypot Detection** | Flags fraudulent profiles with impossible timelines or inflated skills |
| **Platform Availability** | Redrob behavioral signals — activity recency, response rate, notice period |

---

## Design Philosophy

```
Deterministic   — Same input always produces the same ranking
Fast            — Streams JSONL line-by-line; 100K candidates < 5 min on CPU
Anti-Gaming     — Multi-layered honeypot detection penalizes keyword stuffers
Zero Dependencies — No GPU, no network, no external APIs during ranking
```

---

## Architecture

### System Overview

```mermaid
graph TB
    subgraph Input
        A["candidates.jsonl<br/><i>100K+ profiles</i>"]
    end

    subgraph "Streaming Pipeline"
        B["Loader<br/><code>loader.py</code>"]
        C["Feature Extractor<br/><code>feature_extractor.py</code>"]
        D["Honeypot Detector<br/><code>honeypot_detector.py</code>"]
        E["Scorer<br/><code>scorer.py</code>"]
    end

    subgraph "Post-Processing"
        F["Sort by Raw Score"]
        G["Top-K Selection"]
        H["Strictly Decreasing<br/>Score Enforcement"]
        I["Reasoning Generation"]
    end

    subgraph Output
        J["submission.csv<br/><i>Top 100 ranked candidates</i>"]
    end

    A --> B
    B -->|"Stream one<br/>candidate"| C
    C -->|"Feature<br/>vector"| D
    D -->|"Honeypot<br/>flag"| E
    E -->|"Scored<br/>candidate"| F
    F --> G
    G --> H
    H --> I
    I --> J

    style A fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style J fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style B fill:#3182ce,stroke:#2b6cb0,color:#fff
    style C fill:#3182ce,stroke:#2b6cb0,color:#fff
    style D fill:#e53e3e,stroke:#c53030,color:#fff
    style E fill:#38a169,stroke:#2f855a,color:#fff
    style F fill:#805ad5,stroke:#6b46c1,color:#fff
    style G fill:#805ad5,stroke:#6b46c1,color:#fff
    style H fill:#805ad5,stroke:#6b46c1,color:#fff
    style I fill:#805ad5,stroke:#6b46c1,color:#fff
```

### Module Interaction

```mermaid
graph LR
    subgraph "Data Layer"
        SA["skill_aliases.json"]
    end

    subgraph "Core Modules"
        SM["skill_matcher.py"]
        FE["feature_extractor.py"]
        HD["honeypot_detector.py"]
        SC["scorer.py"]
    end

    subgraph "I/O Modules"
        LD["loader.py"]
        OW["output_writer.py"]
    end

    subgraph "Orchestrator"
        RK["rank.py"]
    end

    SA --> SM
    SM --> FE
    FE --> RK
    HD --> RK
    SC --> RK
    LD --> RK
    OW -.->|"available<br/>utility"| RK

    style SA fill:#ecc94b,stroke:#d69e2e,color:#1a202c
    style SM fill:#4299e1,stroke:#3182ce,color:#fff
    style FE fill:#4299e1,stroke:#3182ce,color:#fff
    style HD fill:#fc8181,stroke:#e53e3e,color:#1a202c
    style SC fill:#68d391,stroke:#38a169,color:#1a202c
    style LD fill:#b794f4,stroke:#805ad5,color:#1a202c
    style OW fill:#b794f4,stroke:#805ad5,color:#1a202c
    style RK fill:#f6ad55,stroke:#dd6b20,color:#1a202c
```

---

## Scoring Pipeline

### How a Candidate Gets Scored

```mermaid
flowchart TD
    A["Raw Candidate JSON"] --> B["Extract Skills"]
    A --> C["Analyze Career"]
    A --> D["Score Education"]
    A --> E["Platform Signals"]
    A --> F["Honeypot Check"]

    B --> B1["Trust-Weighted<br/>Skill Groups"]
    B1 --> G["Skill Score<br/><i>Weighted sum of 7 groups</i>"]
    G --> G1["+ Must-Have Bonus"]

    C --> C1["AI/ML months, production<br/>experience, consulting ratio"]
    C1 --> H["Career Multiplier<br/><i>0.10 — 1.20</i>"]

    D --> D1["Tier + field + degree"]
    D1 --> I["Edu Score"]

    E --> E1["Recency, response rate<br/>GitHub, notice period"]
    E1 --> J["Availability Multiplier<br/><i>0.30 — 1.10</i>"]

    F --> F1{"Is Honeypot?"}
    F1 -->|"Yes"| K["× 0.04 penalty"]
    F1 -->|"No"| L["No penalty"]

    G1 --> M["Base Score"]
    I --> M
    M --> N["Final = Base × Career × Availability"]
    H --> N
    J --> N
    K --> N
    L --> N
    N --> O["Clamp to 0.0 — 1.0"]

    style A fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style F1 fill:#e53e3e,stroke:#c53030,color:#fff
    style K fill:#e53e3e,stroke:#c53030,color:#fff
    style N fill:#38a169,stroke:#2f855a,color:#fff
    style O fill:#38a169,stroke:#2f855a,color:#fff
```

### Skill Group Weights

The ranker evaluates candidates against **7 JD-aligned skill groups**, each with a configurable weight:

```mermaid
%%{init: {'theme': 'dark'}}%%
pie title Skill Group Weight Distribution
    "Embeddings" : 1.00
    "Vector DB" : 0.95
    "Ranking / IR" : 0.95
    "Python (strong)" : 0.85
    "NLP / IR" : 0.80
    "Production ML" : 0.80
    "LLM Fine-tuning" : 0.45
```

Each skill group aggregates dozens of keyword aliases (defined in [`skill_aliases.json`](data/skill_aliases.json)) into a canonical group score, weighted by:

| Factor | How It Works |
|:--|:--|
| **Proficiency** | `beginner=0.25` → `expert=1.0` |
| **Endorsements** | Logarithmic bonus up to 18 endorsements |
| **Duration** | Bonus saturates at 36 months |
| **Trust Discount** | Expert + 0 endorsements + 0 months → capped at `0.18` (anti-stuffing) |

---

## Module Breakdown

### rank.py — Orchestrator

The main entry point. Streams candidates from JSONL, runs them through the scoring pipeline, sorts results, enforces strictly decreasing scores, and writes the final CSV.

### src/loader.py — Data Loader

Memory-efficient streaming reader for `.jsonl` and `.jsonl.gz` files. Uses `ujson` for fast JSON parsing with a `json` stdlib fallback.

### src/skill_matcher.py — Skill Alias Resolution

Loads [`skill_aliases.json`](data/skill_aliases.json) and maps raw skill names and free-text mentions to 7 canonical skill groups via substring matching.

### src/feature_extractor.py — Feature Engineering

The largest module. Extracts and normalizes features across four dimensions:

| Function | Purpose |
|:--|:--|
| `extract_candidate_skill_groups()` | Trust-weighted skill scoring with anti-stuffing |
| `score_career_for_role()` | Career analysis: AI/ML tenure, production depth, consulting ratio |
| `score_education()` | Education tier + field relevance + degree level |
| `score_redrob_signals()` | Platform activity, availability, and engagement metrics |
| `score_experience_fit()` | Sweet-spot scoring for 5–9 years experience |
| `extract_all_features()` | Aggregates all features into a single candidate dict |

### src/honeypot_detector.py — Fraud Detection

Identifies fake/impossible profiles using multiple heuristics:

```mermaid
flowchart LR
    A["Candidate Profile"] --> B{"≥3 expert skills with<br/>0 months & 0 endorsements?"}
    A --> C{"Claims > actual + 4 yrs<br/>experience?"}
    A --> D{"> 12 expert skills?"}
    A --> E{"> 18 months of<br/>overlapping roles?"}

    B -->|"Yes"| F["HONEYPOT"]
    C -->|"Yes"| F
    D -->|"Yes"| G["Flag added"]
    E -->|"Yes"| G
    G -->|"≥ 2 flags"| F

    style F fill:#e53e3e,stroke:#c53030,color:#fff
    style G fill:#ecc94b,stroke:#d69e2e,color:#1a202c
```

### src/scorer.py — Scoring Engine

Combines all features into the final score using a multiplicative model:

```
Final Score = Base Score × Career Multiplier × Availability Multiplier
```

Where **Base Score** includes skill fit, must-have bonuses, experience fit, education, assessments, and certifications.

### src/output_writer.py — CSV Writer

Utility module for writing the ranked output to CSV format.

---

## Project Structure

```
candis/
├── rank.py                      # Main entry point & orchestrator
├── requirements.txt             # Dependencies (ujson only)
├── submission.csv               # Generated output
├── submission_metadata.yaml     # Challenge submission metadata
│
├── src/
│   ├── loader.py                # JSONL streaming reader
│   ├── skill_matcher.py         # Skill alias → canonical group mapping
│   ├── feature_extractor.py     # Feature engineering (skills, career, edu, platform)
│   ├── honeypot_detector.py     # Fraudulent profile detection
│   ├── scorer.py                # Multiplicative scoring engine
│   └── output_writer.py         # CSV output helper
│
├── data/
│   └── skill_aliases.json       # 7 skill groups with 90+ keyword aliases
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** (tested on 3.x)
- No GPU required
- No network access required

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd candis

# Install dependencies
pip install -r requirements.txt
```

> **Note:** The only external dependency is [`ujson`](https://pypi.org/project/ujson/) for faster JSON parsing. The system gracefully falls back to the standard library `json` if `ujson` is unavailable.

### Running the Ranker

```bash
# Generate the ranked submission
python rank.py \
  --candidates "./candidates.jsonl" \
  --out submission.csv
```

### Options

| Flag | Default | Description |
|:--|:--|:--|
| `--candidates` | *(required)* | Path to `candidates.jsonl` or `candidates.jsonl.gz` |
| `--out` | *(required)* | Output CSV path |
| `--top-k` | `100` | Number of top candidates to include |

---

## Output Format

The ranker produces a CSV with the following columns:

| Column | Type | Description |
|:--|:--|:--|
| `candidate_id` | string | Unique candidate identifier (e.g., `CAND_0029367`) |
| `rank` | int | Position in ranking (1 = best) |
| `score` | float | Final score, strictly decreasing, in `[0, 1]` |
| `reasoning` | string | Human-readable explanation of the ranking decision |

**Example output:**

```
candidate_id,rank,score,reasoning
CAND_0029367,1,1.000000,"Senior Data Scientist with 5.7 yrs; Python, vector search, embeddings, NLP/RAG; ~5.6 yrs AI/ML-aligned work. Strong availability and career fit signals for the JD."
CAND_0077337,2,0.999999,"Staff ML Engineer with 7.0 yrs; embeddings, LLM fine-tuning, vector search, production ML; ~7.0 yrs AI/ML-aligned work. Strong availability and career fit signals for the JD."
```

---

## Safeguards & Anti-Gaming

The ranker implements multiple layers of defense against profile manipulation:

```mermaid
flowchart TB
    subgraph "Layer 1 — Skill Trust"
        S1["Expert + 0 endorsements + 0 months<br/>→ trust capped at 0.18"]
        S2["Skills verified against<br/>career description text"]
    end

    subgraph "Layer 2 — Honeypot Detection"
        H1["Timeline impossibilities<br/><i>overlapping roles > 18 mo</i>"]
        H2["Inflated experience<br/><i>claimed vs actual > 4 yr gap</i>"]
        H3["Suspicious skill patterns<br/><i>> 12 expert or ≥ 3 zero-evidence experts</i>"]
    end

    subgraph "Layer 3 — Career Penalties"
        C1["Non-ML titles → hard disqualifier"]
        C2["Consulting-only → 0.55× multiplier"]
        C3["Management-only → fraction penalty"]
    end

    subgraph "Layer 4 — Availability Signals"
        A1["Inactive > 180 days → 0.20 recency"]
        A2["Low response rate → reduced availability"]
        A3["Notice > 90 days → 0.82× modifier"]
    end

    S1 --> SCORE["Final Score"]
    S2 --> SCORE
    H1 --> HP["Honeypot: × 0.04"]
    H2 --> HP
    H3 --> HP
    HP --> SCORE
    C1 --> SCORE
    C2 --> SCORE
    C3 --> SCORE
    A1 --> SCORE
    A2 --> SCORE
    A3 --> SCORE

    style HP fill:#e53e3e,stroke:#c53030,color:#fff
    style SCORE fill:#38a169,stroke:#2f855a,color:#fff
```

---

## Tech Stack

| Component | Technology |
|:--|:--|
| Language | Python 3.x |
| JSON Parsing | `ujson` (with `json` fallback) |
| Compute | CPU-only, single-threaded |
| Dependencies | 1 (`ujson>=5.0.0`) |
| GPU Required | No |
| Network Required | No |
| AI Tools Used | Codex (development assistance only) |

---

<div align="center">

**Built for the Redrob India Runs Data & AI Challenge**

*Team Candis*

</div>
