# Design justification

This note ties the research design to source rules, prior work, and theory. It is a crosswalk for the paper methods section, not a substitute for the literature review.

## Source key

| Key | Source |
| --- | --- |
| FSA-COA | Federal Student Aid Handbook, 2025-26, Volume 3, Chapter 2, Cost of Attendance: https://fsapartners.ed.gov/knowledge-center/fsa-handbook/2025-2026/vol3/ch2-cost-attendance-budget |
| FSA-PACK | Federal Student Aid Handbook, 2024-25, Volume 3, Chapter 3, Packaging Aid: https://fsapartners.ed.gov/knowledge-center/fsa-handbook/2024-2025/vol3/ch3-packaging-aid |
| FSA-PELL-SCHEDULES | Federal Student Aid Dear Colleague Letters, Federal Pell Grant Payment and Disbursement Schedules, 2009-2010 through 2023-2024; row-level URLs are stored in `config/policy_shocks.csv`. |
| FSA-YRP-2017 | Federal Student Aid GEN-17-06, Implementation of Year-Round Pell Grants: https://fsapartners.ed.gov/knowledge-center/library/dear-colleague-letters/2017-06-19/gen-17-06-subject-implementation-year-round-pell-grants |
| BLS-CPI-U | Bureau of Labor Statistics CPI-U all items annual averages, series `CUUR0000SA0`, annual average period `M13`: https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems |
| IPEDS-SFA | NCES, IPEDS Survey Methodology, Student Financial Aid component: https://nces.ed.gov/ipeds/survey-components/ipedssurveymethodologyprint?section=2 |
| IPEDS-ADM | NCES, IPEDS Admissions component: https://nces.ed.gov/ipeds/survey-components/6 |
| IPEDS-FIN | NCES, IPEDS Finance component: https://nces.ed.gov/ipeds/survey-components/2 |
| CELLINI-GOLDIN | Cellini and Goldin, 2014, "Does Federal Student Aid Raise Tuition? New Evidence on For-Profit Colleges," American Economic Journal: Economic Policy: https://www.aeaweb.org/articles?id=10.1257/pol.6.4.174 |
| LUCCA-NADAULD-SHEN | Lucca, Nadauld, and Shen, 2019, "Credit Supply and the Rise in College Tuition," Review of Financial Studies: https://doi.org/10.1093/rfs/hhy069 |
| AVERY-HOXBY | Avery and Hoxby, 2003, "Do and Should Financial Aid Packages Affect Students' College Choices?," NBER Working Paper 9482: https://doi.org/10.3386/w9482 |
| MARTIN | Martin, 2002, "Tuition Discounting: Theory and Evidence," Economics of Education Review: https://doi.org/10.1016/S0272-7757(00)00053-4 |
| CHESLOCK-RIGGS | Cheslock and Riggs, 2023, "Ever-Increasing Listed Tuition and Institutional Aid," Educational Evaluation and Policy Analysis: https://doi.org/10.3102/01623737221094565 |
| WINSTON | Winston, 1999, "Subsidies, Hierarchy and Peers: The Awkward Economics of Higher Education," Journal of Economic Perspectives: https://doi.org/10.1257/jep.13.1.13 |
| HOXBY-MARKET | Hoxby, 1997, "How the Changing Market Structure of U.S. Higher Education Explains College Tuition": https://www.nber.org/papers/w6323 |
| HOXBY-SELECTIVITY | Hoxby, 2009, "The Changing Selectivity of American Colleges," Journal of Economic Perspectives: https://www.aeaweb.org/articles?id=10.1257/jep.23.4.95 |
| DALE-KRUEGER | Dale and Krueger, 2002, "Estimating the Payoff to Attending a More Selective College: An Application of Selection on Observables and Unobservables," Quarterly Journal of Economics: https://www.nber.org/papers/w7322 |
| TOLBERT | Tolbert, 1985, "Institutional Environments and Resource Dependence: Sources of Administrative Structure in Institutions of Higher Education": https://hdl.handle.net/1813/75698 |
| BORUSYAK-HULL-JARAVEL | Borusyak, Hull, and Jaravel, 2022, "Quasi-Experimental Shift-Share Research Designs," Review of Economic Studies: https://doi.org/10.1093/restud/rdab030 |
| GOLDSMITH-PINKHAM-SORKIN-SWIFT | Goldsmith-Pinkham, Sorkin, and Swift, 2020, "Bartik Instruments: What, When, Why, and How," American Economic Review: https://doi.org/10.1257/aer.20181047 |
| ROTH | Roth, 2022, "Pretest with Caution," AER: Insights: https://doi.org/10.1257/aeri.20210236 |
| CM-CLUSTER | Cameron and Miller, 2015, "A Practitioner's Guide to Cluster-Robust Inference," Journal of Human Resources: https://doi.org/10.3368/jhr.50.2.317 |

## Conceptual model

The paper studies how published cost of attendance and aid packaging move together inside the Title IV budget constraint. Federal Student Aid rules make COA a central aid-budget object: COA limits total aid for several Title IV programs and enters Pell calculations. Packaging rules also require schools to account for Pell, other Title IV aid, non-Title IV aid, and overawards when building an aid package. That makes COA headroom a credible institutional margin even though IPEDS does not observe student-level packages.

