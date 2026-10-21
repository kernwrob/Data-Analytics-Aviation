# Aircraft movements around Switzerland: plan for the final project

Prepared 1 October 2026. Planning basis: three students, six or more weeks, aircraft topic selected by the group. This is a route to a finished project; conclusions and grades cannot be promised before collection and analysis.

## 1. Recommended project

**Working title:** Beyond altitude: comparing aircraft ground speeds near major Swiss airports and farther away.

**Research question:** How does the relationship between altitude and aircraft ground speed differ near Zurich, Geneva and Basel airports versus farther away, and how well do altitude-only and spatially enriched regression models generalize to later days and other aircraft?

This goes beyond a standard prediction task in three ways: explicit geographical comparisons; a comparison of feature sets; and separate assessments of temporal and aircraft generalization. The aim is to describe patterns and evaluate models, not to prove that airport proximity causes speed changes.

**Primary source:** your own repeated OpenSky API observations. **Secondary source:** airport locations and attributes collected from OurAirports. Airport enrichment is an open reference dataset, not the primary dataset. The old group's saved observations cannot replace your collection.

**Unit of analysis:** one airborne aircraft position report. A snapshot contains many such observations. Multiple observations of the same aircraft are not independent flights. An ICAO24 identifies an aircraft, not a flight. Do not label row counts as flight counts.

**Scope:** the configured rectangle around Switzerland, including nearby foreign airspace. It is not a Swiss national boundary. Selected airports are LSZH, LSGG and LFSB; Basel is physically in France. Airport distance means distance to the nearest of these three selected airports, not the nearest airport worldwide.

**Provisional groups:** near <=30 km, middle >30 and <60 km, far >=60 km. These thresholds are study definitions, not aviation standards. Keep middle observations for EDA; use near/far for the main contrast. Run a sensitivity check with alternative thresholds after recording the primary choice. Do not optimize cutoffs to produce a desirable result.

## 2. Other aircraft ideas considered

| Idea | Comparison question | Data and additional work | Assessment |
|---|---|---|---|
| Airport proximity and speed | Does the altitude-speed relationship differ near selected airports; do spatial features improve later-day performance? | OpenSky + airport metadata; repeated collection | Recommended: directly feasible, joins and maps support the question |
| Climbing versus descending traffic | At comparable altitude and proximity, do ground speeds differ between climbing, descending and approximately level observations? | Same sources, vertical-rate coverage, prespecified thresholds | Good secondary comparison if vertical rate is sufficiently complete; do not claim inferred flight phase is verified |
| Airport approach patterns | Do spatial movement patterns around Zurich, Geneva and Basel differ by time of day? | Same sources, more local coverage and track segmentation | Visually strong; harder to infer departures/arrivals correctly from sparse observations |
| Wind and low-altitude ground speed | Does adding weather help models near airports, and does improvement differ by airport? | OpenSky + airports + a weather API; careful time/height alignment | Stretch only: surface wind is not wind at cruising altitude; forecast information must match the prediction time |

Do not add airport-delay prediction: state vectors do not supply reliable scheduled and actual arrival times. Do not use aircraft registration country as a departure country.

## 3. What the 5.5/6 reference teaches us

The provided presentation has a recognizable research question, EDA, maps, regression, model metrics, clustering and a statistical test. Its scope shows that a conventional Python workflow can cover many assessment topics; a large application is unnecessary.

Specific problems observed in the provided notebook:

1. Cell 5 includes `velocity` among the features while also setting `velocity` as the target. The linear model's R-squared of 1.0 and near-zero RMSE are explained by direct target leakage. Calling this simply possible overfitting misses the cause. Subsequent models using these features inherit the problem.
2. Cell 19 uses altitude, latitude, longitude and heading without speed as an input and reports R-squared about 0.881 and RMSE about 24.49 m/s. This is a distinct, more plausible saved evaluation, not confirmation of the perfect model. It has not been rerun here.
3. The test compares speed bins with clusters built partly from speed. The association is structurally built into the procedure and provides weak independent evidence. The saved test output also differs from the numbers in the explanatory markdown.
4. K-means is fitted without scaling speed and altitude, so the different units can dominate cluster assignments.
5. The visible main collection outputs cover snapshots rather than a substantial time series; one saved EDA output has all observation hours equal to 12. This cannot support a meaningful hourly traffic comparison.
6. Some plots say Switzerland although the fetch uses a European rectangle. The visible workflow does not document a join of independent sources. SQL storage is separated from much of the analysis.
7. The notebook contains embedded credentials. Do not copy, test, reuse or publish them. If you contact the original authors, they can decide whether to rotate their credentials.

The reference's grade does not establish that these practices satisfy your current rubric. Preserve the useful breadth and correct the methodology.

## 4. Collection pilot and go/no-go criteria

Start with a one-day pilot, then collect every five minutes for about 14 days. Five-minute sampling makes this a regional snapshot study, not reconstruction of complete flight trajectories. Short local movements and fast passages can be missed.

The configured rectangle is about 11 square degrees. Current OpenSky documentation lists one credit per `/states/all` request for bounding boxes <=25 square degrees, with 400 daily anonymous credits and 4,000 for standard authenticated users. A five-minute schedule is 288 requests/day before retries. Anonymous requests may share an IP quota; OAuth is preferable when available. Verify current limits at setup. Do not duplicate collectors.

For the pilot, check:

- both source downloads succeed and manifest entries exist;
- airport identifiers and coordinates are present and unique;
- snapshot coverage by hour is visible, with empty responses and failures recorded;
- positions and speeds are sufficiently complete after cleaning;
- there are observations near and far from selected airports;
- altitude ranges overlap between comparison groups;
- enough distinct aircraft remain in each group for meaningful descriptive analysis;
- the chosen computer can stay awake and online.

Counts and coverage are observations to report, not promised quantities. Prespecify a practical minimum after the pilot, such as at least 30 distinct aircraft in each principal comparison group and at least seven observed dates, with 14 complete days preferred. This is a scope rule, not a formal power calculation. Hundreds of snapshots of one aircraft do not substitute for independent aircraft.

If coverage is too thin, extend collection or adjust the geographical scope before freezing the analysis. If local positions remain sparse, switch the main comparison to climbing/descending/level observations with airport enrichment. If API access cannot be made reliable in week 1, reconsider the topic promptly rather than spend most of the project debugging collection. Historical OpenSky research access exists separately, but eligibility and access are not assumed.

## 5. Preparation, integration and storage

Preserve original JSON and the original airport CSV. Log collection time, requested bounds, source URL, HTTP outcome, filename and checksum. Failures and zero-aircraft snapshots matter when explaining gaps. Pin the first airport download; a later changing reference must not silently change results.

The implemented cleaner reports sequential counts for missing required fields, ground observations, stale or invalid records, duplicate aircraft-position timestamps and the airport join. It stores missingness before deletion. It checks position age and last-contact age against a provisional 60-second threshold. Review extreme altitudes/speeds separately; do not delete scientifically inconvenient outliers without explanation.

Spatial enrichment is explicit: calculate the great-circle distance from every aircraft coordinate to each selected airport, choose the closest, and attach its `ident`. Then join airport metadata by that identifier, validating many-to-one cardinality. The assignment always returns one of the three airports when inputs are valid; a 100% match therefore does not validate an actual origin or destination. Report distance distribution and threshold classifications as well as match rate.

Document rows before/after each step, lost/gained/unmatched counts, airport key uniqueness, unit conversions and timezone decisions. Convert speed to km/h only for presentation; keep model metrics in a clearly labeled unit. Geometric altitude is not height above terrain. OurAirports elevations are in feet; multiplying by 0.3048 converts to metres if later used.

