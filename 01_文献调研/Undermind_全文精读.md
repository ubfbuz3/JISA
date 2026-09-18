# Undermind 全文精读（12 篇）

本文档由 Undermind 的 `read_pdfs` 工具对 PDF 全文抽取产出，**不是摘要转述**。
每条提取均带 `[REGION: page=..., bbox=...]` 定位锚点，可回原文核对。

对照文献：[und_selection.json](_scripts/und_selection.json) ｜ 快照：[zotero_snapshot.md](for_codex/zotero_snapshot.md) ｜ 三路检索摘要：[三路检索摘要.md](三路检索摘要.md)

> 说明：`Zuo17`（AUTHSCOPE, CCS 2017）PDF 处于付费墙，未能全文精读，仅保留摘要。

---

## Hua24 · Detecting Broken Object-Level Authorization Vulnerabilities in Database-Backed Applications

- **venue**: Proceedings of the 2024 on ACM SIGSAC Conference on Computer and Communications Security ｜ **year**: 2024 ｜ **doi**: https://doi.org/10.1145/3658644.3690227
- **authors**: Yongheng Huang, Chenghang Shi, Jie Lu, Haofeng Li, Haining Meng, Lian Li

Based on the paper [Hua24], here are the details regarding the **BolaRay** tool and its methodology for detecting Broken Object-Level Authorization (BOLA) vulnerabilities:

### 1. Inference of Object-Level Authorization Models
BolaRay infers authorization models through a three-step process combining SQL parsing and static analysis (Section 4.1):
1.  **Building Database Schemas:** It extracts table names, columns, and keys from SQL scripts or source code strings to build a schema (Section 4.1.1).
2.  **Analyzing Table Relationships:** It identifies **implicit foreign keys**—columns referring to primary keys of other tables that are not explicitly declared in the schema. This is done by analyzing "complex interaction between program code and database queries," specifically identifying variables that hold primary key values and are used in subsequent query WHERE clauses (Section 4.1.2).
3.  **Identifying Authorization Models:** Using the table relationships and a set of heuristic-based rules (Figure 10), it classifies the relationships into four models (Section 3.2):
    *   **Ownership model:** A user directly owns an object (e.g., a user owns their profile).
    *   **Membership model:** A many-to-many relationship where objects are accessed by a specific group (e.g., users in a forum).
    *   **Hierarchical model:** A parent-child relationship where owning a parent object implies ownership of child objects (e.g., a post owner owning all comments on that post).
    *   **Status model:** Actions are permitted only when objects are in specific states (e.g., only "open" posts can be commented on).

The following figure illustrates the structure of these four models:
[REGION: page=4, bbox=87,495,334,917]

### 2. Detection of Vulnerabilities vs. False Positives
BolaRay decides an operation is a vulnerability if a sensitive database operation lacks the necessary authorization checks defined by its inferred model (Section 4.2). 
*   **Detection Logic:** It applies rules (Figure 11) such as `[Own-Check]` or `[Mem-Check]` to verify if a sensitive operation is guarded by conditions that compare the requester's identity to the object's owner or group membership (Section 4.2).
*   **Filtering False Positives:** To avoid over-reporting, BolaRay excludes three categories of operations from being considered "sensitive" (Section 4.3, "Locating Sensitive Operations"):
    *   **SELECT statements:** Since checking every read is too restrictive and often not required for non-confidential data.
    *   **INSERT operations in hierarchical models:** Based on empirical evidence that developers often don't view unauthorized inserts into child objects as security risks.
    *   **DELETE operations in Status models:** As status is typically ignored during deletions.

The formal rules for these safety checks are detailed below:

This set of rules defines how BolaRay verifies if a sensitive operation is "safe." It checks for administrative columns ([Admin-Check]), ownership ([Own-Check]), membership ([Mem-Check]), or status ([Stat-Check]) before declaring an operation secure.
[REGION: page=8, bbox=87,543,348,917]

### 3. Reported False-Positive Rate
BolaRay reported a total of **247 vulnerabilities**, of which **193 were confirmed as true vulnerabilities**, resulting in a **false-positive rate of 21.86%** (Section 5.2.2). 
*   **Measurement:** The researchers "manually examined the generated reports" to evaluate precision (Section 5.1). For new vulnerabilities, confirmation was sought from application maintainers; **155 vulnerabilities have been confirmed** to date (Section 1.3).

### 4. Evaluation Targets and Ground Truth
*   **Targets:** The tool was evaluated on **25 popular open-source database-backed PHP applications** (Section 5, Table 2). These included 19 applications widely used in previous research and 6 from the authors' own empirical study.
*   **Ground Truth:** 
    *   **Existing Vulnerabilities:** The ground truth for the empirical study (and for testing the tool against known bugs) was a **manually annotated dataset of 101 BOLA vulnerabilities** (Section 3.1). Three authors independently annotated each, with a fourth resolving disagreements.
    *   **New Vulnerabilities:** The ground truth was established via **manual annotation** of BolaRay's output by the authors, followed by reporting to maintainers for external verification (Section 5.1, 5.2.2).

### 5. Admitted Limitations
The authors explicitly list several limitations (Section 5.5):
*   **Manual DAL Specifications:** BolaRay requires manual annotation of Data Access Layer (DAL) specifications to understand how SQL is encapsulated in framework APIs (averaging 13 lines per API).
*   **Generalizability:** Currently, the implementation only supports PHP applications.
*   **SELECT Statements:** By ignoring SELECT statements to reduce false positives, the tool cannot detect BOLAs leading to sensitive information leakage.
*   **Incorrect Authorization Checks:** BolaRay is designed to find *missing* checks; it is not suited for detecting *incorrect* checks (e.g., checking against the wrong variable), which the authors note are "rare in practice."
*   **Heuristic Reliance:** The rules for inferring models are heuristic-based and "neither sound nor complete" (Section 4.4.1).

***

**Reference List:**
[Hua24] Yongheng Huang, Chenghang Shi, Jie Lu, Haofeng Li, Haining Meng, and Lian Li. 2024. Detecting Broken Object-Level Authorization Vulnerabilities in Database-Backed Applications. In Proceedings of the 2024 ACM SIGSAC Conference on Computer and Communications Security (CCS ’24), October 14–18, 2024, Salt Lake City, UT, USA. ACM, New York, NY, USA, 15 pages. https://doi.org/10.1145/3658644.3690227

---

---

## Dha25 · BACFuzz: Exposing the Silence on Broken Access Control Vulnerabilities in Web Applications

- **venue**: ArXiv ｜ **year**: 2025 ｜ **doi**: https://doi.org/10.48550/arXiv.2507.15984
- **authors**: I. P. A. Dharmaadi, Mohannad Alhanahnah, Van-Thuan Pham, Fadi Mohsen, Fatih Turkmen

Based on the paper [Dha25], here are the precise details regarding the BACFuzz framework:

### 1. Oracle Mechanism (SQL-based Checking)
BACFuzz uses **SQL checking** as its primary oracle to detect "silent" authorization flaws that do not produce crashes or explicit error messages. The mechanism works by instrumenting the web interpreter to record all SQL queries generated by the Web Under Test (WUT). It detects a vulnerability if mutated input values appear within data manipulation queries, indicating an authorization bypass (Section 4.3).

The paper defines two specific rules for detection:
*   **Rule 1: Broken Function-level (BFLA):** A vulnerability is flagged if a request submitted using a **lower-role account** results in a DML (Data Manipulation Language) query where at least one value matches the submitted request, provided that the function/request is not typically available to that user role (Section 4.3.1).
*   **Rule 2: Broken Object-level (BOLA):** A vulnerability is flagged if the fuzzer submits a request with **altered reference parameters** and detects a DML query where the `WHERE` clause value matches the mutated reference value, and that value is not found in the legitimate corpus for that user role (Section 4.3.1).

To ensure these are not accidental matches, the fuzzer employs **Multiple Checking**, repeating the test (e.g., 10 times) with different mutated values to confirm the vulnerability (Section 4.3.2).
[REGION: page=6, bbox=514,525,830,911]

### 2. LLM-Guided Parameter Selection
BACFuzz utilizes a Large Language Model (LLM) to identify **semantically important parameters** (referred to as "reference params") from system-generated data that may refer to protected objects or functions (Section 4.2.2).

*   **Role of the LLM:** The LLM is used only for **parameter analysis**. It identifies which parameters in an HTTP request are likely to be reference IDs or function calls (Section 4.2.2). 
*   **Final Judgement:** The LLM **does not make any final judgement** on whether a vulnerability exists. It merely labels parameters to prioritize them for mutation. The final determination of a vulnerability is handled by the **SQL checking oracle** based on runtime feedback (Section 4.2.2, Section 4.3).

The prompt used to guide the LLM in identifying these parameters is shown here:
[REGION: page=6, bbox=101,84,411,480]

### 3. Runtime Instrumentation
The framework employs lightweight code instrumentation using PHP libraries to capture:
*   **SQL Queries:** It uses the `uopz` library for function hooking to monitor original PHP functions related to SQL calls (e.g., `mysqli_query`, `mysqli_prepare`, `PDOStatement`) to catch queries sent to the database (Section 5.4).
*   **Code Coverage:** It uses the `PCOV` library to account for line coverage, which helps the fuzzer reach deeper statements within the application (Section 5.4).

