# References

Source citations for the QA Assistant Agent project (see [`../article.pdf`](../article.pdf)).
Status reflects a reference-verification pass on 2026-06-08.

## To upload here (not findable online)

Drop the PDFs in this folder with these filenames:

- `silva-llm-test-case-generation.pdf` — Silva, L. et al. *Investigating the Use
  of LLMs in Test Case Generation.* **Highest priority** — it underpins the
  evaluation metrics (`../plan.md` §8) and the Phase 8 comparison.
- `gheventer-industrial-readiness.pdf` — Gheventer, A. et al. *Generative AI
  Solutions for Software Quality: Assessing Industrial Readiness.*
- `souza-functional-test-evolution.pdf` — Souza, B. P. et al. *A Journey of
  Functional Test Evolution in the Public Sector.* (Backs the `data-testid` decision.)
- `hernandez-aguero-invest.pdf` — Hernández-Agüero, E.; Quesada-López, C.;
  Chaves-Sánchez, J. P. *LLM-Assisted INVEST Evaluation and Improvement of User
  Stories: An Industrial Replication Study.* (Not marked attached, but no public
  URL/DOI was found — please add the DOI/link too.)

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
