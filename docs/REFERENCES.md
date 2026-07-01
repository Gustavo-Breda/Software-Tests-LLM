# References

Source citations for the QA Assistant Agent project (see [`../article.pdf`](../article.pdf)).
Status reflects a reference-verification pass on 2026-06-08; upload tracking updated 2026-06-30.

## Uploaded (available in `docs/`)

The following PDFs have been added to `docs/` under their original filenames. Their compressed
content streams cannot be extracted without `pdftotext`/`pdfplumber` — add a note here once
the key excerpts (methodology, metrics) have been read and cross-referenced with PLAN.md §8.

**Silva, L. et al. (2026)** — *Investigating the Use of LLMs in Test Case Generation.*
Journal of Software Engineering Research and Development. UFRJ group (including advisor
Rafael de Mello). File: `Todos e Tema 2- Silva et al., 2026.pdf`

Controlled study: GPT-4o, DeepSeek, Gemini 1.5 Flash × 10 real user stories (Brazilian
judicial system) × zero/one-shot × 3 repetitions = 180 runs, 1,528 test cases. Oracle:
production-validated test cases by experienced testers. Metrics: Precision, Recall, F1
against Travassos et al. (1999) defect taxonomy — Incorrect Fact, Inconsistency, Ambiguity,
Omission; correctness is **all-or-nothing** (one defect = entire case Defective). Results:
72.68% correct; F1 plateau 0.58–0.65 across all models (no statistically significant
difference); one-shot improves precision but hurts recall; omission (FN) is dominant failure.
**Phase 8 comparison baseline:** the bare Agent 1 (zero/one-shot, no RAG, no judge) run
in this project replicates this protocol — target Precision ~0.72, Recall ~0.56, F1 ~0.62.
Replication package: https://github.com/leonardocesarc/testcase

---

**Gheventer, A. et al. (2026)** — *Generative AI Solutions for Software Quality: Assessing
Industrial Readiness.* Software Quality Journal. In Press. UFRJ group. File: `Todos- Gheventer et al., 2026.pdf`

Rapid Multivocal Literature Review (RMLR): 732 publications screened (Scopus + grey
literature); 22 selected (9 scientific + 13 grey); 24 Gen AI solutions identified including
GitHub Copilot, Snyk, Testim, GitLab Duo. Inter-rater: Linear Weighted Cohen's Kappa 0.45–0.70.
Main finding: field is "emerging but immature" — academic prototypes dominate, nearly all lack
industrial validation, formal support, or production-readiness. Three structural barriers:
(1) *Last Mile Problem* (research-to-production gap); (2) *Strategic Adoption Dilemma* (closed
models → vendor lock-in vs. open models → GPU cost; Ollama cited as lower-barrier CPU option);
(3) *Scarcity of Realistic Public Data*. Cite in PLAN.md §3.1 and §8 to justify closed-vs-open
model comparison and Ollama use. Cite in §9 Risks for API version instability finding (silent
updates broke pipelines — Kang et al. 2024). Zenodo: https://zenodo.org/records/17096048

---

**Souza, B. P. et al. (2025)** — *A Journey of Functional Test Evolution in the Public Sector.*
SAST'25. UFRJ + UNIRIO + UFF + CAPGov-COPPETEC. File: `Tema 2- de Souza et al., 2025.pdf`

Experience report: 10-year partnership maintaining a large-scale legal system for a Brazilian
public institution. Documents 4 maturity stages (ad-hoc → manual → Selenium IDE → fully
automated). Key finding: "random generation of form element identifiers" was one of three
primary barriers to automation; fix was mandating consistent naming conventions across teams.
**Directly justifies the `data-testid` convention** used throughout the PoC frontend and
`ui_map.json` — empirical evidence from real Brazilian public-sector production experience
that naming stability is a precondition for reliable automation. Cite in AGENTS.md.

---

## Still needed (not yet uploaded)

- `hernandez-aguero-invest.pdf` — Hernández-Agüero, E.; Quesada-López, C.;
  Chaves-Sánchez, J. P. *LLM-Assisted INVEST Evaluation and Improvement of User
  Stories: An Industrial Replication Study.* (No public URL/DOI found — upload PDF
  and add DOI/link.)

## Verified online (no upload needed)

| Ref | Citation | Source | Status |
|---|---|---|---|
| Correia et al. | Conversational Models vs. Humans (Firefox case) | arXiv:2510.21933 | preprint, 2025 · co-authored by advisor R. de Mello |
| Quattrocchi et al. | Can LLMs Generate User Stories and Assess Their Quality? | arXiv:2507.15157 / IEEE TSE | published, 2026 |
| Sterling & Oliveira | Hybrid Intelligence in Requirements Education | MDPI Information 17(2):166 | published, 2026 |
| Wang et al. (CURE) | Co-Evolving LLM Coder and Unit Tester via RL | arXiv:2506.03136 | NeurIPS 2025 (Spotlight) |
| Qin et al. (DAJ) | Data-Reweighted LLM Judge for Test-Time Scaling | arXiv:2601.22230 | preprint, 2026 |
| Sakib et al. | From Reviews to Requirements | arXiv:2603.28163 | preprint, 2026 |

## Notes from the verification pass

- **Correia et al.** is marked "Material anexado" in the report but is public on
  arXiv — consider citing the arXiv ID. The report's wording slightly over-claims:
  the abstract confirms "a GPT model + RAG" (not explicitly GPT-4o) and frames
  quality as comprehensiveness/helpfulness/conciseness; its central trade-off is
  that **RAG makes answers more verbose** — the Context Builder should guard against this.
- **Qin et al.** and **Sakib et al.** are non-peer-reviewed preprints — flag as
  such in the final bibliography.
- **Sakib et al.** is cited in the report under "reliability/traceability," but its
  actual findings are about story *fluency* and a *lack of independence/diversity*;
  consider re-framing that citation alongside Quattrocchi (the "LLMs lack diversity" theme).
