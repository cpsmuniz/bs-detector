# BS Detector

Legal briefs lie. Not always intentionally — but they do. They cite cases that don't say what they claim. They quote authority with words quietly removed. They state facts that contradict the documents sitting right next to them.

This pipeline is designed to catch these discrepancies. But building it required a deliberate departure from the standard "throw more agents at it" approach.

Here is the story of how this solution evolved, moving from bloated complexity toward deterministic reliability.

---

## The Thought Process & Architecture

When tackling this challenge, the most obvious approach is usually the worst one: passing the entire legal motion to an LLM and asking it to just "find the bad stuff." Or worse, creating 10 different "Agents" that just talk back and forth to each other until they burn through your entire token budget.

I wanted to constrain the LLM. Keep it in a sharp, locked-down box and only use it for tasks that strictly require semantic reasoning.

### Strict Typing at the Boundaries
Before we do anything with the text, we need to guarantee that our data structures are bulletproof. By relying on strict Pydantic models ([`backend/domain/schemas.py`](backend/domain/schemas.py)) and explicit enumerations ([`backend/domain/enums.py`](backend/domain/enums.py)), we protect the pipeline from malformed inputs and ensure that every status (like "EXACT" or "NOT_FOUND") is mathematically defined, not just a random string an LLM decided to emit.

### Taming the Extractors

I started with the extraction. How do we find the citations and quotes in a dense legal motion? If you ask an LLM to do this, it's slow, expensive, and sometimes it just skips over quotes entirely because it gets lazy.

So, I completely bypassed the LLM here. I built a pure, deterministic extractor using Regex ([`backend/domain/extraction.py`](backend/domain/extraction.py)). It instantly scrubs the document for legal citations and direct quotes with perfect accuracy. No tokens spent, no hallucinations.

```text
[ Raw Motion .txt ] 
       │
       ▼
 ┌─────────────┐
 │  EXTRACTOR  │ (Deterministic Regex)
 └─────────────┘
       │
       ├─> Quotes: "The hirer is ordinarily not liable..."
       └─> Citations: Privette v. Superior Court, 5 Cal.4th...
```

### Ground Truth and the "Librarian"

Once we have the citations, we need to know what the law *actually* says. If we rely on the LLM's internal weights to remember case law, we risk it inventing a quote that sounds plausible but is legally wrong.

So I introduced an authority lookup module—basically a librarian ([`backend/infrastructure/source_lookup.py`](backend/infrastructure/source_lookup.py)). When the extractor finds a citation, the librarian looks it up in a designated override file (our mock database for this challenge). If the text isn't there, we don't guess. We simply mark it as "NOT_FOUND" or "DISABLED". This absolute grounding is the first major defense against AI hallucinations.

### Solving the N+1 Problem

Now we had the quotes, the citations, and the actual source texts. It was time to verify them. This is where most AI pipelines hit a wall. 

The typical pattern is to create an agent for every single check. Check Quote 1? *API Call.* Check Quote 2? *API Call.* Check Fact 1 against Witness Statement? *API Call.* If a motion has 50 citations, you just made 50 slow, expensive calls.

I fixed this by implementing batched LLM calls. The Verifier agent ([`backend/application/citation_evaluator.py`](backend/application/citation_evaluator.py)) gathers *all* pending citations and quotes, bundles them with the retrieved authority text, and asks the LLM to grade them all in one single, structured JSON request.

```text
 ┌─────────────┐
 │  VERIFIER   │ (LLM with JSON schema)
 └─────────────┘
       │
       ├─ Phase A: [Batch evaluate Citations + Quotes against Authority]
       │           Returns: { "supports", "does_not_support", "exact"... }
       │
       └─ Phase B: [Batch extract facts & evaluate against Police docs]
                   Returns: { "supported", "contradicted" }
```

This single architectural decision dramatically reduced runtime, increased stability, and kept the code footprint remarkably lean.

**But we aren't just sending raw strings to the LLM either.** I built a structured prompt pipeline to ensure safety and precision:
* **The Contract:** We use a strict YAML contract ([`backend/prompts/contract.yaml`](backend/prompts/contract.yaml)) to force the LLM to return exact, predictable JSON.
* **The Templates:** Prompts are organized into clean Jinja2 templates ([`backend/prompts/citation_evaluator_system.j2`](backend/prompts/citation_evaluator_system.j2)) instead of messy inline strings.
* **The Loader:** A dedicated prompt loader ([`backend/infrastructure/prompt_loader.py`](backend/infrastructure/prompt_loader.py)) safely renders these templates before sending them to the LLM.

