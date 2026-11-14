# Constitutional source review — 14 November 2026

The added notes are paraphrases checked against the Legislative Department,
Ministry of Law and Justice’s [official Constitution of India](https://www.legislative.gov.in/static/uploads/2025/08/b9a933fb88c0a5afba254256bc55a3f0.pdf).
Its cover states **“As on 10th September, 2026”**. Review here means comparison
with that source text, not approval by a lawyer or a claim to cover later case law.

| Catalog source | Provisions checked | PDF page (one-based) | Notes |
| --- | --- | --- | --- |
| `constitution-speech` | 19(1)(a), 19(2) | 40–41 | `speech-right`, `speech-limits` |
| `constitution-equality` | 14 | 37 | `equality-protection` |
| `constitution-liberty` | 21 | 42 | `liberty-protection` |
| `constitution-education` | 21A | 42 | `education-age` |
| `constitution-remedies` | 32(1), 32(2) | 50 | `remedies-court`, `remedies-writs` |

The source-library entries use PDF page fragments for navigation. All five refer
to one official document, not five independent authorities. Together with the
existing eight documents, the catalog has 13 source entries for nine documents,
23 notes, and ten introductory topics plus emergency signposting.

## Material qualifications preserved

- Speech: Article 19(1)(a) concerns citizens; the right is qualified by reasonable
  restrictions imposed by law under Article 19(2). Both notes are required context.
- Equality and personal liberty: Articles 14 and 21 refer to persons, not only citizens.
- Education: Article 21A specifies ages six to fourteen and provision in the manner
  determined by law. These notes do not promise free university or every private school.
- Remedies: Article 32 concerns enforcement of Part III fundamental rights through
  appropriate proceedings. The notes do not promise admission or success of a petition.

The collection does not provide the full interpretation of these provisions,
case-specific legal conclusions, other Article 19 freedoms, Article 21 privacy case
law, or filing procedures. Unknown article references and multi-topic article
comparisons return a coverage limit. Other unsupported wording can still evade the
heuristic checks; the evaluation is deliberately described as a regression set.

## Updating the corpus

1. Open the official source; verify the relevant provision, edition and qualifications.
2. Update `data/knowledge.json` with a concise paraphrase, stable fact ID, source ID,
   official HTTPS link, review date, article selectors and bounded topic description.
3. Keep a qualification in the same note or add it to the topic’s `requiredFacts`.
   Check that required context fits in four chunks. Never mark a statutory quote
   as a paraphrase or silently broaden a topic beyond its evidence.
4. Add positive and unsupported examples to `backend/eval_cases.json`; test both
   Python retrieval and the web outage fallback. Add independent examples before
   claiming broader accuracy.
5. Run ingestion, real-model tests, evaluation and the memory guard. A changed corpus
   fingerprint invalidates the cached index automatically; Render rebuilds it at deploy.
6. Push the reviewed change to the deployment branch. CI checks the app before
   deploying the exact backend revision and the matching Worker.

No live website scraping occurs during a chat. Source material remains a manually
maintained, versioned collection of introductory notes. Independent legal review
and a broader held-out evaluation remain outstanding.
