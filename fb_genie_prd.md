PRODUCT REQUIREMENT DOCUMENT (PRD)
UMHackathon 2026

- Project Name: F&B Genie
- Version: 1.0
1. Project Overview
Problem Statement:
Many small F&B business owners start a business based on instinct, personal confidence, or trends rather than structured investigation. They often lack access to consultants, reliable decision support, or a proper checklist to validate whether a location, target market, price point, and operating model are actually viable. As a result, businesses may open in unsuitable places, misread local demand, underestimate competition, ignore site realities, and enter financially unsustainable conditions.
Target Domain:
AI-assisted decision support for small and medium F&B business planning and operational review in Malaysia.
Proposed Solution Summary:
F&B Genie is an AI-powered business investigation partner for small F&B owners. Instead of only answering questions, it iteratively asks users for important business details, analyzes available data, integrates with tools such as Google Maps, Google Places, and Google Calendar, and generates field investigation tasks that users must complete to improve decision quality. The system helps users evaluate whether they should open a business, improve an existing one, pivot, or stop, based on available evidence, location context, competitor data, and financial realities.
2. Background & Business Objective
2.1 Background of the Problem
A large number of small F&B businesses begin with incomplete planning. Owners may choose locations based on convenience, emotion, or surface-level traffic assumptions without deeply investigating nearby competitors, actual customer flow, demographics, parking conditions, pricing fit, public transport accessibility, or environmental constraints. Even when owners know they should investigate further, they often do not know what to check, how to structure the investigation, or what findings should change their decision.
For ongoing businesses, owners may continue operating despite weak signals, negative margins, poor customer fit, or structural problems because they do not have a rigorous system to diagnose what is wrong. Existing advice tools are often too generic, too agreeable, or too passive to push the owner toward hard but necessary business decisions.
2.2 Importance of Solving This Issue
Helping small F&B owners make better pre-launch and post-launch decisions can reduce failed business openings, improve capital efficiency, and encourage more disciplined entrepreneurship. A system that identifies blind spots early, demands real-world validation, and updates its recommendations as new evidence is collected can give business owners a much more grounded path than intuition alone.
2.3 Strategic Fit / Impact
F&B Genie supports practical entrepreneurship by making structured business investigation more accessible to small business owners who cannot afford consultants. It also demonstrates how AI can move beyond passive chat into agentic decision support by interacting with external APIs, creating investigation tasks, and continuously refining its recommendations based on evidence.
3. Product Purpose
3.1 Main Goal of the System
To provide small F&B business owners with an AI investigation partner that helps them decide whether to launch, improve, pivot, or stop a business through iterative questioning, real-world task generation, external data integration, and strict evidence-based recommendations.
3.2 Intended Users (Target Audience)
- Small F&B business owners
- First-time food business founders
- Owners planning to open a new food stall, kiosk, café, or restaurant
- Existing small F&B operators seeking diagnosis, recovery, or business direction
3.3 Primary Market
Malaysia, with initial use cases tailored for local F&B operating conditions.
4. System Functionalities
4.1 Description
F&B Genie operates as an AI-driven business investigation system. It gathers user input in natural language, evaluates business context, enriches the analysis using external services such as Google Maps and Google Places, and identifies missing evidence that must be collected by the owner. The system then generates actionable tasks, such as visiting a location during peak hours, checking nearby competitors, validating school dining restrictions, observing queue lengths, or reviewing parking conditions. These tasks can be turned into real actions through integrations such as Google Calendar.
The system supports two main modes:
1. Pre-launch mode for evaluating whether a new F&B business and location are suitable.
2. Ongoing business mode for diagnosing weak performance, identifying improvements, or recommending recovery, pivot, or exit.
4.2 Key Functionalities
Iterative Business Investigation
The system asks follow-up questions progressively instead of depending on a single long prompt. This enables it to uncover missing details and challenge weak assumptions.
Location and Competitor Enrichment
Through Google Maps and Google Places, the system gathers nearby competitor information, surrounding business context, access patterns, and other site-related clues that improve its analysis.
Human-in-the-Loop Field Tasks
When digital data is insufficient, F&B Genie assigns real-world tasks to the user, such as checking lunch traffic, parking conditions, queue length, canteen pricing, school restrictions, or other on-site realities that only a human can validate.
Task-to-Action Workflow
Generated tasks can be turned into actionable follow-ups through integrations such as Google Calendar so users can schedule site visits, competitor reviews, and evidence collection.
Business Plan Generation
Based on available evidence, the system generates a business plan and practical next steps limited to areas that have actually been discussed with the owner.
Existing Business Diagnosis
For ongoing businesses, the system requests financial and operating information, identifies weaknesses, calculates or estimates basic business health indicators where possible, and recommends improvements, recovery strategies, or shutdown where necessary.
Strict Recommendation Engine
The system is designed to be decisive rather than agreeable. It can explicitly recommend proceeding, reconsidering, improving, pivoting, or not proceeding if evidence suggests the business is not viable.
Re-analysis After New Evidence
As users complete tasks and provide new findings, the system updates its recommendation and may strengthen, revise, or reverse earlier conclusions.
4.3 AI Model & Prompt Design
4.3.1 Model Selection
The primary model used is Z AI GLM.
4.3.2 Justification
Z AI GLM is selected because it offers strong reasoning capability at lower cost compared to some larger alternatives, making it more practical for repeated conversational questioning and iterative planning. It is also aligned with the hackathon context as a sponsor-backed technology choice.
4.3.3 Prompting Strategy
The system uses a multi-step agentic prompting approach. Instead of producing a one-shot answer, the model:
- gathers initial business context,
- identifies evidence gaps,
- generates investigation tasks,
- incorporates external API data,
updates its recommendations after new evidence is provided.
This fits the use case because F&B business decisions depend on partial information that improves over time, not on a single complete prompt.
4.3.4 Context & Input Handling
The system accepts natural language input as its main interface. Users may also provide optional supporting materials such as images, business details, sales reports, menus, street photos, or competitor observations. Because the selected model has a shorter context window, the system should summarize prior interaction history, retain key facts as structured memory, and keep only decision-relevant details in the active context. Oversized or excessive inputs should be summarized, chunked, or selectively retained based on relevance.
4.3.5 Fallback & Failure Behavior
If the model provides vague, unrealistic, off-topic, or hallucinated recommendations, the system uses a second evaluation step to assess whether the output is realistic and grounded. Where external API data appears incomplete or incorrect, the user may correct it, and the system will rerun the analysis using the corrected assumptions. If critical evidence is missing, the system should refuse to provide a final recommendation and instead issue further investigation tasks.
5. User Stories & Use Cases
5.1 User Stories
As a small F&B owner, I want the system to ask me the right questions so I do not miss important business factors.
As a new founder, I want the system to investigate my location and competitors so I can decide whether opening is worth the risk.
As an existing F&B owner, I want the system to analyze my finances and business conditions so I can understand whether to improve, pivot, or stop.
As a busy owner, I want important investigation tasks to be directly added to my calendar so I can act on the recommendations immediately.
As a user, I want the AI to challenge weak assumptions instead of blindly agreeing with me.
5.2 Use Cases (Main Interactions)
Use Case 1: New Business Evaluation
The user describes their business idea, product type, target area, approximate price range, and other basic details. The system asks follow-up questions, retrieves contextual data through APIs, identifies risks, and generates an initial business recommendation with investigation tasks.
Use Case 2: Site Investigation Workflow
The system detects missing evidence, such as uncertainty around school dining policies, parking conditions, or peak traffic. It generates tasks for the user and allows them to schedule those tasks through Google Calendar.
Use Case 3: Competitor Analysis
The system uses Google Maps and Google Places to identify nearby competitors and uses those findings to challenge the user’s assumptions about differentiation, saturation, or market fit.
Use Case 4: Existing Business Review
The user shares current business conditions and finance-related information. The system diagnoses possible causes of poor performance or hidden weaknesses, then recommends corrective actions, recovery directions, or exit.
Use Case 5: Re-analysis After Evidence Collection
The user returns with on-site findings, uploaded evidence, or corrected assumptions. The system updates the analysis and refines its final recommendation.
6. Features Included (Scope Definition)
- Natural language business intake and iterative questioning
- Pre-launch F&B location and viability analysis
- Existing business diagnosis and review
- Google Maps and Google Places integration for nearby competitor and environment analysis
- Google Calendar integration for investigation task scheduling
- Human-in-the-loop task generation
- Re-analysis after new evidence is submitted
- Optional file or image input for richer context
- Strict, evidence-driven AI recommendations
- Business plan generation limited to discussed areas
Recovery recommendation or shutdown recommendation for ongoing businesses where appropriate
7. Features Not Included (Scope Control)
- Full accounting or bookkeeping automation
- Full POS integration in initial version
- Automatic legal, licensing, or compliance submission
- Full demographic intelligence platform beyond available data integrations
- Autonomous execution of business decisions without user approval
Full marketing campaign management beyond draft assistance such as promo ideas or captions
- Franchise-scale multi-branch optimization in initial version
- Production-grade forecasting with guaranteed financial accuracy
8. Assumptions & Constraints
8.1 LLM Cost Constraint
Since the system depends on iterative questioning and re-analysis, token costs may increase with longer sessions. To control cost, the design should summarize previous conversations, store structured findings, and avoid repeatedly sending the full raw conversation back to the model.
8.2 Technical Constraints
The system depends partly on third-party APIs such as Google Maps, Google Places, and Google Calendar. Their coverage, rate limits, and returned data quality may affect system output. The chosen model also has a shorter context window, requiring careful context management and summarization.
8.3 Performance Constraints
Because the product may combine user input, API enrichment, and reasoning over multiple business factors, response quality may depend on how much reliable data is available at a given point in the workflow. Recommendations may need to remain provisional until key tasks are completed.
8.4 User Input Assumption
The system assumes the user is willing to answer follow-up questions, validate unknowns, and complete real-world investigation tasks. The quality of the final plan depends heavily on the completeness and honesty of user-provided information.
8.5 Data Reliability Constraint
External data sources may be incomplete, outdated, or misleading. The system must allow user correction and avoid presenting uncertain findings as absolute truth.
9. Risks & Questions Throughout Development
- Data Completeness Risk
- How should the system behave when Maps or Places data is sparse, ambiguous, or outdated?
- Overconfidence Risk
How can the system remain decisive without overstating certainty in cases where critical evidence is still missing?
- Recommendation Trust Risk
How should the system communicate harsh recommendations, such as not opening or shutting down, in a way that is firm but still credible and useful?
- Field Validation Dependency
Since many important factors require physical observation, how can the system maintain value if users do not complete the assigned tasks?
- Reasoning Quality Risk
How effective is the secondary model-check step in filtering unrealistic or hallucinated business recommendations?
- Scope Expansion Risk
How much business planning should be included before the product becomes too broad and loses focus on the core F&B viability workflow?
- User Adoption Risk
Will small business owners prefer a strict, challenging AI, or will they resist a system that disagrees with them strongly?
- Stronger one-line pitch
F&B Genie is an agentic AI business investigator that helps small F&B owners decide whether to open, improve, pivot, or stop by combining iterative questioning, real-world task assignment, API-enriched analysis, and strict evidence-based recommendations.
- Stronger judge-facing differentiation line
Unlike a normal chatbot prompt, F&B Genie does not only advise. It investigates, pulls external location context, assigns field tasks, integrates with calendar actions, and updates its business recommendation after new evidence is collected.