The economic mechanism is not a single Bennett-hypothesis pass-through story. Prior evidence finds heterogeneous price responses to federal aid by sector, aid type, and institution type. For-profits are different enough that they should not define the baseline. Public and private nonprofit institutions also differ in accounting, subsidy sources, pricing autonomy, admissions markets, and revenue constraints. The design therefore treats sector splits as part of the estimand, not as an optional appendix.

The broader organizational frame is resource dependence. Colleges depend on external streams such as tuition, grants, government appropriations, endowment returns, and student demand. Price setting and aid packaging can therefore be read as organizational responses to resource constraints, enrollment management, and legitimacy pressures, not only as profit maximization. This matters most for public and nonprofit institutions, where the objective function includes enrollment, mission, access, quality, and budget balance.

## Design crosswalk

| Design choice | Why it is in the design | Basis | Boundary |
| --- | --- | --- | --- |
| Use institution-year IPEDS data. | The research question is about institution-reported COA and institution-level aid outcomes. IPEDS supplies annual institution-level COA, SFA, admissions, and finance fields. | IPEDS-SFA; IPEDS-ADM; IPEDS-FIN | Do not describe the estimates as student-level packaging effects. |
| Keep four-year Title IV public and private nonprofit institutions as the main sample. | Title IV status matches the federal-aid mechanism. Four-year public and private nonprofit institutions share the degree-level setting but differ enough to justify separate estimates. | IPEDS-SFA; WINSTON; HOXBY-MARKET | Do not claim a full postsecondary-sector estimate. |
| Exclude for-profits from the baseline. | For-profits have different incentives, regulatory exposure, program mix, and evidence in the Bennett-hypothesis literature. Keeping them separate avoids mixing different institutional models. | CELLINI-GOLDIN; LUCCA-NADAULD-SHEN | Use for-profits only as a named diagnostic or appendix sample unless the paper adds a separate for-profit design. |
| Use sector-specific outputs. | Sector-specific accounting and pricing rules mean common pooled coefficients can hide different mechanisms. | IPEDS-FIN; WINSTON; MARTIN; HOXBY-MARKET | Pooled sector-interaction models are checks, not replacements for sector estimates. |
| Treat the panel as unbalanced. | The target population changes through entry, exit, sector changes, and Title IV status changes. Dropping all nonbalanced institutions would change the estimand. | IPEDS source rules; local entry-exit audit | Report balance and minimum-years checks rather than forcing a balanced panel as the baseline. |
| Use off-campus, not-with-family non-tuition COA as the main headroom measure. | The theory concerns the allowance margin inside the published COA budget. Tuition is charge-like; books, room and board, and other expenses are allowance-like budget components. | FSA-COA; FSA-PACK | The measure is a published budget margin, not unused aid dollars for an individual student. |
| Pair headroom with FTFT SFA outcomes. | The IPEDS COA and SFA fields are closest for first-time, full-time cohorts. This keeps the aid outcomes near the pricing cohort. | IPEDS-SFA; FSA-PACK; AVERY-HOXBY | Use all-undergraduate aid fields as checks, not as the main measure. |
| Treat net price as secondary. | Net price has a different denominator, thinner coverage, and income-band structure. It is useful for incidence, but it is not the cleanest test of the COA-packaging margin. | IPEDS-SFA; FSA-PACK | Report net-price results after the main COA and aid outcomes. |
| Use open-admissions status in the baseline. | IPEDS admissions data are collected for institutions without open admissions. Requiring admit rates or test scores would drop open-admissions schools by design. | IPEDS-ADM | Keep admit rates and test scores in the selective-admissions sample. |
| Build a selectivity sensitivity index. | Selectivity affects pricing, demand, aid awards, and student composition. Admissions competition and academic signal both matter, so the index combines admit rate and test-score information within year. | DALE-KRUEGER; HOXBY-SELECTIVITY | The index is not a ranking and is not used to define the baseline. |
| Use a parsimonious baseline control set. | The baseline controls for admissions policy, scale, and fiscal capacity while institution and year effects absorb stable mission and common national shocks. This avoids turning the main design into a thin complete-case exercise. | FSA-PACK; IPEDS-SFA; local variable audit | Add richer controls only through named sensitivity designs. |
| Use SFA cohort counts as scale controls. | Ordinary enrollment fields do not have usable coverage in the verified local panel for this sample, while SFA cohort counts align with the FTFT aid outcomes. | IPEDS-SFA; local variable audit | Replace or supplement if upstream enrollment coverage is recovered. |
| Exclude ordinary enrollment and race-share controls from the baseline. | The missingness problem is empirical, not theoretical. Including these fields now would define the sample by data gaps rather than the research question. | Local variable audit | Record this as a data limitation and add a later sensitivity if coverage improves. |
| Harmonize finance controls by sector. | Public and private institutions report finance data under different accounting standards. Sector-specific construction is needed before common finance controls can be used. | IPEDS-FIN; WINSTON | Treat cross-sector finance controls as approximations, not identical accounting concepts. |
| Use institution and year fixed effects for the baseline. | Institution fixed effects absorb stable institutional differences; year effects absorb common national shocks. This estimates within-institution associations between headroom and aid outcomes. | Panel-design logic; CM-CLUSTER | The baseline is not causal by itself. |
| Cluster standard errors by institution. | Outcomes and residual shocks are likely serially correlated within institutions. | CM-CLUSTER | Report cluster counts and model diagnostics. |
| Keep baseline estimates unweighted, with FTFT-weighted checks. | The primary object is institutional behavior. FTFT weights answer a different question: how estimates look when larger FTFT cohorts receive more weight. | Theory of institutional behavior; IPEDS-SFA | Do not let the weighted check redefine the estimand. |
| Build descriptive decomposition before models. | The paper first has to show whether headroom is a meaningful empirical margin and whether component changes come from charge-like or allowance-like fields. | FSA-COA; local decomposition audit | Do not read descriptive component growth as a causal estimate. |
| Audit distribution tails before winsorization. | Large values may reflect real institutional scale, reporting rules, or errors. Capping before inspection would hide which case applies. | Local distribution audit | Use caps only as table or sensitivity choices, not as silent data edits. |
| Materialize model samples before estimation. | Complete-case drops should be visible before regression output is produced. A manifest makes sample size, singleton clusters, and within-variation checks auditable. | Replication practice; local model-plan audit | Do not hide sample construction inside estimator code. |
| Use a predetermined Pell-exposure design for policy tests. | A national Pell policy shock is absorbed by year fixed effects. Identification requires pre-period exposure to vary across institutions before the shock. | FSA-YRP-2017; FSA-PELL-SCHEDULES; BORUSYAK-HULL-JARAVEL; GOLDSMITH-PINKHAM-SORKIN-SWIFT | The design estimates differential change by exposure. It is not a treated-versus-untreated policy. |
| Use real maximum Pell changes for the repeated-shock design. | Nominal maximum Pell increases mix policy generosity with inflation. Expressing the maximum award in constant dollars gives the cleaner policy-intensity measure. | FSA-PELL-SCHEDULES; BLS-CPI-U | Keep nominal maximum Pell and large-increase flags as checks, not the preferred repeated-shock measure. |
| Keep the policy-shock registry separate from exposure estimation. | The national Pell schedule supplies timing and policy intensity, but timing or intensity alone is not institution-level treatment. The registry is therefore an input to exposure construction, not an estimate. | FSA-YRP-2017; FSA-PELL-SCHEDULES | Do not treat a national Pell change as a school-level shock without pre-period exposure. |
| Require placebo and pre-trend checks before causal wording. | A policy-exposure coefficient is credible only if high- and low-exposure institutions were not already moving differently before the policy. | ROTH; standard event-study logic | A sharp placebo blocks main causal claims for that outcome. |
| Use 2020-2021 exclusion as a sensitivity. | The pandemic period can affect COA budgets, enrollment, aid awards, and living arrangements through channels outside the 2017 Pell policy. | Design logic; local model specification | Treat it as a sensitivity, not a new baseline. |
| Keep metadata and zero-aid audits. | Reporting flags and internally inconsistent zeros can produce false movement in aid outcomes. | IPEDS source rules; local audit outputs | Use flags and suspect-zero exclusions as sensitivity checks. |
| Validate estimates before paper use. | Numerical success is not enough. The estimator must also pass model-count, rank, convergence, cluster-count, finite-estimate, and placebo checks. | CM-CLUSTER; ROTH; local validation gate | A failed design check should be reported as a limitation or block main-text use. |