### 4. Evaluation and Detection Rates
The evaluation was conducted on a set of **20 real-world PHP-based web applications**, which included 15 CVE cases and several benchmark applications like DVWA and XVWA (Section 6.1, Table 2).

*   **Known-Issue Detection Rate:** BACFuzz successfully detected **16 out of 17** known issues (Section 6.3). The single failure (CVE-2023-43663) was due to the application converting the submitted ID into a different internal ID before the SQL query, making the match fail (Section 6.3).
*   **New Vulnerabilities:** The tool uncovered **26 previously unknown** BAC vulnerabilities (Abstract, Section 6.3).
*   **False-Positive (FP) Level:** The authors report "low false positive rates." Table 2 shows a total of **11 false positives** across all tested applications (specifically: 5 for CVE-2024-7437/38, 2 for CVE-2024-8290, 3 for CVE-2023-43663, and 1 for OpenCart) (Table 2).

The following table summarizes the evaluation results across all 20 applications:
[REGION: page=9, bbox=126,84,412,912]

### 5. Admitted Limitations
The authors acknowledge several limitations of their approach:
*   **RBAC Focus:** The work focuses exclusively on **Role-Based Access Control (RBAC)**; other models like context-based or attribute-based access control are out of scope (Section 3.3).
*   **DML Dependency:** Because the oracle relies on DML queries (INSERT, UPDATE, DELETE), it cannot currently detect **passive or view-type BAC**, which only involves `SELECT` statements to gain unauthorized access to sensitive info (Conclusion).
*   **Context-Dependent BAC:** It cannot identify vulnerabilities that require specific **preconditions** or complex state transitions (e.g., a specific feature must be activated first) (Conclusion).
*   **Initial Data:** The fuzzer assumes the tester has already prepared the application with some initial data and registered users; it does not explore data insertion actions at the start (Section 3.3).

**Reference:**
[Dha25] I Putu Arya Dharmaadi, Mohannad Alhanahnah, Van-Thuan Pham, Fadi Mohsen, and Fatih Turkmen. 2025. BACFuzz: Exposing the Silence on Broken Access Control Vulnerabilities in Web Applications. In Proceedings of XXX (Under peer-review). ACM, New York, NY, USA, 12 pages.

---

---

## Cha22 · Metamorphic Testing for Web System Security

- **venue**: IEEE Transactions on Software Engineering, pp. 3430-3471 ｜ **year**: 2022 ｜ **doi**: https://doi.org/10.1109/TSE.2023.3256322
- **authors**: N. B. Chaleshtari, F. Pastore, Arda Goknil, L. Briand

In 'Metamorphic Testing for Web System Security' [Cha22], the authors propose **MST-wi**, an approach that uses metamorphic testing (MT) to address the oracle problem in web security testing by defining relations between multiple executions of a system.

### 1. Catalog of Security Metamorphic Relations
The authors provide a catalog of **76 system-agnostic metamorphic relations (MRs)** (Section 8). These MRs are designed to automate 16 OWASP security testing activities and detect 101 types of CWE vulnerabilities (Section 8).

For access control and authorization, the MRs typically compare outputs across different user roles or access methods. Key examples include:

*   **Bypass Authorization Schema (Fig. 2):** Verifies that if a URL is not provided to User-B via the GUI, User-B should receive a different response (e.g., an error) than User-A (who was provided the link) when requesting that URL directly.
*   **Incorrect User Management (Fig. 13):** Tests if a user can access resources dedicated to other users through direct requests.
*   **Directory Traversal (Fig. 17):** Checks if a user can access files outside the web document root by modifying parameters to random file paths.

The MRs are structured according to a template (Fig. 9) and categorized into **23 patterns (P1-P23)** based on combinations of preconditions, follow-up input generation strategies, and output conditions (Section 8.2, Table 4).

The following region shows Table 4, which lists the 23 MR patterns identified by the authors. This is crucial for designing a differential oracle as it maps specific precondition and generation strategies to expected output relations (equality, difference, etc.).
[REGION: page=17, bbox=428,47,764,953]

### 2. Avoiding a Ground-Truth Oracle
MST-wi avoids the need for a ground-truth (absolute) oracle by relying on **metamorphic relations (MRs)**. Instead of checking if an output $f(x)$ matches a specific expected value, it checks if the relationship between the outputs of multiple executions $\langle f(x_1), \dots, f(x_n) \rangle$ holds given a relationship between the inputs $\langle x_1, \dots, x_n \rangle$ (Section 2, Definition 1).

In the context of web security, this often manifests as a **differential oracle**:
*   **Role-based differentiation:** If User-A has permission and User-B does not, their outputs for the same resource should be "different" (Section 4.3).
*   **Input Sanitization:** If an attack string is injected, the output should either be an error page or identical to the output of a "clean" input (indicating the attack was neutralized) (Section 8.1.3).

The authors use a Domain-Specific Language (SMRL) to specify these relations, which are then transformed into executable Java code (Section 5).

### 3. Control and Filtering of False Positives
False positives (unwarranted failure reports) are controlled primarily through **preconditions** and **filtering logic**:

*   **Preconditions (Section 8.1.1):** MRs include checks to ensure the source input is valid for testing. For example, `!isSupervisorOf(User(2), User(1))` ensures that the differential test for authorization isn't invalidated by one user naturally having higher privileges than the other.
*   **Output State Verification:** Functions like `isError(Output)` are used to ensure the system is in a stable state before testing (Section 4.4, Table 2).
*   **Redundancy Filtering:** The approach uses `notTried(User, actionURL)` to avoid testing the same URL/User combination multiple times, which reduces noise and speeds up execution (Section 8.1.1).
*   **HTTP Request Focus:** MST-wi reports only failures that perform HTTP requests not generated by input sequences that led to previously reported failures, reducing the time spent analyzing duplicate triggers for the same vulnerability (Section 9.2.2).

### 4. Experimental Setup and Effectiveness
The authors evaluated MST-wi using two open-source subjects: **Jenkins (v2.121.1)** and **Joomla (v3.8.7)** (Section 10.1).

**Setup:**
*   **Data Collection:** Used an extended version of **Crawljax** to automatically derive source inputs, supplemented by 5 manual Selenium scripts to cover complex use cases (Section 10.2.1).
*   **Execution:** MRs were executed as JUnit tests within the Eclipse environment (Section 7).

**Effectiveness Numbers (Table 23):**
*   **Sensitivity (Fault Detection):** MST-wi detected **85.71%** of the targeted vulnerabilities (12 out of 14) when combining Crawljax and manual scripts.
*   **Specificity:** The approach showed high specificity at **99.81%**, meaning only 0.19% of generated inputs led to a false positive.

The following table summarizes the effectiveness results across the two case studies, showing that the addition of manual scripts significantly improved sensitivity for Jenkins.
[REGION: page=32, bbox=77,47,192,488]

### 5. Admitted Limitations
The authors identify several limitations (Section 9.3, Section 11):

*   **Non-Web Vulnerabilities:** MST-wi cannot address vulnerabilities that are not web-based or mobile-based (Reason **R1** in Table 11).
*   **Requirement for Program Analysis:** Some weaknesses (e.g., those requiring static analysis of code) cannot be detected via black-box interactions (Reason **R2**).
*   **Human Inspection Needed:** Certain outputs require human judgment to distinguish valid from invalid behavior (Reason **R3**).
*   **Combinatorial Explosion:** Testing all combinations of users, URLs, and parameters can lead to an explosion of test cases. While the authors suggest parallelization, some MRs still required over 14 hours to execute (Section 10.3.2).
*   **Asynchronous Actions:** Some false positives in Jenkins were attributed to asynchronous actions in source inputs that had not completed before the follow-up input was executed (Section 10.2.2).

The authors provide a detailed distribution of these reasons in Table 12:
[REGION: page=24, bbox=46,512,274,952]

***

**Reference:**
[Cha22] N. B. Chaleshtari, F. Pastore, A. Goknil, and L. C. Briand, "Metamorphic Testing for Web System Security," *IEEE Transactions on Software Engineering*, vol. 49, no. 4, pp. 1827-1854, 2023.

---

---

## Mai19 · Metamorphic Security Testing for Web Systems

- **venue**: 2020 IEEE 13th International Conference on Software Testing, Validation and Verification (ICST), pp. 186-197 ｜ **year**: 2019 ｜ **doi**: https://doi.org/10.1109/icst46399.2020.00028
- **authors**: Phu X. Mai, F. Pastore, Arda Goknil, L. Briand

Based on the paper [Mai19], here are the details regarding metamorphic security testing for Web systems:

### 1. Security Metamorphic Relations Covering Access Control
The authors provide a catalog of 22 system-agnostic metamorphic relations (MRs), several of which specifically target access control vulnerabilities as defined by OWASP [9].

*   **OTG-AUTHZ-002 (Bypass Authorization Schema):** This MR (shown in Figure 2) checks if URLs dedicated to specific users can be accessed by other users via direct requests. It specifies that if a URL is not reachable through the GUI for User B (but is for User A), the system should return different responses (e.g., an error for User B) when both attempt to access it.
*   **OTG-AUTHZ-001 (Directory Traversal/File Include):** As described in Table III, this MR ensures that a file path passed in a parameter never enables a user to access data not provided by the user interface. It uses nested loops to test various parameters with random file paths, verifying if the system either returns an error or content the user is already authorized to see.
*   **Additional Access Control MRs:** The "Notes" below Table III list other covered activities:
    *   **OTG-AUTHZ-003:** Testing for privilege escalation.
    *   **OTG-AUTHZ-004:** Testing for insecure direct object references.