SQLite stores `observations`, `airports` and `integration_audit`. SQL from Python performs the airport join, group aggregations, and descriptive queries. The included database builder creates unique indices and rejects duplicate keys. A richer PostgreSQL extension should use explicit types, primary/foreign keys and SQL queries, not merely copy an opaque dataframe.

**Rubric ambiguity:** the minimum explicitly requires SQLite, while the bonus explicitly says PostgreSQL or similar, no SQLite. The safest implementation is the required SQLite database plus a mirrored PostgreSQL database for the bonus, with Python SQL joins/aggregations shown for both. Ask the lecturer whether PostgreSQL alone can replace SQLite; until confirmed, keep SQLite. PostgreSQL is not implemented in this starter.

## 6. EDA that answers the question

Produce a compact set of informative outputs:

1. Data-quality table: source, dates, attempted/successful collections, raw/clean rows, distinct aircraft, missingness and exclusions.
2. Descriptive table by proximity group and airport: sample sizes, distinct aircraft, speed and altitude medians, IQRs and relevant tails.
3. Speed and altitude distributions, separated by group. Explain unequal distributions before interpreting regression.
4. Altitude versus speed scatterplots or binned summaries by zone, with transparent overplotting treatment.
5. Time coverage plot and local hour/weekday summaries, distinguishing unique-aircraft counts from observation counts. No claims about unobserved hours.
6. Map of selected airports and sampled observations colored by group or speed, with scale/units and a legend.
7. Model residuals and error by zone, airport, date and altitude band.

For group comparisons, inspect common altitude support. A near-airport group dominated by low altitude and a far group dominated by cruise altitude can make an apparent proximity difference reflect altitude composition. Compare within prespecified overlapping altitude bands and report groups that lack overlap. Aircraft type, weather and operational constraints remain potential confounders.

## 7. Regression and evaluation design

**Target:** observed ground speed in m/s. This is simultaneous estimation from other observed variables, not a promise to forecast future aircraft behavior.

**Fixed model set:** mean baseline; altitude-only linear regression; spatially enriched linear regression with an altitude-by-near interaction; random forest with a conservative fixed depth and minimum leaf size. Keep model choices small enough that all group members can explain them.

The starter uses altitude, airport distance, latitude/longitude, a near indicator and its interaction with altitude. Target speed and conversions of speed must never enter regression features. Aircraft identifiers are used for splits and counts, not as predictors. Heading or vertical rate can be added only after checking availability and representing circular heading correctly.

**Primary evaluation:** train on the earlier approximately 70% of observed UTC dates; evaluate on the later 30%. Fit preprocessing on training data only. Report exact train/test dates and aircraft overlap. Recurring aircraft in the later period are allowed: this answers later-day performance in the observed traffic mix, not performance on entirely new aircraft.

**Secondary evaluation:** fit fresh models using a group split by ICAO24, so train/test share no aircraft. This answers transfer to other aircraft within the collected period; it does not also establish future-day transfer. For a stronger joint challenge, hold out both later days and unseen aircraft if enough observations remain, and report the reduced sample.

The starter uses prespecified hyperparameters and no tuning. If you tune, create validation dates inside the training period and leave the final test untouched. Do not select thresholds, features or models on final test performance. Date-based validation is needed for time-dependent data.

Report MAE, RMSE and R-squared overall and by comparison group, plus baseline performance and sample sizes. MAE and RMSE are in m/s; R-squared can be negative on held-out data. A good score does not prove physical causation or safety for operational aviation use. Differences in held-out error need context: group imbalance, aircraft mix, observation density and coverage.

Add an aircraft-balanced sensitivity analysis or aggregation so that frequently observed aircraft do not dominate the interpretation. For uncertainty intervals, resample aircraft rather than treating all snapshots as independent; temporal dependence still needs discussion. This extension is planned, not implemented in the starter.

## 8. Statistics, clustering and creativity