## Claim implications

The current design can support three levels of claims.

1. Descriptive claims: COA headroom, aid outcomes, sector composition, and sample dynamics in the public/private nonprofit Title IV four-year panel.

2. Within-institution association claims: changes in headroom are associated with changes in institutional grant aid, Pell aid, loans, or net price within the same institution over time, after year effects and controls.

3. Policy-exposure claims: institutions with higher pre-period Pell exposure changed outcomes differently after the 2017 year-round Pell restoration, if placebo and pre-trend checks pass for the outcome.

At the current stage, headroom is the cleaner policy-exposure outcome. Institutional grant aid fails the 2016 placebo check and should remain diagnostic until the design is tightened.

## Manuscript wording

Use:

> I study cost-of-attendance headroom as a published institutional budget margin inside the Title IV aid cap. The design links that margin to FTFT aid outcomes and separates public from private nonprofit institutions because pricing autonomy, accounting rules, and subsidy environments differ by sector.

Use for baseline estimates:

> The baseline fixed-effects estimates are within-institution associations. They describe whether headroom and aid outcomes move together after absorbing institution and year effects.

Use for policy estimates only after validation:

> The policy-exposure estimates compare institutions with different pre-2017 Pell exposure before and after the 2017 year-round Pell restoration. I treat an outcome as policy-ready only when its placebo and sensitivity checks do not indicate differential pre-period movement.

Do not use:

> The estimates prove student-level grant substitution.

Do not use:

> The model shows institutions intentionally inflated COA.