The code for an access control MR is presented here, showing the logic for detecting if a user can reach a URL through the GUI versus a direct request:
[REGION: page=4, bbox=54,54,216,493]

Table III provides the logic and descriptions for several MRs, including directory traversal which is a form of unauthorized access:
[REGION: page=8, bbox=82,54,496,913]

### 2. Replacing Direct Oracles for Authorization Checks
The metamorphic approach addresses the **oracle problem** (the difficulty of determining the correct output for a given input) by reasoning about the **relations between outputs of multiple test executions** rather than specifying expected input-output behavior for every individual case (Section I).

For authorization, instead of knowing exactly what every user should see at every URL, the approach uses MRs to define expected properties:
*   **Differential Testing:** It compares the response of an authorized user (who found the URL via the GUI) with an unauthorized user (who requests the URL directly).
*   **Behavioral Consistency:** As stated in Section V-D, the relation indicates that the same sequence of actions should provide different outputs when performed by two different users under specific conditions (e.g., one user lacks supervisor privileges over the other).
*   **Automation:** The SMRL (Security Metamorphic Relation Language) allows these properties to be expressed declaratively and then automatically transformed into executable Java code that performs these multi-execution checks (Section VI).

### 3. Dealing with Ambiguous or Noisy Responses
Web systems often return slightly different content (e.g., timestamps or session IDs) even for functionally identical pages. The authors handle this "noise" using **edit distance**:
*   **State Detection:** During data collection, the framework uses edit distance to distinguish system states. If the distance between a new page and a cached page is below a 5% threshold, they are considered the same state (Section VII).
*   **Output Comparison:** To determine if two Web pages are equal during test execution (checking if a vulnerability was triggered), the framework also relies on edit distance (Section X, "Sensitivity is high").

### 4. Evaluation Results and False Positives
The approach was evaluated on two systems: a commercial Web system (E2) and Jenkins (Section X).

*   **Detection Rate (Sensitivity):** The approach detected **10 out of 12 (83.33%)** targeted vulnerabilities. It achieved 100% sensitivity for E2 and 75% for Jenkins when using both automated crawling and manual scripts (Table VI).
*   **Specificity:** The overall specificity was **99.50%**, meaning false alarms were very rare.
*   **False Positives:** Only **32 out of 6401** generated inputs (~0.5%) resulted in false alarms. These were primarily due to limitations in the crawler (Crawljax) failing to traverse all URLs for all users, leading the MR to incorrectly assume a URL was "unreachable" via the GUI when it actually was (Section X).

The summary of these results is captured in Table VI:
[REGION: page=10, bbox=64,48,145,479]

### 5. Admitted Limitations
The authors acknowledge several limitations of their current approach:
*   **Missed Vulnerabilities:** Two targeted vulnerabilities in Jenkins were not detected. One required server configuration modifications during execution (which the tool does not support), and the other involved a non-interruptible reboot process that could not be reproduced (Section X).
*   **Crawler Limitations:** The sensitivity of the approach drops (below 75% for Jenkins) if it relies solely on automated crawling (Crawljax) without manual test scripts to reach complex features, such as those requiring specific valid input sequences (Section X).
*   **Combinatorial Explosion:** Testing all possible combinations of inputs and users can lead to very long execution times; the authors currently cap testing at 24 hours per MR (Section IX).
*   **Environmental Constraints:** The approach cannot currently handle vulnerabilities that require modifying the server environment or configuration during the test run (Section X).

***

**References:**
*   [9] M. Meucci and A. Muller, “OWASP Testing Guide v4,” https://www.owasp.org/images/1/19/OTGv4.pdf.
*   [32] Authors of this paper, “SMRL editor executable, catalog of MRs, MT framework, experimental data.” https://sntsvv.github.io/SMRL/.
*   [103] MITRE, “CVE-2018-1999047, concerns OTG-AUTHZ-002,” https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-1999047.
*   [105] MITRE, “CVE-2018-1999045, concerns OTG-AUTHZ-002,” https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-1999045.

---

---

## Wan24b · A hybrid LLM workflow can help identify user privilege related variables in programs of any size

- **venue**: ArXiv ｜ **year**: 2024 ｜ **doi**: https://doi.org/10.48550/arXiv.2403.15723
- **authors**: Haizhou Wang, Zhilong Wang, Peng Liu

Based on the paper, here is the detailed report on the hybrid LLM workflow for identifying user privilege related (UPR) variables.

### 1. Hybrid Workflow Steps
The workflow consists of six major steps, combining deterministic static analysis with LLM-based semantic rating (Section IV-B, Page 5).

*   **Step 1 (Deterministic):** Static analysis of source code files to generate a Program Dependence Graph (PDG) for each function.
*   **Step 2 (Deterministic):** Slicing the PDG into variable subgraphs, each corresponding to a single variable in the program.
*   **Step 3 (Deterministic):** Collecting a unique set of code statements from these subgraphs that are either control or data dependent on the variables.
*   **Step 4 (LLM):** Rating each unique code statement using an LLM to generate a "UPR rating" based on its relationship to user privileges.
*   **Step 5 (Deterministic):** Updating the variable subgraphs by assigning the LLM-generated ratings to the corresponding nodes.
*   **Step 6 (Deterministic):** Aggregating these node scores using a specific algorithm to compute a final "UPR score" (0–10) for each variable.

This workflow is illustrated in the following diagram:

The workflow starts with source code, uses static analysis to extract PDGs and variable subgraphs, employs an LLM to rate individual code statements, and finally aggregates those ratings into a final UPR score for each variable.
[REGION: page=6, bbox=71,114,321,885]

### 2. LLM Task and Grounding
**The Task:** The LLM is asked to act as a "security critical code statement identifier" and provide a "criticalness rating from 0 to 10" for individual code statements (Section V, Page 8). It is provided with a list of "malicious goals" (e.g., bypassing authentication, gaining elevated privileges) to provide context for what constitutes a UPR-related statement.

**Validation/Grounding:** To prevent the LLM from producing arbitrary results, its output is grounded through **Algorithm 1 (Compute UPR score)**. Instead of a binary verdict, the LLM's statement-level ratings are weighted and aggregated based on the program's actual dependency structure (the graph topology).

Algorithm 1 defines how the UPR score is computed by considering a criterion node and its immediate neighbors in the dependence graph, using a parameter $\lambda$ to weigh the influence of neighboring nodes.
[REGION: page=7, bbox=205,510,432,900]

### 3. Accuracy and Precision Figures
The method was evaluated on 7 open-source programs (e.g., `nginx`, `sshd`, `sudo`). Using a UPR score threshold of $>8.0$ (or $9.0$ in some experiments):

*   **Average False Positive Rate (FPR):** 13.49% (Table I, Page 9).
*   **Efficiency:** Out of 4,455 analyzed variables, only 645 required manual inspection, saving analysts approximately 85% of the time compared to checking all variables (Section II, Page 2).
*   **Comparison:** The tool identified significantly more UPR variables than heuristic-based methods (like `semgrep` rules) while maintaining a much lower FPR (13.49% vs. 54.53% for heuristics) (Section VI-C, Page 9; Figure 5, Page 10).

Table I provides a breakdown of the variables analyzed and detected across different programs, showing a consistent FPR around 13-15%.
[REGION: page=9, bbox=68,542,192,864]

### 4. Observed Failure Modes
The authors identify two primary failure modes for the LLM component:
*   **PDG Granularity:** Variables with nearly identical subgraphs can lead to false alarms. For example, `cleartxt_passwd` (a UPR variable) and `cleartxt_passwd_len` (not a UPR variable) often appear in the same statements, leading to similar UPR scores for both (Section VI-B, Page 9).
*   **Mediocre Ratings (Context Loss):** Because the LLM rates statements in isolation to minimize context length, it may assign "mediocre" (middle-range) scores to statements that lack clear UPR indicators when viewed without the surrounding function logic (Section VI-D, Page 10).

### 5. Admitted Limitations
*   **Proprietary Programs:** LLMs are trained on open-source data. The authors note that the "UPR rating for code statements in open source programs are in-distribution data," whereas proprietary code is "out-of-distribution," which might affect performance (Section VII-A, Page 11).
*   **Cost of Service:** Every unique statement requires an LLM call. While they minimize tokens by avoiding long code snippets, there is still a per-statement cost (Section VII-B, Page 11).

### 6. Preventing the LLM from being the Final Judge
The authors explicitly design the system to avoid a "binary verdict" from the LLM (Section IV-A, Page 5). They prevent the LLM from being the final judge by:
1.  **Outputting a Score, Not a Verdict:** The tool produces a quantitative **UPR score** (0–10) that reflects the *degree* of relevance, acknowledging that some variables are "borderline" (Section IV-A).
2.  **Mandatory Human Review:** The workflow concludes with the statement: "To confirm a UPR variable, subsequent manual review is necessary for those with highest ratings" (Section IV-B, Page 5).
3.  **Algorithmic Filtering:** The LLM's subjective rating is filtered through the objective lens of the Program Dependence Graph (PDG), meaning a high rating only results in a high UPR score if it is supported by the variable's actual role in the code's data/control flow.

***