**Statistical bonus:** a prespecified Spearman altitude-speed association with a reported coefficient, p-value and sample size. The starter selects one observation per aircraft on one deterministically selected analysis date and reports correlations separately for near/far where sample sizes permit. Freeze that date rule before examining associations. This reduces repeated-aircraft dependence but does not remove every shared-weather or temporal dependence issue. P-values are exploratory; a difference between two p-values is not a test of a difference between relationships. Report exact computed values, never invented example numbers.

For a direct adjusted comparison, add a regression interaction coefficient with suitable uncertainty, or an aircraft-level analysis within common altitude bands. Explain test assumptions and confounding. Do not test speed bins against clusters constructed from speed as if that were independent confirmation.

**Clustering bonus:** build aircraft-level median altitude/speed profiles, standardize features, compare k=2..5 with silhouette scores and inertia, and interpret centroid profiles. These are exploratory profiles in this sample, not verified aircraft types or flight phases. Whole-period clustering is descriptive and must not be used as a feature in temporal prediction without a separate training-only design.

**Creativity:** a map that combines proximity groups with model residuals, a data-coverage view, and a transparent later-day versus other-aircraft comparison. Make these support the research question. A dashboard is optional and not needed for a strong grade.

## 9. Every grading item has a deliverable

| Criterion | Concrete evidence | State |
|---|---|---|
| 1. Own collection | API script, raw snapshots, manifest, group-run collection | Script prepared; real collection pending |
| 2. Two-source integration | OpenSky + OurAirports, spatial assignment, audited key join | Builder prepared; real audit pending |
| 3. SQLite + Python SQL | SQLite artifact, SQL joins and aggregations | Builder prepared; database pending |
| 4. Rich EDA | Quality tables, distributions, comparisons, maps | Notebook prepared; outputs pending |
| 5. Regression beyond prediction | Proximity/airport and feature-set comparisons | Design and notebook prepared |
| 6. Evaluation | Baselines, temporal/group splits, MAE/RMSE/R-squared | Notebook prepared; results pending |
| 7. Interpretation | Results tied to question, limitations and sample coverage | Group review required |
| 8. AI documentation | Dated prompt/task/result/verification/failure log | Template prepared; maintain throughout |
| 9. Moodle material | Frozen data, databases, notebooks, environment, slide PDF/video | Final packaging pending |
| Bonus: creativity | Residual map and generalization comparison | Planned extension |
| Bonus: PostgreSQL | Mirror database + Python SQL join/aggregate | Not implemented; resolve rubric ambiguity |
| Bonus: geography | Airport enrichment and annotated maps | Notebook prepared |
| Bonus: statistical test | Coefficient, p-value, assumptions and sample size | Notebook prepared |
| Bonus: k-means | Scaling, k selection, centroids, interpretation | Notebook prepared |
| Bonus: public GitHub | Sanitized public code, README, URL on slides | Group must provide/create repository |
| Video: 7 criteria | 15-minute story, evidence, readable visuals, AI reflection, all speakers | Outline prepared; recording pending |

These entries are evidence targets, not guarantees of individual marks. Aim to satisfy all nine minimum requirements before spending time on bonus infrastructure.

## 10. Six-week plan for three people

| Week | Work | Exit condition |
|---|---|---|
| 1 | Select exact question and cutoffs; confirm lecturer topic approval; install tools; pilot sources; arrange collector | Both sources work; adequate group coverage; named collection owner |
| 2 | Continue collection; clean pilot; audit spatial join; SQLite SQL; initial EDA | Reproducible data build and logged exclusions |
| 3 | Finish approximately 14-day collection; freeze raw-data version; examine coverage/common support; create final EDA | Group can explain every source, variable, unit and join |
| 4 | Fixed baseline/regression models; temporal and aircraft splits; subgroup errors; statistics and k-means | Genuine held-out metrics, justified comparisons, no leakage |
| 5 | Sensitivity analysis; optional PostgreSQL mirror/residual map; independent run-through; interpret results | Every conclusion traceable to output; code runs from a clean start |
| 6 | Prepare final slides/PDF and script; rehearse; record 15-minute video; package Moodle and sanitize GitHub | All members can defend methods; timing and files verified |