And for Phase B (the fact-checking against the police and medical documents)? That's cleanly separated into two distinct steps:
1. **Extracting Claims:** We pull specific, testable facts out of the motion ([`backend/application/claim_extractor.py`](backend/application/claim_extractor.py)).
2. **Cross-Referencing:** We grade those exact facts against the provided physical evidence bundle ([`backend/application/cross_document_assessor.py`](backend/application/cross_document_assessor.py)).

### Who Judges the Judge? 

The prompt asked for a "confidence scoring layer." How do we know if the pipeline is actually confident? Many solutions lazily ask the LLM: *"Rate your confidence from 0 to 1."* This is a trap. An LLM might be 100% confident about a hallucination.

I moved confidence scoring *out* of the AI's hands entirely and into a deterministic rule engine ([`backend/application/report.py`](backend/application/report.py)).

If the librarian couldn't find the source text, the confidence is instantly scored as low (0.2). If the LLM successfully matches quotes exactly, confidence is high. If it detects a contradiction, it's flagged with high confidence because the source text explicitly proves it.

This means our confidence scores are opinionated, mathematically grounded, and entirely transparent.

### Wrapping It Up

With all findings verified and scored, we needed to summarize them for the final user (the judge) without generating a "wall of prose." 

A specialized Memo Writer agent ([`backend/application/memo.py`](backend/application/memo.py)) takes the highest-confidence flags and synthesizes them into a single, punchy paragraph. 
    
Finally, I wrapped everything in the Orchestrator ([`backend/application/runner.py`](backend/application/runner.py)). Instead of a massive, nested try/except nightmare of error handling, the Orchestrator is a simple, elegant loop. It runs the Extractor, then the Librarian, then the Verifier, and finally calls the Assembly. If any step fails, it's caught cleanly.

Rather than running as a messy script, the entire backend is safely exposed as a clean REST API via FastAPI. The routing is minimal and explicit ([`backend/api/app.py`](backend/api/app.py)), served by a single, dead-simple entry point ([`backend/main.py`](backend/main.py)). 

And because looking at raw JSON isn't a great user experience, the findings are beautifully rendered on the frontend explicitly parsing our structured output ([`frontend/src/App.jsx`](frontend/src/App.jsx)).

```text
============= THE FINAL VERIFICATION PIPELINE =============

 1. [ Case Files ]
           │
           ▼
 2. [ Extractor (Regex) ] ───> Finds Citations & Quotes
           │
           ▼
 3. [ Authority Lookup ] ────> Fetches True Legal Text
           │
           ▼
 4. [ Verifier (LLM) ] ──────> Batches checks (Quotes/Citations/Facts)
           │
           ▼
 5. [ Assembler (Rules) ] ───> Applies deterministic confidence scores
           │
           ▼
 6. [ Memo Writer ] ─────────> Drafts the final Judicial Memo
           │
           ▼
    [ JSON Report & UI ]

===========================================================
```

---

## Setup & Execution

### Docker (Easiest & Recommended)

```bash
cp .env.example .env   # add your OpenAI API key
docker compose up --build
```

**API:** `http://localhost:8002`
**UI:** `http://localhost:5175`

*Case docs in `documents/` are automatically mounted. Both services hot-reload — edit files on your host and changes appear automatically.*



## Running evals

From the backend dir with the virtual environment active:

```bash
cd backend
source venv/bin/activate
python -m evals.run_evals
```

Results go to `backend/evals/results/latest.json` unless you set `EVALS_RESULTS_PATH`. Gold expectations live in `backend/evals/fixtures/gold.json` (citation, quote, and cross-doc entries keyed by `reference_id` and `expected_status`). 

The script runs the full pipeline, scores against gold, and writes the results through our custom scoring engine ([`backend/evals/scoring.py`](backend/evals/scoring.py)) and harness ([`backend/evals/run_evals.py`](backend/evals/run_evals.py)):
* **Precision**: Correct flags among what the pipeline predicted.
* **Recall**: Correct flags among what gold expects.
* **Hallucination Rate**: False positives plus extra findings, over total findings.

---