**References:**
[1] N. Provos, M. Friedl, and P. Honeyman, “Preventing privilege escalation,” in 12th USENIX Security Symposium (USENIX Security 03), 2003.
[2] F. Jaafar, G. Nicolescu, and C. Richard, “A systematic approach for privilege escalation prevention,” in 2016 IEEE International Conference on Software Quality, Reliability and Security Companion (QRS-C). IEEE, 2016, pp. 101–108.
[3] H. Shacham, “The Geometry of Innocent Flesh on the Bone: Return-into-libc Without Function Calls (on the x86),” in CCS, 2007.
[4] S. Checkoway, L. Davi, A. Dmitrienko, A.-R. Sadeghi, H. Shacham, and M. Winandy, “Return-Oriented Programming Without Returns,” in Proceedings of the 17th ACM Conference on Computer and Communications Security, 2010.
[5] H. Hu, S. Shinde, S. Adrian, Z. L. Chua, P. Saxena, and Z. Liang, “Data-Oriented Programming: On the Expressiveness of Non-control Data Attacks,” in Proceedings of the 37th IEEE Symposium on Security and Privacy, 2016.
[6] Z. Feng, D. Guo, D. Tang, N. Duan, X. Feng, M. Gong, L. Shou, B. Qin, T. Liu, D. Jiang et al., “Codebert: A pre-trained model for programming and natural languages,” arXiv preprint arXiv:2002.08155, 2020.
[7] D. Guo, S. Ren, S. Lu, Z. Feng, D. Tang, S. Liu, L. Zhou, N. Duan, A. Svyatkovskiy, S. Fu et al., “Graphcodebert: Pre-training code representations with data flow,” arXiv preprint arXiv:2009.08366, 2020.
[8] X. Li, Q. Yu, and H. Yin, “Palmtree: Learning an assembly language model for instruction embedding,” arXiv preprint arXiv:2103.03809, 2021.
[9] O. Press, N. Smith, and M. Lewis, “Train short, test long: Attention with linear biases enables input length extrapolation,” in International Conference on Learning Representations, 2022.
[10] S. Chen, S. Wong, L. Chen, and Y. Tian, “Extending context window of large language models via positional interpolation,” arXiv preprint arXiv:2306.15595, 2023.
[11] G. Xiao, Y. Tian, B. Chen, S. Han, and M. Lewis, “Efficient streaming language models with attention sinks,” arXiv preprint arXiv:2309.17453, 2023.
[12] N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, “Lost in the middle: How language models use long contexts,” arXiv preprint arXiv:2307.03172, 2023.
[13] C. E. Jimenez, J. Yang, A. Wettig, S. Yao, K. Pei, O. Press, and K. Narasimhan, “Swe-bench: Can language models resolve real-world github issues?” arXiv preprint arXiv:2310.06770, 2023.
[14] M. Weiser, “Program slicing,” IEEE Transactions on software engineering, no. 4, pp. 352–357, 1984.
[15] Z. Yu and V. Rajlich, “Hidden dependencies in program comprehension and change propagation,” in Proceedings 9th International Workshop on Program Comprehension. IWPC 2001. IEEE, 2001, pp. 293–299.
[16] J. Ferrante, K. J. Ottenstein, and J. D. Warren, “The program dependence graph and its use in optimization,” ACM Transactions on Programming Languages and Systems (TOPLAS), vol. 9, no. 3, pp. 319–349, 1987.
[17] S. Kang, J. Yoon, and S. Yoo, “Large language models are few-shot testers: Exploring llm-based general bug reproduction,” in 2023 IEEE/ACM 45th International Conference on Software Engineering (ICSE). IEEE, 2023, pp. 2312–2323.
[18] C. Lemieux, J. P. Inala, S. K. Lahiri, and S. Sen, “Codamosa: Escaping coverage plateaus in test generation with pre-trained large language models,” in International conference on software engineering (ICSE), 2023.
[19] C. S. Xia, M. Paltenghi, J. L. Tian, M. Pradel, and L. Zhang, “Universal fuzzing via large language models,” arXiv preprint arXiv:2308.04748, 2023.
[20] Nergal, “The Advanced Return-into-lib(c) Exploits,” http://phrack.com/issues.html?issue=67&id=8.
[21] T. Bletsch, X. Jiang, V. W. Freeh, and Z. Liang, “Jump-Oriented Programming: A New Class of Code-reuse Attack,” in Proceedings of the 6th ACM Symposium on Information, Computer and Communications Security, 2011.
[22] S. Chen, J. Xu, E. C. Sezer, P. Gauriar, and R. K. Iyer, “Non-Control Data Attacks Are Realistic Threats,” in Proceedings of the 14th USENIX Security Symposium, 2005.
[23] S. Robertson, H. Zaragoza, and M. Taylor, “Simple bm25 extension to multiple weighted fields,” in Proceedings of the thirteenth ACM international conference on Information and knowledge management, 2004, pp. 42–49.
[24] T. M. Austin and G. S. Sohi, “Dynamic dependency analysis of ordinary programs,” in Proceedings of the 19th annual international symposium on Computer architecture, 1992, pp. 342–351.

---

---

## Wen24 · Enchanting Program Specification Synthesis by Large Language Models using Static Analysis and Program Verification

- **venue**: International Conference on Computer Aided Verification, pp. 302-328 ｜ **year**: 2024 ｜ **doi**: https://doi.org/10.48550/arXiv.2404.00762
- **authors**: Cheng Wen, Jialun Cao, Jie Su, Zhiwu Xu, Shengchao Qin, Mengda He, and Cong Tian

In the paper "Enchanting Program Specification Synthesis by Large Language Models using Static Analysis and Program Verification" [Wen24], the authors present **AutoSpec**, a framework that uses a "generator-validator" architecture to synthesize formal specifications (ACSL annotations) for C programs.

### 1. Combination of LLM, Static Analysis, and Program Verifier
AutoSpec combines these three components in a three-step workflow:
*   **Static Analysis (Code Decomposition):** AutoSpec uses static analysis to decompose a C program into an **extended call graph**, where both functions and loops are treated as nodes. This graph determines the order of specification generation (Section 3.1, page 7).
*   **LLM (Candidate Generation):** Large Language Models (specifically GPT-3.5 and Llama-2 in the study) act as generators. They are prompted to "infill" candidate specifications into placeholders inserted at the locations identified by the static analysis (Section 3.2, page 8).
*   **Program Verifier (Validation):** A theorem prover (Frama-C with the WP plugin) acts as the validator. It checks the candidate specifications generated by the LLM for legality, satisfiability, and adequacy (Section 3.3, page 10).

The following figure illustrates this overview:

The workflow starts with a C program and properties to be verified, progresses through code decomposition and hierarchical specification generation using LLMs, and uses a verification tool to produce a final result.
[REGION: page=7, bbox=214,217,333,782]

### 2. Interaction Protocol: Verifier Gating and Correction
The verifier (theorem prover) acts as a rigorous filter for the LLM's outputs. The process follows a "LLM proposes, verifier disposes" protocol:
*   **Legality and Satisfiability Check:** For each function/component, the LLM generates a set of candidate specifications ($spec_{tmp}$). The verifier checks if they are syntactically correct (legal) and if the code can actually satisfy them (satisfiable). Any illegal or unsatisfiable specifications are discarded (Section 3.3, page 10).
*   **Adequacy Check:** Once a set of satisfiable specifications is gathered, the verifier checks if they are "adequate"—meaning they are sufficient to prove the target property. If the verification fails, the system triggers another iteration to generate more specifications (Section 3.3, page 11).
*   **Error Accumulation Avoidance:** By validating in each round, AutoSpec ensures that only "validated" specifications are kept for the next round of synthesis, preventing the LLM from building upon its own previous mistakes (Abstract, page 1).

### 3. Loop Structure and Termination Condition
The core logic is defined in **Algorithm 2: Hierarchical Specification Generation** (page 9).

*   **Loop Structure:** It consists of an outer loop iterating up to a predefined limit $t$ (set to 5 in the evaluation) and an inner loop that traverses the program hierarchy in a bottom-up manner using a stack $S$.
*   **Termination Conditions:** The process terminates when:
    1.  The target property (assertion $ass$) is successfully verified by the theorem prover: `if spec_validation(C, ass) then ... break` (Algorithm 2, Line 16).
    2.  The iteration count reaches the predefined upper bound $t$ (Algorithm 2, Line 2).

The hierarchical generation algorithm is detailed here:

This algorithm shows the iterative process of using a stack to traverse the call graph bottom-up, querying the LLM for candidates, validating them, and terminating either on success or reaching the iteration limit.
[REGION: page=9, bbox=121,217,399,782]

### 4. Evaluation Results and Success Rates
The evaluation was conducted on 251 C programs across four benchmarks and one real-world project:
*   **Overall Success Rate:** AutoSpec successfully verified **79% (199 / 251)** of the programs (Abstract, page 1).
*   **Comparison:** This represents a **1.592x improvement** over state-of-the-art tools like Pilat, Code2inv, and CLN2Inv, which were limited to programs with linear loops (Section 3, page 3).
*   **Real-world Application:** In the X509-parser project, AutoSpec successfully generated specifications for six representative functions within a few minutes (Section 4.2, page 14).

Statistical details of the benchmarks are provided in Table 1:

This table lists the five benchmarks used (Frama-C-problems, X509-parser, SyGuS, OOPSLA-13, and SV-COMP), the number of programs in each, and the types of specifications generated.
[REGION: page=11, bbox=148,217,215,782]

### 5. Admitted Limitations
The authors identify several limitations of the current approach:
*   **Missing Context/Dependencies:** AutoSpec fails when the necessary context (e.g., external library code like `<math.h>`) is not provided in the prompt, as the LLM cannot determine the expected behavior of external functions (Case 2, page 18).
*   **Semantic Bugs:** If the input program is semantically buggy, AutoSpec cannot synthesize adequate specifications, as the properties are fundamentally unprovable (Section 3, page 6).
*   **Scalability:** While it performed well on the X509-parser functions, the authors admit that "completing the whole verification task on the entire project remains challenging" (Section 5, page 19).
*   **LLM Intrinsic Weaknesses:** The authors acknowledge that LLMs "can make mistakes," may suffer from "lost in the middle" attention issues, and that "errors accumulate" in their output—which is why the validation step is mandatory (Section 2, page 2).

***

**References:**
[Wen24] Cheng Wen, Jialun Cao, Jie Su, Zhiwu Xu, Shengchao Qin, Mengda He, Haokun Li, Shing-Chi Cheung, and Cong Tian. Enchanting Program Specification Synthesis by Large Language Models using Static Analysis and Program Verification. arXiv:2404.00762v2 [cs.SE], 2 Apr 2024.

---

---

## Wan25d · Large Language Model-Powered Protected Interface Evasion: Automated Discovery of Broken Access Control Vulnerabilities in Internet of Things Devices

- **venue**: Sensors (Basel, Switzerland) ｜ **year**: 2025 ｜ **doi**: https://doi.org/10.3390/s25092913
- **authors**: Enze Wang, Wei Xie, Shuhuan Li, Runhao Liu, Yuan Zhou, Zhenhua Wang, and Baosheng Wang

In the paper **[Wan25d]**, the authors present **ACBreaker**, an LLM-powered tool designed to discover broken access control vulnerabilities in IoT devices.

### 1. LLM Usage and Generation
The LLM is primarily used in the **Intelligent Firmware Analysis** stage to extract device-specific information from semantically intact code snippets provided by a code slicer (Section 5.1).

*   **How it is used:** The system employs a **two-round inference strategy** guided by **Chain-of-Thought (CoT)** prompting (Sections 5.1 and 5.1.4).
    *   **Round 1:** The LLM identifies structural elements for information extraction and marks complex parameters (e.g., those requiring encryption or complex logic) with placeholders.
    *   **Round 2:** The LLM performs targeted reasoning on these placeholders to infer specific constraints and instance values, such as MD5-based token generation logic (Section 5.1.4).
*   **What it generates:** The LLM produces structured JSON output containing two categories of information (Section 5.1.1):
    *   **File Information:** Interface access paths (e.g., `/admin/user/`), file identifiers (e.g., `settings`), and file types (e.g., `.php`).
    *   **HTTP Information:** Protocol versions, request methods, HTTP headers (e.g., `Content-Type`, `Authorization`), and specific request parameters (e.g., `username=admin`).

The prompt construction process, including role definition and few-shot learning, is detailed in Figure 7:
[REGION: page=10, bbox=268,278,683,809]

### 2. Verification of Candidate Failures
Candidate failures are verified using a **Difference Analyzer** that employs a three-layer filtering mechanism to distinguish real violations from false positives (Section 5.2.3 and Algorithm 2):

1.  **Preprocessing Strategy:** Filters out invalid responses (status codes 400, 404, 501) and empty response bodies. It also discards responses where the content is identical to the baseline despite a status code change, as this often indicates an error-handling mechanism rather than evasion (Section 5.2.3).
2.  **Status Code Transition-based Detection:** Identifies potential evasion when a status code transitions from restricted (401 Unauthorized or 403 Forbidden) to successful (200 OK or 202 Accepted) (Section 5.2.3).
3.  **Response Body Difference-based Detection:** To handle cases where status codes are unreliable, it uses **FNV-1a hashing** to calculate page similarity. It filters dynamic content (like timestamps) and considers a vulnerability "true" if the similarity to a successful baseline is below a **0.9 threshold** (Section 5.2.3, Section 5.3).

### 3. Evaluation Targets and Disclosure
*   **Evaluation Targets:** ACBreaker was evaluated against **11 commercial IoT devices** from leading manufacturers: Netgear, TP-Link, D-Link, Redmi, Xiaomi, and ASUS (Section 6.1). The devices include routers, NAS, and modems (Table 2).
*   **Real-World Disclosure:** The authors discovered **39 previously unknown (0-day) vulnerabilities** affecting a total of 508 protected interfaces (Abstract, Section 6.2).
*   **Results:** All vulnerabilities were responsibly disclosed. **Six IoT devices** have already been assigned **CVE IDs** following confirmation from the vendors (Abstract, Section 6.2).

### 4. Quantitative Effectiveness Numbers
*   **Vulnerability Discovery:** Identified **39 distinct vulnerabilities** (Table 3).
*   **Affected Interfaces:** These 39 payloads were able to evade access control for **508 total interfaces** (Abstract).
*   **Comparison to SOTA:** In a comparative study (Table 4), ACBreaker(GPT) found 39 vulnerabilities, while the state-of-the-art tool **nomore403 found only 4**, and **Boofuzz found 0** (Section 6.3).
*   **Extraction Accuracy:** GPT-4o uniquely detected **124 valid interfaces**, whereas the open-source Qwen model detected only **1** (Section 6.3).
*   **Code Coverage:** The tool analyzed **1,274,646 lines** of heterogeneous firmware code (Abstract).

The summary of discovered vulnerabilities across the 11 devices is provided in Table 3:

Table 3 lists the 11 devices by ID, showing the number of "hints" (affected interfaces), the number of distinct vulnerabilities found, the type of evasion (Path, Parameter, or Header manipulation), and the CVE status. It highlights that Device 1 and Device 11 were particularly susceptible, with 257 and 133 affected interfaces respectively.
[REGION: page=19, bbox=327,55,528,944]

### 5. Ethical Constraints and Admitted Limitations
**Ethical Constraints (Section 7):**
*   **Responsible Disclosure:** Followed a strict disclosure process; vulnerabilities were reported to manufacturers before public discussion.
*   **Controlled Testing:** All tests were conducted on legally purchased devices within a controlled laboratory environment.
*   **Release Restrictions:** The source code will only be released after all 10 affected manufacturers have issued security patches (currently 6/10 are patched), and access will be restricted to verified academic researchers.

**Admitted Limitations (Section 7):**
*   **Protocol Scope:** The research focuses exclusively on **HTTP-based interfaces**. Other protocols like MQTT or UPnP were not evaluated.
*   **Code Slicing vs. Configuration Files:** The call-relationship-based slicing strategy has difficulty handling **configuration file information**. This can lead to incomplete parameter constraint extraction and potential **false negatives**.
*   **Language Hybridity:** While effective, the authors acknowledge that the heterogeneity of device architectures and communication protocols remains a challenge for generalizability.

***

**Full References from the paper:**
[Wan25d] Wang, E.; Xie, W.; Li, S.; Liu, R.; Zhou, Y.; Wang, Z.; Ma, S.; Yang, W.; Wang, B. Large Language Model-Powered Protected Interface Evasion: Automated Discovery of Broken Access Control Vulnerabilities in Internet of Things Devices. *Sensors* **2025**, *25*, 2913. https://doi.org/10.3390/s25092913

---

---

## Lec25 · Can LLMs Reason About Program Semantics? A Comprehensive Evaluation of LLMs on Formal Specification Inference

- **venue**: Annual Meeting of the Association for Computational Linguistics, pp. 21991-22014 ｜ **year**: 2025 ｜ **doi**: https://doi.org/10.48550/arXiv.2503.04779
- **authors**: Thanh Le-Cong, Bach Le, Toby Murray

Based on the paper "Can LLMs Reason About Program Semantics? A Comprehensive Evaluation of LLMs on Formal Specification Inference," here is the detailed report you requested.

### 1. Benchmark/Task Design and Specification Formats
The authors introduce **FormalBench**, a benchmark designed to evaluate LLM reasoning about program semantics through the task of formal specification inference.

*   **Task Design:** The task requires LLMs to annotate Java programs with formal specifications that describe their behavior. This acts as a proxy for semantic reasoning because it requires exhaustive reasoning over all possible program executions and the generation of precise, syntactically correct logic.
*   **Dataset Components:**
    *   **FormalBench-Base:** 700 manually validated Java programs with natural language descriptions (Section 3.1).
    *   **FormalBench-Diverse:** 6,219 program variants generated via 18 semantic-preserving transformations (e.g., variable renaming, loop restructuring) to test robustness (Section 3.1, Appendix A).
*   **Specification Formats:** The primary format used is **JML (Java Modeling Language)**. The paper also mentions **ACSL** as a general context for formal specifications, but the evaluation focus is on JML for Java (Section 1 and 4).

### 2. Main Quantitative Findings
The study reveals that LLMs currently possess a "limited effectiveness" in reasoning about program semantics:

*   **Low Success Rates:** Under zero-shot settings, most open-source models (except CodeQwen-2.5) have success rates below **3%**. Proprietary models like GPT-4o and Claude-3.5-Sonnet perform better but still peak at success rates of **11.2%** and **10.5%** respectively under zero-shot conditions (Section 4.1, Table 1).
*   **Failure Rates:** Failure rates are high, often exceeding **50%** across models (Section 2).
*   **Robustness Issues:** LLMs exhibit "flip rates" (where they succeed on an original program but fail on a semantically identical variant) between **27.2% and 39.2%** (Section 4.3, Table 2).

The following table provides a comparison of model performance:

> | Models | Success Rate (%) | Failure Rate (%) | Completeness (%) |
> | :--- | :---: | :---: | :---: |
> | **Open-Source LLMs** | | | |
> | CodeQwen-2.5-32B | 7.6 | 77.1 | 83.3 |
> | + LTM (Least-to-Most) | 12.0 | 68.2 | 89.1 |
> | **Proprietary LLMs** | | | |
> | DeepSeek-V3-671B | 8.4 | 65.2 | 89.6 |
> | + LTM | 16.6 | 56.8 | 89.6 |
> | GPT-4o | 11.2 | 56.4 | 80.4 |
> | + LTM | 15.0 | 57.7 | 86.4 |
> | Claude-3.5-Sonnet | 10.5 | 64.5 | 91.2 |
> | + LTM | 15.4 | 51.1 | 86.4 |
>
> [REGION: page=5, bbox=35,123,594,874]

### 3. Semantic Reasoning Failures and Systematic Error Patterns
The authors identified **32 distinct types of failures** (Section 4.4.1). LLMs specifically struggle with:

*   **Complex Control Flow:** While LLMs perform well on sequential or branched programs, they struggle significantly with **loops**. Success rates for loop-containing programs are less than **10%**, with failure rates exceeding **50%** (Section 4.1).
*   **Unsupported Inductive Quantifiers:** LLMs frequently use quantifiers like `\sum`, `\product`, or `\num_of`. These are often unsupported by deductive verifiers because they require complex inductive reasoning and auxiliary lemmas that LLMs fail to provide (Section 4.4.1, "Unsupported Inductive Quantifiers").
*   **Arithmetic Range Reasoning:** Models often fail to account for **arithmetic overflows**, leading to "ArithmeticOperationRange" failures (Section 4.4.1, page 18).
*   **Postcondition and Loop Invariant Failures:** These account for nearly **30%** of total failures. They occur when the model provides an incorrect/incomplete specification or fails to provide strong enough preconditions for the verifier to prove the logic (Section 4.4.1, page 8).
*   **Syntax Errors:** Models often violate JML or Java syntax, such as erroneously including the `assignable` keyword inside a loop invariant (Section 4.4.1, Figure 4).

The distribution of these failures across different control flow types is visualized in the radar charts:

> This figure shows that failures (red lines) are most prominent in programs involving nested, multi-path, and single-path loops compared to simpler sequential or branching structures.
> [REGION: page=16, bbox=190,132,393,485]

### 4. Verification and Feedback Mechanisms
The authors tested several prompting strategies to improve performance:

*   **Advanced Prompting:** Using **Least-to-Most (LTM)** prompting improved success rates to **16.6%** (Section 2).
*   **Self-Repair (Feedback):** The authors designed customized "self-repair" prompts that include error descriptions and guidance. This mechanism **improved success rates by 25%** (increasing from 16% to 20%) and **reduced failure rates by approximately 40%** (Section 4.4.2).
*   **Limitations of Repair:** The effectiveness of self-repair tends to saturate and converge after a few iterations (Section 2).

### 5. Admitted Limitations
The authors acknowledge several limitations to their study (Section 7):

*   **Mutation Analysis Proxy:** Their measure of "completeness" relies on mutation analysis, which can be affected by the presence of "equivalent mutants" (semantically identical code variants) that evade detection.
*   **Verification Tool Ambiguity:** The deductive verifiers returned a substantial number of **"unknown"** results. While manual inspection suggests these are often high-quality but complex specifications, they introduce ambiguity into the quantitative success metrics.
*   **Language Scope:** The study is restricted to **Java and JML**. The authors note that while their methodology could extend to C or Python, JML is particularly mature for this kind of evaluation.
*   **Model Availability:** Due to resource and policy constraints, the authors could not evaluate OpenAI’s `o1` or certain DeepSeek models fully at the time of writing.

***

**References from the paper:**

*   **[Lec25]:** Thanh Le-Cong, Bach Le, Toby Murray. 2025. Can LLMs Reason About Program Semantics? A Comprehensive Evaluation of LLMs on Formal Specification Inference. (Preprint arXiv:2503.04779v4).

---

---

## Cro23 · Data Quality for Software Vulnerability Datasets

- **venue**: 2023 IEEE/ACM 45th International Conference on Software Engineering (ICSE), pp. 121-133 ｜ **year**: 2023 ｜ **doi**: https://doi.org/10.1109/ICSE48619.2023.00022
- **authors**: Roland Croft, M. A. Babar, M. M. Kholoosi

Based on the study by Croft et al. [Cro23], here is the report on the data quality of software vulnerability datasets.

### 1. Specific Data Quality Problems Identified
The authors systematically analyzed five inherent data quality attributes across four state-of-the-art (SOTA) datasets. These attributes and their prevalence are summarized in **Table I** and **Table III**.

*   **Accuracy (Label Correctness):** Widespread inaccuracies in vulnerability labels, particularly in real-world datasets.
*   **Uniqueness (Duplication):** Massive duplication of records (17-99%), leading to data leakage and inflated performance.
*   **Consistency (Conflict):** Similar or identical code snippets having different labels (vulnerable vs. non-vulnerable).
*   **Completeness (Missing Info):** Missing source code or truncated functions.
*   **Currentness (Concept Drift):** While measured, this was the least problematic attribute, showing no significant temporal distribution issues.

This table defines the five attributes used to measure the quality of the datasets.
[REGION: page=2, bbox=83,86,183,912]

This table provides the quantitative results for each attribute across the four studied datasets, where a value of 1.0 indicates no quality issues.
[REGION: page=5, bbox=807,100,928,485]

### 2. Critique of Ground-Truth Labeling
The paper offers a severe critique of common methods for obtaining ground truth, categorizing them into four sources (**Section II-A**) and identifying specific failure modes for each:

*   **Reliance on Noisy Proxies:** Most real-world datasets (like **Big-Vul** and **Devign**) assume that any code touched by a vulnerability fix is "vulnerable." The authors found this false because fixing commits often include **irrelevant changes** (style, refactoring) or **cleanup changes** that do not represent exploitable code (**Section IV-A, Table IV**).
*   **Manual Annotation Limitations:** Even manual validation (used in **Devign**) is fallible. The authors noted that "this accuracy assurance comes at the cost of data size" and yet "Devign still exhibits some inaccuracies" (**Section IV-A, page 6**).
*   **Latent Vulnerabilities:** The "non-vulnerable" class is often defined by the absence of a reported vulnerability, which the authors call an "unreliable" source because "vulnerabilities can remain latent or undetected" (**Section II-A**). This leads to **label inconsistency** (Section IV-C).
*   **Data Leakage via Duplication:** Duplication across training and test sets allows models to "trivially classify samples" by memorization rather than learning security patterns, inflating reported performance (**Section IV-B**).

### 3. Recommended Practices for Trustworthy Ground Truth
In **Section V (Discussion)** and **Section VII (Conclusion)**, the authors suggest the following to move toward more reliable datasets:

*   **Rule-Based Syntactic Filtering:** Use filters to detect and remove duplicates, inconsistent labels, and incomplete entries.
*   **Improve Collection Heuristics:** Move beyond simple keyword matching or "commit-history" scraping. There is a need for "semantic filters or heuristics for correct vulnerability fixing lines" (**Section V**).
*   **Diverse Non-Vulnerable Sampling:** Instead of just using "any non-modified code," develop heuristics to obtain more diverse and truly representative non-vulnerable samples.
*   **Verification:** Practitioners should "be wary of reusing existing datasets without first checking the data quality" (**Section V**).

### 4. Quantitative Measurement of Label Error Rates
The authors conducted manual validation on random samples from the datasets. The label error rates (1 - Accuracy) for the vulnerable class were found to be:
*   **D2A:** 71.4% error rate (Accuracy 0.286)
*   **Big-Vul:** 45.7% error rate (Accuracy 0.543)
*   **Devign:** 20.0% error rate (Accuracy 0.800)
*   **Juliet (Synthetic):** 0% error rate (Accuracy 1.000)

Additionally, the authors categorized the *causes* of label inaccuracy in Table IV:

This table breaks down why labels were inaccurate, citing "Irrelevant" code changes, "Cleanup" changes, and "Inaccurate" fix identification.
[REGION: page=5, bbox=837,557,917,896]

### 5. Affected Datasets
The study investigated four specific datasets, each representing a different label source:
1.  **Big-Vul** (Security Vendor Provided)
2.  **Devign** (Developer Provided / Manually Validated)
3.  **D2A** (Tool Created via Static Analysis)
4.  **Juliet** (Synthetically Created)

All datasets exhibited significant quality issues, though **Juliet** (the only one "constructed by design") was the only one with 100% label accuracy, despite suffering from low uniqueness (83.7% duplication) and lower consistency (**Table III**).

### Strongest Criticism for Citing
The following quote summarizes the danger of relying on post-hoc annotation of real-world commits rather than ground truth by design:

> "Accuracy is limited for some real-world datasets due to their reliance on noisy and hard-to-identify vulnerability fixing commits. Accuracy issues cause SVP models to infer the wrong patterns between classes." (**Section IV-A, Page 6**)

***

**Reference:**
[Cro23] Roland Croft, M. Ali Babar, and M. Mehdi Kholoosi. 2023. Data Quality for Software Vulnerability Datasets. In *arXiv preprint arXiv:2301.05456*.

---

---

## Le21 · Automated reverse engineering of role-based access control policies of web applications

- **venue**: J. Syst. Softw., pp. 111109 ｜ **year**: 2021 ｜ **doi**: https://doi.org/10.1016/j.jss.2021.111109
- **authors**: H. Le, Lwin Khin Shar, D. Bianculli, L. Briand, Duy Cu Nguyen

Based on the paper [Le21], here is the precise report on the requested details:

### 1. Artifacts Analyzed
The **ReACP** framework employs a **black-box approach**, meaning it does not require access to the application's source code. It analyzes the following artifacts:
*   **Access Logs:** These are recording of HTTP request and response messages generated during the exploration of the application (Section 4.1, Page 6).
*   **HTTP Message Components:** Within the logs, it specifically mines:
    *   **URLs** (including protocol, host, port, path, and query strings).
    *   **Parameter names and values** from URL query strings, POST request bodies, and Web forms.
    *   **Headers** (specifically server-generated cookies) (Section 4.2, Page 7).
*   **User Credentials and Entry URLs:** Provided as initial inputs to the framework to facilitate crawling (Section 3, Page 5).

### 2. Inference Algorithm and Granularity
*   **Algorithm:** ReACP uses **Decision Tree learning** (specifically the **C4.5 classifier**, implemented as **J48** in the Weka toolset). The tree is trained on labeled access logs to produce IF-THEN rules that represent the access control policies (Section 4.5.2, Page 12; Section 4.7, Page 14).
*   **Granularity:** The framework recovers policies at the **role level**, rather than the individual user level (Section 6, Page 26). It also aims for a **high level of abstraction** by using "meta-attributes" (like `isOwned`) to capture relationships between factors influencing access, rather than just raw parameter values (Section 2, Page 2; Section 4.5.1, Page 11).

### 3. Accuracy of Inferred Policy
The paper reports that when using application-specific labeling rules, the framework achieved an average accuracy of **97.8%**.
*   The correctness was verified by checking the inferred policies against the actual implementation (the "Gold Standard").
*   The performance varied slightly by application: iTrust (99.3%), TaskFreak (99.7%), WordPress (72.3%), and SECP (98.6%) (Table 9, Page 19).

The following table details the correctness results for the four applications evaluated:

**Table 9: Number of correct policies inferred using generic and app-specific labeling rules**
| Application | Resources | Inferred Policies | Correct Policies | %Correct (App-specific) |
| :--- | :--- | :--- | :--- | :--- |
| iTrust | 162 | 693 | 688 | 99.3 |
| TaskFreak | 21 | 1547 | 1544 | 99.7 |
| WordPress | 28 | 278 | 201 | 72.3 |
| SECP | 61 | 4113 | 4054 | 98.6 |
| **Total** | **272** | **6631** | **6487** | **97.8** |
[REGION: page=19, bbox=146,145,297,853]

### 4. Human Confirmation and Input
The framework is described as **semi-automated**, requiring human intervention in several stages:
*   **Input Specification:** While the framework mines specifications, a human ("domain expert") may need to **manually refine** the Xinput files to exclude invalid/irrelevant inputs or define specific data types and boundaries (Section 4.2, Page 8; Section 5.5, Page 23).
*   **Labeling Rules:** Users often need to **define or refine application-specific labeling rules** to correctly categorize HTTP responses as "allowed" or "denied," especially when applications return "200 OK" for denied requests (Section 4.4, Page 10; Section 5.5, Page 23).
*   **Policy Validation:** The final inferred policies are presented to a **security engineer** for manual validation against intended access rights to detect vulnerabilities or implementation errors (Abstract, Page 1; Section 5.5, Page 23).

### 5. Limitations
The authors admit several limitations regarding the recovery of policies:
*   **Internal Logic:** Because it is a black-box approach, it "may not discover access control policies implemented through **sophisticated business logic in the code**," which can only be identified via static analysis (Section 5.5, Page 23).
*   **Model Scope:** The approach is strictly limited to the **RBAC model** and does not currently generalize to other models like Attribute-Based Access Control (ABAC) or Task-Based Access Control (Section 5.6, Page 24).
*   **State Dependency:** Incomplete or incorrect system state initialization during testing (e.g., failing to set up specific document ownership) can lead to incorrectly inferred policies (Section 5.3, Page 19).
*   **Observation Bias:** The framework can only infer policies for resources and behaviors that it can **observe through HTTP requests and responses**; if a crawler or manual browser cannot reach a specific state, the corresponding policy cannot be recovered (Section 4.2, Page 7).

***

**References from the paper:**
*   [7] R. S. Sandhu, E. J. Coyne, H. L. Feinstein, C. E. Youman, Role-based access control models, IEEE Computer 29 (1996) 38–47.
*   [9] H. T. Le, C. D. Nguyen, L. C. Briand, B. Hourte, Automated inference of access control policies for web applications, in: Proceedings of the 20th ACM Symposium on Access control Models and Technologies (SACMAT’15), ACM, 2015.
*   [15] J. R. Quinlan, C4.5: Programs for Machine Learning, volume 1, Morgan Kaufmann Publisher, 1993.
*   [27] M. Hall, E. Frank, G. Holmes, B. Pfahringer, P. Reutemann, I. H. Witten, The weka data mining software: An update, ACM SIGKDD Explorations Newsletter 11 (2009) 10–18.

---

---

## Zha24b · Extracting Database Access-control Policies From Web Applications

- **venue**: ArXiv ｜ **year**: 2024 ｜ **doi**: https://doi.org/10.48550/arXiv.2411.11380
- **authors**: Wen Zhang, Dev Bali, Jamison Kerney, Aurojit Panda, S. Shenker

Based on the paper, here is the detailed report on **Ote**, the policy-extraction tool:

### 1. Extracted Content and Artifacts
Ote extracts **access-control policies** in the form of **SQL view definitions** from the source code of **legacy Ruby on Rails web applications** (Abstract, §1, §2.2). 

It specifically extracts:
*   **SQL queries (SELECTs):** The data the application attempts to access.
*   **Conditions:** The program logic (branch conditions) and database states that trigger those queries (Abstract, §4).
*   **Artifacts analyzed:** Ruby on Rails application code (controller actions, view templates, helpers), the database schema, and database constraints (§3.1, §4.1).

### 2. The Algorithm and Handling of Spread Policies
The extraction process follows a multi-step workflow designed to unify logic spread across application code and database schemas (Figure 1, §3.1):

*   **Concolic Execution (§4):** Ote explores execution paths through application handlers. It uses a modified JRuby interpreter to track symbolic variables and record **transcripts** of branches taken and SQL queries issued.
*   **Handling Code-embedded Logic (§4.1):** It focuses on the "query-issuing core"—the program components that determine query parameters or whether a query is issued. To handle path explosion in complex code, it uses an **LLM-based relevance judge** (§4.6) to identify and prune branches unrelated to data access (e.g., HTML formatting).
*   **Handling Database Schema/Constraints (§3.1, §5.2):** Ote incorporates database constraints (e.g., uniqueness, foreign key invariants) provided by the user or auto-generated from the schema (§6). These constraints are used to:
    1.  Keep symbolic exploration within valid database states.
    2.  Simplify policies by removing redundant conditions (e.g., a lookup guaranteed to succeed by a foreign key).
*   **Simplification and Merging (§5.1–§5.3):** Transcripts are converted into **conditioned queries**. Ote uses **Algorithm 1** to simplify these by merging branches and removing "vacuous" records. Finally, **Algorithm 2** "conjoins" these conditions into a final set of SQL views representing the policy.

### 3. Evaluation Targets and Accuracy
The authors evaluated Ote on three real-world Ruby on Rails applications (§7):
1.  **diaspora:** A social network with >850k users.
2.  **Autolab:** A course management platform used at >20 schools.
3.  **The Odin Project:** A web development education site.

**Accuracy and Findings (§7.6):**
*   **Discovery of Errors:** Ote identified several errors in previously **handwritten policies**, including overly permissive views that leaked sensitive data.
*   **Code Bug Discovery:** In *Autolab*, Ote revealed a "subtle bug" where a misconfigured external library inadvertently disabled an intended access check (the `exam?` check).
*   **Tightness:** Extracted policies were generally more "tight" (restrictive and precise) than handwritten ones, which often omit non-privacy-critical conditions for simplicity (Table 4).

### 4. Machine-Checkability
**Yes, the extracted policy is machine-checkable.** The paper states that once the policy is extracted and reviewed, it can be "enforced using an enforcer [56, 58, 107] to ensure continued compliance" (§1). Specifically, Ote uses an existing enforcement tool called **Blockaid** (§5.4, §107) to check for information containment and to prune redundant views during the extraction process.

### 5. Admitted Limitations
The authors acknowledge several limitations regarding what Ote can analyze and express:

*   **Inexpressible Policies (§3.2, §4.7):**
    *   **Negations:** Ote’s policy language (Project-Select-Join views) cannot express negations (e.g., "Allow Q1 only if Q2 returns no rows").
    *   **Complex Queries:** It approximates complex SQL features like general joins or aggregations using simpler PSJ constructs (§7.3).
*   **The "Simple Core" Assumption (§4.1, §4.7):** Ote assumes the logic governing query issuance relies on simple operations. It may produce incorrect (too broad or too tight) policies if query issuance depends on uninstrumented complex operations like **regex-matching** or complex **string formatting**.
*   **Non-Guarantees (§3.2):** Because concolic execution is bounded and the LLM judge may make mistakes, Ote does not guarantee **completeness** (covering all possible queries) or **tightness** (the most restrictive possible policy).
*   **Manual Effort (§7.8):** It requires users to provide some manual database constraints and relevance hints to compensate for the LLM's reasoning limitations.

The following figure illustrates the workflow and where these components (like the LLM judge and database constraints) fit in:
[REGION: page=4, bbox=108,124,248,875]

Table 4 shows the difference in view counts, highlighting that extracted policies are often more detailed than handwritten ones.
[REGION: page=12, bbox=144,539,219,873]

***

**Reference:**
[107] Wen Zhang, Eric Sheng, Michael Alan Chang, Aurojit Panda, Mooly Sagiv, and Scott Shenker. Blockaid: Data access policy enforcement for web applications. In Marcos K. Aguilera and Hakim Weatherspoon, editors, 16th USENIX Symposium on Operating Systems Design and Implementation, OSDI 2022, Carlsbad, CA, USA, July 11-13, 2022, pages 701–718. USENIX Association, 2022.

---

---

## Li26g · Detecting Privilege Escalation in Polyglot Microservices via Agentic Program Analysis

- **venue**: 2026 IEEE Symposium on Security and Privacy (SP), pp. 1747-1765 ｜ **year**: 2026 ｜ **doi**: https://doi.org/10.1109/SP63933.2026.00121
- **authors**: Penghui Li, H. Chong, Yinzhi Cao, Junfeng Yang

Based on the paper "Detecting Privilege Escalation in Polyglot Microservices via Agentic Program Analysis" [Li26g], here is the report on the requested details:

### 1. Structure of Agentic Program Analysis
NEO’s framework is structured as an iterative loop where an **LLM-based agent** orchestrates **deterministic code search primitives** and **symbolic solvers**.

*   **LLM-Driven Components:**
    *   **Orchestration & Planning:** The agent (e.g., Claude 3.7 Sonnet) dynamically generates analysis plans and adapts search strategies based on intermediate results (§4.1, §5).
    *   **Privileged Operation Identification:** The LLM interprets semantic cues (function names, comments, documentation) to identify security-critical operations (§4.2).
    *   **Security Check Validation:** The LLM performs "Sufficiency Assessment" to determine if a located check (e.g., `can_switch_roles`) adequately protects a specific privileged operation (§4.4).
    *   **Constraint Extraction:** The LLM extracts path constraints from code and translates them into SMT-LIB format for the solver (§5).
*   **Symbolic/Deterministic Components:**
    *   **Code Search Engine:** A set of deterministic primitives ($Q_{name}$, $Q_{ast}$, $Q_{flow}$, $Q_{cg}$) built on **CodeQL** to perform scalable name-based lookups, AST analysis, data-flow tracking, and call-graph traversal (§4.1.1).
    *   **Path Constraint Validation:** A deterministic **Z3 solver** is used to check the satisfiability of the predicates generated by the LLM to prune infeasible paths (§4.4, §5).

The workflow is illustrated in Figure 3, showing the interaction between the LLM agent and the search engine.
[REGION: page=4, bbox=87,143,260,847]

### 2. Cross-Cutting Multiple Languages
NEO addresses the "polyglot nature" of microservices through two mechanisms:
*   **Unified Code Search API:** NEO abstracts language-specific CodeQL predicates into a unified, language-agnostic interface. This allows the LLM to issue queries like `Qflow(service, from, to)` without needing to know if the underlying service is written in Java, Python, or Go (§4.1.1, §5).
*   **Inter-service Communication Query ($Q_{inter}$):** This specific primitive identifies points where services communicate (e.g., HTTP, gRPC). It uses a "channel identifier" (like a URL or topic name) to associate a caller in one language with a callee in another, effectively "stitching together" data flows across service boundaries (§4.3, §5).

This process is formalized in Algorithm 1, which tracks flows from user inputs through intermediate boundary-crossing calls to final privileged operations.
[REGION: page=7, bbox=89,520,361,908]

### 3. Detection Oracle and False Positive Suppression
*   **Detection Oracle:** The primary oracle is the LLM-based **Sufficiency Assessment**. After identifying a flow from a user input to a privileged operation, the agent locates security checks (authN/authZ) and asks the LLM to classify them and verify if the protection matches the operation's requirements (e.g., checking role eligibility vs. simple authentication) (§4.4).
*   **False Positive Suppression:**
    *   **Path Constraint Validation:** NEO uses the LLM to collect conditional guards along a flow and the **Z3 solver** to filter out flows with unsatisfiable (infeasible) constraints (§4.4).
    *   **Iterative Context Retrieval:** Instead of analyzing files as unstructured text, the agent use "property functions" like `getSource()` and `getLocation()` to retrieve only relevant code snippets, providing the LLM with enough semantic context to avoid misidentifying benign code as vulnerable (§4.1.2, §4.4).
    *   **LLM-based authN/authZ Validation:** The LLM filters out cases where proper authorization is present but implemented in ways traditional tools might miss (e.g., custom decorators) (§6.3.3).

### 4. Evaluation Targets and Quantitative Results
*   **Targets:** NEO was evaluated on **25 open-source microservice applications** spanning **7 programming languages** (Java, Python, JS, Go, C#, C, C++) and comprising **6.2 million lines of code** (§1, §6.1). The dataset included a "ground-truth" set of 4 applications with 20 known vulnerabilities.
*   **Quantitative Results:**
    *   **Vulnerability Discovery:** Uncovered **24 zero-day** privilege escalation vulnerabilities in the evaluation corpus (§1, §6.2).
    *   **Accuracy (Ground Truth):** Achieved **81.0% precision** and **85.0% recall** (§1, Table 4).
    *   **Efficiency:** Averaged **1.6 hours** and **$18 USD** in API costs per application (§6.5).
    *   **Comparison:** Outperformed the **EnIGMA** agent (which found 24 fewer vulnerabilities) and the **MScan** static analysis tool (§1, §6.4).

Table 4 summarizes the detection results across the datasets.
[REGION: page=10, bbox=85,91,215,487]

### 5. Admitted Limitations
The authors acknowledge several limitations (§7):
*   **CodeQL Dependencies:** NEO inherits limitations from CodeQL regarding the precision of call-target resolution for dynamic language features (reflection, dynamic dispatch) and pointer aliases (§4.1.1, §7).
*   **Configuration Files:** The analysis focuses on source code; it cannot directly perform structured semantic analysis on configuration files (e.g., YAML, XML) and relies on the LLM to interpret them as unstructured context (§7).
*   **Deployment Environment:** Vulnerabilities stemming from specific real-world deployment misconfigurations (e.g., cloud environment settings) are out of scope (§7).
*   **Framework-Specific Semantics:** NEO can fail when specific web frameworks have unique URL parsing behaviors (e.g., Spring’s matrix variables) that the analysis does not explicitly model, as seen in its failure to detect CVE-2023-38493 (§6.2, §6.4.2).
*   **LLM Sensitivity:** Performance is highly sensitive to the chosen LLM model and the design of the prompts (§A.4).

***

**References**

[Li26g] Penghui Li, Hong Yau Chong, Yinzhi Cao, and Junfeng Yang. 2026. Detecting Privilege Escalation in Polyglot Microservices via Agentic Program Analysis. In Proceedings of the 2026 IEEE Symposium on Security and Privacy (S&P).

[8] Gz-yami, “Mall4Cloud: A microservices-based e-commerce platform,” 2025, accessed: October 2025. [Online]. Available: https://github.com/gz-yami/mall4cloud

[20] F. Liu, Y. Zhang, T. Chen, Y. Shi, G. Yang, Z. Lin, M. Yang, J. He, and Q. Li, “Detecting taint-style vulnerabilities in microservice-structured web applications,” in 2025 IEEE Symposium on Security and Privacy (SP). IEEE, 2025, pp. 972–990.

[23] GitHub, Inc., “CodeQL: Discover vulnerabilities across a codebase with queries,” 2025, accessed: October 2025. [Online]. Available: https://codeql.github.com/

[26] T. Abramovich, M. Udeshi, M. Shao, K. Lieret, H. Xi, K. Milner, S. Jancheska, J. Yang, C. E. Jimenez, F. Khorrami, P. Krishnamurthy, B. Dolan-Gavitt, M. Shafique, K. R. Narasimhan, R. Karri, and O. Press, “EnIGMA: Interactive tools substantially assist LM agents in finding security vulnerabilities,” in Forty-second International Conference on Machine Learning, 2025. [Online]. Available: https://openreview.net/forum?id=Of3wZhVv1R

---

---

## Zuo17

> PDF 无法下载，未能全文精读。❌ Error: Could not get PDF for [Zuo17]. The PDF may not be available for download.  Region format: page is 1-indexed; bbox=top,left,bottom,right, normalized 0-1000 from top-left.