Start collection early. Documentation, slides and the AI log grow throughout the project. Formal topic approval at the concept presentation is still required even if that presentation is ungraded. The exact course dates can change the schedule.

**Suggested ownership:** Student A owns collection, metadata, manifest and database; Student B owns EDA, integration review and geography; Student C owns modeling, evaluation and statistics. All three co-own interpretation, AI reflection and presentation. Cross-review another person's work; do not let only one member understand models or joins.

## 11. What the assistant can do, and what you must do

| Workstream | I can prepare or help complete | Your group must decide, verify or provide |
|---|---|---|
| Question/scope | Refine a defensible comparison and hypotheses | Interest, exact boundaries, course approval |
| Access/collection | Collector, OAuth setup guidance, scheduling instructions, debugging | Your account/access, machine and actual collection ownership |
| Data and SQL | Cleaning/integration code, schema, audit, database queries | Units/meaning, inclusion rules, suspicious observations |
| EDA | Tables, charts, maps and plain-language explanations | Which comparisons matter; check that interpretations match plots |
| Modeling | Splits, baselines, regression, evaluation, leakage checks | Explain predictors, target, split and limitations yourselves |
| Extra methods | Clustering, statistical tests, optional PostgreSQL workflow | Approve useful extensions and understand assumptions |
| Presentation | Slides/PDF, speaker draft, explanatory figures, rehearsal questions | Names, language, final claims, voices and video recording |
| Delivery | README, environment instructions, clean archive and public-code preparation | Repository ownership/publication and Moodle submission |
| AI reflection | Capture this work and subsequent fixes; summarize observed benefits/failures | Accurate personal reflection; preserve examples of your own checks |

Your involvement is primarily scientific judgment and understanding, not typing every line of code. I can help implement and explain the analysis as you collect data, but cannot obtain your grade, perform your video recording, or replace lecturer approval. This package is a starting implementation, not a claim that real collection or final analysis has already happened.

## 12. Final 15-minute presentation

Use about 10-12 content slides, plus references and backup material. Allocate approximately five minutes to each student. Suggested total: 1:30 context/question; 2:30 data/collection/integration; 3:00 EDA/geography; 3:30 models/evaluation; 2:00 conclusions/limitations; 2:30 AI reflection and closing. Put key metrics in readable tables and plots; avoid screenshots of long console output. Show code only when it clarifies a join, split or leakage check. Record actual total runtime; equal section labels alone do not guarantee timing.

The final claim may be a modest or null result. A spatial model that does not beat altitude-only regression is still an informative result if the experiment is sound. Never manufacture findings to match a planned story.

## 13. Decisions still needed

The topic family, group size and available time are confirmed. Next decisions: accept/refine the recommended question; name the collection owner; select exact start/end dates; confirm cutoff definitions and the analysis-date rule after the pilot; decide whether to pursue PostgreSQL; supply student names, final deadline and presentation language. Public GitHub is a planned bonus; publication of code is a separate action to authorize when the material is ready.

## Sources checked for feasibility

- OpenSky API schema, OAuth and current credit limits: https://openskynetwork.github.io/opensky-api/rest.html
- OpenSky current client documentation (basic authentication change): https://github.com/openskynetwork/opensky-api
- OpenSky terms for research, educational use and data sharing: https://opensky-network.org/about/terms-of-use
- OurAirports downloads and public-domain release: https://ourairports.com/data/
- OurAirports field meanings, keys and units: https://ourairports.com/help/data-dictionary.html
- Optional weather extension, modeled/reanalysis weather documentation: https://open-meteo.com/en/docs/historical-weather-api

Sources were checked as documentation, not as proof that live collection has succeeded from your computer. Current service restrictions and terms must be respected when collecting and sharing the final data.
