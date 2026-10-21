# Decision log

Confirmed: aircraft movements; three students; six or more weeks.

| Date | Decision | Reason | Owner | Evidence / lecturer response |
|---|---|---|---|---|
| Pending | Final research question | Airport/feature-set/generalization comparisons | All | Pending |
| Pending | Collection owner and dates | Reliable repeated group-owned collection | Student A | Pending |
| Pending | 30/60 km cutoffs and freshness rule | Freeze before inspecting final results | All | Pilot review |
| Pending | Analysis date rule for exploratory correlation | Avoid selecting a date for a desired p-value | Student C | Pending |
| Pending | SQLite plus optional PostgreSQL | Resolve conflicting minimum and bonus wording | All | Pending |
| Pending | Names, language, deadline | Final deliverables | All | Pending |

Record scope changes and why. Do not silently overwrite decisions after seeing test results.

## Technical progress — 1 October 2026

Local Python setup and anonymous source retrieval were verified. A bounded one-day collection pilot was registered for this machine, repeating every five minutes and expiring on 2 October; see `PILOT.md` and `outputs/pilot/schedule.json`. Original 30/60 km cutoffs, 60-second freshness and the spatial extent were used unchanged for the pilot. They are not yet frozen for final analysis. `requirements-lock.txt` records the tested environment. Group ownership, final collection dates and all scientific/lecturer decisions in the table remain pending.

## Follow-up work — 1 October 2026

| Decision/action | Reason and evidence | Status |
|---|---|---|
| End the technical pilot after sufficient approximately two-hour checks | Explicit user request supersedes the original one-day recommendation; 32 aligned scheduled responses, no scheduled gaps, integrity/join checks pass | Specific pilot disabled/stopped at 15:56:57 Zurich; originals/config retained; no new files after subsequent former ticks |
| Preserve normal laptop sleep/power behavior | User travels; downtime is missing observations | Main Start/Pause/Resume utility prepared; no main task registered, dates/duration await the group |
| Add optional pinned OpenSky aircraft metadata | Explain aircraft mix while preserving existing airport/speed analysis | 520,000 source records audited; 67.27% observation / 68.08% aircraft key coverage; left join preserves 4,115 rows |
| Use deterministic duplicate selection and unknown/other | No trustworthy recency field for choosing conflicting records; avoid unsupported categories | Most complete retained attributes, original record order tie-break; candidates/conflicts logged; fixed conservative description mapping documented |
| Prepare optional A/B/C category comparison | Isolate additional category information using the same observations and splits | Defined and tested for unseen categories; not run on pilot-only data |
| Private GitHub for code; restricted university folder for dated data | Separate code history from growing datasets and environments | Local Git/index prepared; author, private remote, collaborator usernames and folder location still needed; nothing uploaded |

Primary question, 30/60 km cutoffs, freshness, analysis-date rule, PostgreSQL choice and final deliverable decisions remain pending. Public code publication is a later authorized step. See `COLLABORATION.md`, `COLLECTION.md`, `METADATA.md` and `SHARING.md` for concrete workflows and conditions.

## Handover recheck — 1 October 2026

The pilot task remains disabled (last run 15:55:40 Zurich, result 0), and no main collection task is registered. The prepared repository still has no commit author or remote; account details and the restricted university folder are needed to finish access. README setup now distinguishes the collector from teammates using exports. Dataset switching must preserve the previous folder and copy a complete replacement into an analysis clone, because merging raw folders would change the agreed sample. No additional live collection was started.

## Airport-context review — 13 October 2026

The user identified omitted neighbouring airports as a possible problem. A read-only pilot audit confirms that 94 current far reports are within 30 km of Malpensa and 49 within 30 km of Bergamo; Frankfurt's closest pilot report is 225.7 km away. Proximity is not evidence of a verified flight phase or airport effect. See `outputs/pilot/airport_proximity_review.md` for airport-set sensitivity counts.

Proposed, not adopted: make the main question the incremental value of spatial context and optional category beyond altitude, with a stronger altitude-only baseline and the existing separate later-day/held-out-aircraft evaluations. Retain named-airport distances and add regional airport context using a documented inclusion rule and boundary buffer. Group/lecturer review is needed before changing classifications; existing config and database remain intact.

The user supplied the course evaluation text, preserved in `COURSE_EVALUATION.md`. The concept has a ten-minute slot and eight evaluation criteria, with formal topic approval at that presentation. Its grade weighting is not specified in the excerpt; do not assume it is ungraded.
