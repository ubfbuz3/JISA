# Zotero 集合快照：WebAPI安全与漏洞挖掘_JISA_2026

来源：本地 Zotero 集合 `4VUU5LNB`。元数据来自 OpenAlex（真实索引，摘要经 Crossref/出版社页补齐）
与 Undermind 深度检索（`mcp.undermind.ai`）。共 39 篇。

## [1] Rethinking Broken Object Level Authorization Attacks Under Zero Trust Principle

- **cite_key**: `-`
- **year**: 2026 | **venue**: ACM Transactions on Software Engineering and Methodology
- **authors**: Anbin Wu, Zhiyong Feng, Ruitao Feng, Zhenchang Xing, Yang Liu
- **doi**: https://doi.org/10.1145/3833417
- **cited-by**: 0 | **source**: OpenAlex | **tag**: API-越权
- **pdf**: -

> RESTful APIs facilitate data exchange between applications, but they also expose sensitive resources to potential exploitation. Broken Object Level Authorization (BOLA) is the top vulnerability in the OWASP API Security Top 10, exemplifies a critical access control flaw where attackers manipulate API parameters to gain unauthorized access. To address this, we propose BolaZ , a defense framework grounded in zero trust principles. BolaZ analyzes the data flow of resource IDs, pinpointing BOLA attack injection points and determining the associated authorization intervals to prevent horizontal privilege escalation. Our approach leverages static taint tracking to categorize APIs into producers and consumers based on how they handle resource IDs. By mapping the propagation paths of resource IDs, BolaZ captures the context in which these IDs are produced and consumed, allowing for precise identification of authorization boundaries. Unlike defense methods based on common authorization models, BolaZ is the first authorization-guided method that adapts defense rules based on the system's best-practice authorization logic. We validate BolaZ through empirical research on 10 GitHub projects. The results demonstrate BolaZ 's effectiveness in defending against vulnerabilities collected from CVE and discovering 35 new BOLA vulnerabilities in the wild, demonstrating its practicality in real-world deployments.

## [2] Automated broken object-level authorization attack detection in REST APIs through OpenAPI to colored petri nets transformation

- **cite_key**: `-`
- **year**: 2025 | **venue**: International Journal of Information Security
- **authors**: Ailton Santos Filho, Ricardo J. Rodríguez, Eduardo Feitosa
- **doi**: https://doi.org/10.1007/s10207-024-00970-5
- **cited-by**: 6 | **source**: OpenAlex | **tag**: API-越权
- **pdf**: -

> Abstract The representational state transfer architectural style (REST) specifies a set of rules for creating web services. In REST, data and functionality are considered resources, accessed, and manipulated using a uniform, well-defined set of rules. RESTful web services are web services that follow the REST architectural style and are exposed to the Internet using RESTful APIs. Most of them are described by OpenAPI, a standard language-independent interface for RESTful APIs. RESTful APIs are continuously available on the Internet and are therefore a common target for cyberattacks. To prevent vulnerabilities and reduce risks in web systems, there are several security guidelines available, such as those provided by the Open Web Application Security Project (OWASP) foundation. A common vulnerability in web services is broken object level authorization (BOLA), which allows an attacker to modify or delete data or perform actions intended only for authorized users. For example, an attacker can change an order status, delete a user account, or add unauthorized data to the server. In this paper, we propose a transformation from OpenAPI to Petri nets, which enables formal modeling and analysis of REST APIs using existing Petri net analysis techniques to detect potential security risks directly from the analysis of web server logs. In addition, we also provide a tool, named , which automatically performs model transformation (taking the OpenAPI specification as input) and BOLA attack detection by analyzing web server execution traces. We apply it to a case study of a vulnerable web application to demonstrate its applicability. Our results show that it is capable of detecting BOLA attacks with an accuracy greater than 95% in the proposed scenarios.

## [3] Enhancing REST API fuzzing with access policy violation checks and injection attacks

- **cite_key**: `-`
- **year**: 2026 | **venue**: Journal of Systems and Software
- **authors**: Ömür Şahin, Man Zhang, Andrea Arcuri
- **doi**: https://doi.org/10.1016/j.jss.2026.113060
- **cited-by**: 0 | **source**: OpenAlex | **tag**: API-模糊测试
- **pdf**: -

> Due to their widespread use in industry, several techniques have been proposed in the literature to fuzz REST APIs. Existing fuzzers for REST APIs have been focusing on detecting crashes (e.g., 500 HTTP server error status code). However, security vulnerabilities can have major drastic consequences on existing cloud infrastructures. In this paper, we propose a series of novel automated oracles aimed at detecting violations of access policies in REST APIs, as well as executing traditional attacks such as SQL Injection and XSS. These novel automated oracles can be integrated into existing fuzzers, in which, once the fuzzing session is completed, a “security testing” phase is executed to verify these oracles. When a security fault is detected, as output our technique is able to general executable test cases in different formats, like Java, Kotlin, Python and JavaScript test suites. Our novel techniques are integrated as an extension of EvoMaster , a state-of-the-art open-source fuzzer for REST APIs. Experiments are carried out on 9 artificial examples, 8 vulnerable-by-design REST APIs with black-box testing, and 36 REST APIs from the WFD corpus with white-box testing, for a total of 52 distinct APIs. Results show that our novel oracles and their automated integration in a fuzzing process can lead to detect security issues in several of these APIs.

## [4] Advanced White-Box Heuristics for Search-Based Fuzzing of REST APIs

- **cite_key**: `-`
- **year**: 2024 | **venue**: ACM Transactions on Software Engineering and Methodology
- **authors**: Andrea Arcuri, Man Zhang, Juan Pablo Galeotti
- **doi**: https://doi.org/10.1145/3652157
- **cited-by**: 17 | **source**: OpenAlex | **tag**: API-模糊测试
- **pdf**: -

> Due to its importance and widespread use in industry, automated testing of REST APIs has attracted major interest from the research community in the last few years. However, most of the work in the literature has been focused on black-box fuzzing. Although existing fuzzers have been used to automatically find many faults in existing APIs, there are still several open research challenges that hinder the achievement of better results (e.g., in terms of code coverage and fault finding). For example, under-specified schemas are a major issue for black-box fuzzers. Currently, EvoMaster is the only existing tool that supports white-box fuzzing of REST APIs. In this paper, we provide a series of novel white-box heuristics, including for example how to deal with under-specified constrains in API schemas, as well as under-specified schemas in SQL databases. Our novel techniques are implemented as an extension to our open-source, search-based fuzzer EvoMaster . An empirical study on 14 APIs from the EMB corpus, plus one industrial API, shows clear improvements of the results in some of these APIs.

## [5] Handling Web Service Interactions in Fuzzing with Search-Based Mock-Generation

- **cite_key**: `-`
- **year**: 2025 | **venue**: ACM Transactions on Software Engineering and Methodology
- **authors**: Susruthan Seran, Man Zhang, Onur Duman, Andrea Arcuri
- **doi**: https://doi.org/10.1145/3731558
- **cited-by**: 2 | **source**: OpenAlex | **tag**: API-模糊测试
- **pdf**: -

> Testing large and complex enterprise software systems can be a challenging task. This is especially the case when the functionality of the system depends on interactions with other external services over a network (e.g., external web services accessed through REST API calls). Although several techniques in the research literature have been shown to be effective at generating test cases in a good number of different software testing contexts, dealing with external services is still a major research challenge. In industry, a common approach is to mock external web services for testing purposes. However, generating and configuring mock web services can be a very time-consuming task, e.g., external services may not be under the control of the same developers of the tested application, making it challenging to identify the external services and simulate various possible responses. In this article, we present a novel search-based approach aimed at fully automated mocking of external web services as part of white-box, search-based fuzzing. We rely on code instrumentation to detect all interactions with external services, and how their response data is parsed. We then use such information to enhance a search-based approach for fuzzing. The tested application is automatically modified (by manipulating DNS lookups) to rather interact with instances of mock web servers. The search process not only generates inputs to the tested applications but also automatically configures responses in those mock web server instances, aiming at maximizing code coverage and fault-finding. An empirical study on four open source REST APIs from EMB, and one industrial API from an industry partner, shows the effectiveness of our novel techniques (i.e., in terms of line coverage and fault detection).

## [6] GRACE: Empowering LLM-based software vulnerability detection with graph structure and in-context learning

- **cite_key**: `-`
- **year**: 2024 | **venue**: Journal of Systems and Software
- **authors**: Guilong Lu, Xiaolin Ju, Xiang Chen, Wenlong Pei, Zhilong Cai
- **doi**: https://doi.org/10.1016/j.jss.2024.112031
- **cited-by**: 171 | **source**: OpenAlex | **tag**: LLM-检测
- **pdf**: -

> Software vulnerabilities inflict considerable economic and societal harm. Therefore, timely and accurate detection of these flaws has become vital. Large language models (LLMs) have emerged as a promising tool for vulnerability detection in recent studies. However, their effectiveness suffers when limited to plain text source code, which may ignore the syntactic and semantic information of the code. To address this limitation, we propose a novel vulnerability detection approach GRACE that empowers LLM-based software vulnerability detection by incorporating graph structural information in the code and in-context learning. We also design an effective demonstration retrieval approach that identifies highly relevant code examples by considering semantic, lexical, and syntactic similarities for the target code to provide better demonstrations for in-context learning. To evaluate the effectiveness of GRACE, we conducted an empirical study on three vulnerability detection datasets (i.e., Devign, Reveal, and Big-Vul). The results demonstrate that GRACE outperforms six state-of-the-art vulnerability detection baselines by at least 28.65% in terms of the F1 score across these three datasets. Keywords: Graph structure; In-context learning; Large language model; Source code representation; Vulnerability detection. [来源：ScienceDirect/ACM 官方摘要页]

## [7] DLAP: A Deep Learning Augmented Large Language Model Prompting framework for software vulnerability detection

- **cite_key**: `-`
- **year**: 2024 | **venue**: Journal of Systems and Software
- **authors**: Yanjing Yang, Xin Zhou, Runfeng Mao, Jinwei Xu, Lanxin Yang, Yu Zhang, Haifeng Shen, He Zhang
- **doi**: https://doi.org/10.1016/j.jss.2024.112234
- **cited-by**: 38 | **source**: OpenAlex | **tag**: LLM-检测
- **pdf**: -

> Software vulnerability detection is generally supported by automated static analysis tools, which have recently been reinforced by deep learning (DL) models. However, despite the superior performance of DL-based approaches over rule-based ones in research, applying DL approaches to software vulnerability detection in practice remains a challenge. This is due to the complex structure of source code, the black-box nature of DL, and the extensive domain knowledge required to understand and validate the black-box results for addressing tasks after detection. Conventional DL models are trained by specific projects and, hence, excel in identifying vulnerabilities in these projects but not in others. These models with poor performance in vulnerability detection would impact the downstream tasks such as location and repair. More importantly, these models do not provide explanations for developers to comprehend detection results. In contrast, Large Language Models (LLMs) with prompting techniques achieve stable performance across projects and provide explanations for results. However, using existing prompting techniques, the detection performance of LLMs is relatively low and cannot be used for real-world vulnerability detections. This paper contributes DLAP, a Deep Learning Augmented LLMs Prompting framework that combines the best of both DL models and LLMs to achieve exceptional vulnerability detection performance. Experimental evaluation results confirm that DLAP outperforms state-of-the-art prompting frameworks, including role-based prompts, auxiliary information prompts, chain-of-thought prompts, and in-context learning prompts, as well as fine-tuning, on multiple metrics. [来源：ScienceDirect/arXiv:2405.01202]

## [8] SecureQwen: Leveraging LLMs for vulnerability detection in python codebases

- **cite_key**: `-`
- **year**: 2024 | **venue**: Computers & Security
- **authors**: Abdechakour Mechri, Mohamed Amine Ferrag, Mérouane Debbah
- **doi**: https://doi.org/10.1016/j.cose.2024.104151
- **cited-by**: 27 | **source**: OpenAlex | **tag**: LLM-检测
- **pdf**: -

> Identifying vulnerabilities in software code is crucial for ensuring the security of modern systems. However, manual detection requires expert knowledge and is time-consuming, underscoring the need for automated techniques. In this paper, we present SecureQwen, a novel vulnerability detection tool leveraging large language models (LLMs) with a context length of 64K tokens to identify potential security threats in large-scale Python codebases. Utilizing a decoder-only transformer architecture, SecureQwen captures complex relationships between code tokens, enabling accurate classification of vulnerable code sequences across 14 common weakness enumerations (CWEs), including OS Command Injection, SQL Injection, Improper Check or Handling of Exceptional Conditions, Path Traversal, Broken or Risky Cryptographic Algorithm, Deserialization of Untrusted Data, and Cleartext Transmission of Sensitive Information. We evaluate SecureQwen on a large Python dataset with over 1.875 million function-level code snippets from different sources, including GitHub repositories, Codeparrot's dataset, and synthetic data generated by GPT-4o. The experimental evaluation demonstrates high accuracy, with F1 scores ranging from 84% to 99%. [来源：ScienceDirect 官方摘要页]

## [9] Towards Explainable Vulnerability Detection With Large Language Models

- **cite_key**: `-`
- **year**: 2025 | **venue**: IEEE Transactions on Software Engineering
- **authors**: Qiheng Mao, Zhenhao Li, Xing Hu, Kui Liu, Xin Xia, Jianling Sun
- **doi**: https://doi.org/10.1109/tse.2025.3605442
- **cited-by**: 17 | **source**: OpenAlex | **tag**: LLM-检测
- **pdf**: -

> Software vulnerabilities pose significant risks to the security and integrity of software systems. Although prior studies have explored vulnerability detection using deep learning and pre-trained models, these approaches often fail to provide the detailed explanations necessary for developers to understand and remediate vulnerabilities effectively. The advent of large language models (LLMs) has introduced transformative potential due to their advanced generative capabilities and ability to comprehend complex contexts, offering new possibilities for addressing these challenges. In this paper, we propose LLMVulExp, an automated framework designed to specialize LLMs for the dual tasks of vulnerability detection and explanation. To address the challenges of acquiring high-quality annotated data and injecting domain-specific knowledge, LLMVulExp leverages prompt-based techniques for annotating vulnerability explanations and fine-tunes LLMs using instruction tuning with Low-Rank Adaptation (LoRA), enabling LLMVulExp to detect vulnerability types in code while generating detailed explanations, including the cause, location, and repair suggestions. Additionally, we employ a Chain-of-Thought (CoT) based key code extraction strategy to focus LLMs on analyzing vulnerability-prone code, further enhancing detection accuracy and explanatory depth.We conducted experiments across multiple vulnerability detection settings on three benchmark datasets, demonstrating the effectiveness of our method. This study highlights the feasibility of utilizing LLMs for real-world vulnerability detection and explanation tasks, providing critical insights into their adaptation and application in software security.

## [10] Multitask-Based Evaluation of Open-Source LLM on Software Vulnerability

- **cite_key**: `-`
- **year**: 2024 | **venue**: IEEE Transactions on Software Engineering
- **authors**: Xin Yin, Chao Ni, Shaohua Wang
- **doi**: https://doi.org/10.1109/tse.2024.3470333
- **cited-by**: 68 | **source**: OpenAlex | **tag**: LLM-评测
- **pdf**: -

> This paper proposes a pipeline for quantitatively evaluating interactive Large Language Models (LLMs) using publicly available datasets. We carry out an extensive technical evaluation of LLMs using Big-Vul covering four different common software vulnerability tasks. This evaluation assesses the multi-tasking capabilities of LLMs based on this dataset. We find that the existing state-of-the-art approaches and pre-trained Language Models (LMs) are generally superior to LLMs in software vulnerability detection. However, in software vulnerability assessment and location, certain LLMs (e.g., CodeLlama and WizardCoder) have demonstrated superior performance compared to pre-trained LMs, and providing more contextual information can enhance the vulnerability assessment capabilities of LLMs. Moreover, LLMs exhibit strong vulnerability description capabilities, but their tendency to produce excessive output significantly weakens their performance compared to pre-trained LMs. Overall, though LLMs perform well in some aspects, they still need improvement in understanding the subtle differences in code vulnerabilities and the ability to describe vulnerabilities to fully realize their potential. Our evaluation pipeline provides valuable insights into the capabilities of LLMs in handling software vulnerabilities.

## [11] Defendroid: Real-time Android code vulnerability detection via blockchain federated neural network with XAI

- **cite_key**: `-`
- **year**: 2024 | **venue**: Journal of Information Security and Applications
- **authors**: Janaka Senanayake, Harsha Kalutarage, Andrei Petrovski, Luca Piras, M. Omar Al-Kadri
- **doi**: https://doi.org/10.1016/j.jisa.2024.103741
- **cited-by**: 22 | **source**: OpenAlex | **tag**: JISA-本体
- **pdf**: -

> Ensuring strict adherence to security during the phases of Android app development is essential, primarily due to the prevalent issue of apps being released without adequate security measures in place. While a few automated tools are employed to reduce potential vulnerabilities during development, their effectiveness in detecting vulnerabilities may fall short. To address this, “Defendroid”, a blockchain-based federated neural network enhanced with Explainable Artificial Intelligence (XAI) is introduced in this work. Trained on the LVDAndro dataset, the vanilla neural network model achieves a 96% accuracy and 0.96 F1-Score in binary classification for vulnerability detection. Additionally, in multi-class classification, the model accurately identifies Common Weakness Enumeration (CWE) categories with a 93% accuracy and 0.91 F1-Score. In a move to foster collaboration and model improvement, the model has been deployed within a blockchain-based federated environment. This environment enables community-driven collaborative training and enhancements in partnership with other clients. The extended model demonstrates improved accuracy of 96% and F1-Score of 0.96 in both binary and multi-class classifications. The use of XAI plays a pivotal role in presenting vulnerability detection results to developers, offering prediction probabilities for each word within the code. This model has been integrated into an Application Programming Interface (API) as the backend and further incorporated into Android Studio as a plugin, facilitating real-time vulnerability detection. Notably, Defendroid exhibits high efficiency, delivering prediction probabilities for a single code line in an average processing time of a mere 300 ms. The weight-sharing transparency in the blockchain-driven federated model enhances trust and traceability, fostering community engagement while preserving source code privacy and contributing to accuracy improvement.

## [12] Enhancing vulnerability detection efficiency: An exploration of light-weight LLMs with hybrid code features

- **cite_key**: `-`
- **year**: 2024 | **venue**: Journal of Information Security and Applications
- **authors**: Jianing Liu, Guanjun Lin, Huan Mei, Fan Yang, Yonghang Tai
- **doi**: https://doi.org/10.1016/j.jisa.2024.103925
- **cited-by**: 10 | **source**: OpenAlex | **tag**: JISA-本体
- **pdf**: -

> Vulnerability detection is a critical research topic. However, the performance of existing neural network-based approaches requires further improvement. The emergence of large language models (LLMs) has demonstrated their superior performance in natural language processing (NLP) compared to conventional neural architectures, motivating researchers to apply LLMs for vulnerability detection. This paper focuses on evaluating the performance of various Transformer-based LLMs for source-code-level vulnerability detection. We propose a framework named VulACLLM (AST & CFG-based LLMs Vulnerability Detection), which leverages combined feature sets derived from Abstract Syntax Tree (AST) and Control Flow Graph (CFG). The recall rate of VulACLLM in the field of vulnerability detection reached 0.73, while the F1-score achieved 0.725. Experimental results show that the proposed feature sets significantly enhance detection performance. To further improve the efficiency of LLM-based detection, we examine the performance of LLMs compressed using two techniques: Knowledge Distillation (KD) and Low-Rank Adaptation (LoRA). To assess the performance of these compressed models, we introduce efficiency metrics that quantify both performance loss and efficiency gains achieved through compression. Our findings reveal that, compared to KD, LLMs compressed with LoRA achieve higher recall, achieving a maximum recall rate of 0.82, while substantially reducing training time, taking only 20 min to complete one epoch, and disk size, requiring only 4.89 MB of memory. [来源：ScienceDirect 官方摘要页]

## [13] HyVulDect: A hybrid semantic vulnerability mining system based on graph neural network

- **cite_key**: `-`
- **year**: 2022 | **venue**: Computers & Security
- **authors**: Wenbo Guo, Yong Fang, Cheng Huang, Haoran Ou, Chun Lin, Yongyan Guo
- **doi**: https://doi.org/10.1016/j.cose.2022.102823
- **cited-by**: 40 | **source**: OpenAlex | **tag**: 经典-GNN
- **pdf**: -

> (无摘要)

## [14] Python source code vulnerability detection with named entity recognition

- **cite_key**: `-`
- **year**: 2024 | **venue**: Computers & Security
- **authors**: M. Ehrenberg, Shahram Sarkani, Thomas A. Mazzuchi
- **doi**: https://doi.org/10.1016/j.cose.2024.103802
- **cited-by**: 15 | **source**: OpenAlex | **tag**: 经典-NER
- **pdf**: -

> Vulnerabilities within source code have grown over the last 20 years to become a common threat to systems and networks. As the implementation of open-source software continues to develop, more unknown vulnerabilities will exist throughout system networks. This research proposes an enhanced vulnerability detection method specific to Python source code that utilizes pre-trained, BERT-based transformer models to apply tokenization, embedding, and named entity recognition (a natural language processing technique). The use of named entity recognition not only allows for the detection of potential vulnerabilities, but also for the classification of different vulnerability types. This research uses the publicly available CodeBERT, RoBERTa, and DistilBERT models to fine-tune for the downstream task of token classification for six different common weakness enumeration specifications. The results achieved in this research outperform previous Python-based vulnerability detection methods. 代码开源：github.com/sonhai1401/PyVulDet-NER [来源：ScienceDirect/PlumX 官方摘要]

## [15] AIBugHunter: A Practical tool for predicting, classifying and repairing software vulnerabilities

- **cite_key**: `-`
- **year**: 2023 | **venue**: Empirical Software Engineering
- **authors**: Michael C. Fu, Chakkrit Tantithamthavorn, Trung Le, Yuki Kume, Van Nguyen, Dinh Phung, John Grundy
- **doi**: https://doi.org/10.1007/s10664-023-10346-3
- **cited-by**: 66 | **source**: OpenAlex | **tag**: 经典-工具
- **pdf**: -

> Abstract Many Machine Learning(ML)-based approaches have been proposed to automatically detect, localize, and repair software vulnerabilities. While ML-based methods are more effective than program analysis-based vulnerability analysis tools, few have been integrated into modern Integrated Development Environments (IDEs), hindering practical adoption. To bridge this critical gap, we propose in this article AIBugHunter , a novel Machine Learning-based software vulnerability analysis tool for C/C++ languages that is integrated into the Visual Studio Code (VS Code) IDE. AIBugHunter helps software developers to achieve real-time vulnerability detection, explanation, and repairs during programming. In particular, AIBugHunter scans through developers’ source code to (1) locate vulnerabilities, (2) identify vulnerability types, (3) estimate vulnerability severity, and (4) suggest vulnerability repairs. We integrate our previous works (i.e., LineVul and VulRepair) to achieve vulnerability localization and repairs. In this article, we propose a novel multi-objective optimization (MOO)-based vulnerability classification approach and a transformer-based estimation approach to help AIBugHunter accurately identify vulnerability types and estimate severity. Our empirical experiments on a large dataset consisting of 188K+ C/C++ functions confirm that our proposed approaches are more accurate than other state-of-the-art baseline methods for vulnerability classification and estimation. Furthermore, we conduct qualitative evaluations including a survey study and a user study to obtain software practitioners’ perceptions of our AIBugHunter tool and assess the impact that AIBugHunter may have on developers’ productivity in security aspects. Our survey study shows that our AIBugHunter is perceived as useful where 90% of the participants consider adopting our AIBugHunter during their software development. Last but not least, our user study shows that our AIBugHunter can enhance developers’ productivity in combating cybersecurity issues during software development. AIBugHunter is now publicly available in the Visual Studio Code marketplace.

## [16] Detecting Broken Object-Level Authorization Vulnerabilities in Database-Backed Applications

- **cite_key**: `Hua24`
- **year**: 2024 | **venue**: Proceedings of the 2024 on ACM SIGSAC Conference on Computer and Communications Security
- **authors**: Yongheng Huang, Chenghang Shi, Jie Lu, Haofeng Li, Haining Meng, Lian Li
- **doi**: https://doi.org/10.1145/3658644.3690227
- **cited-by**: 15 | **source**: Undermind | **tag**: API-越权
- **pdf**: 有

> Broken object-level authorization (BOLA) vulnerabilities are among the most critical security risks facing database-backed applications. However, there is still a significant gap in our systematic understanding of these vulnerabilities. To bridge this gap, we conducted an in-depth study of 101 real-world BOLA vulnerabilities from opensource applications. Our study revealed the four most common object-level authorization models in database-backed application. The insights gained from our study inspired the development of a new tool called BolaRay. This tool employs a combination of SQL and static analysis to automatically infer the distinct types of object-level authorization models, and subsequently verify whether existing implementations enforce appropriate checks for these models. We evaluated BolaRay using 25 popular database-backed applications, which led to the identification of 193 true vulnerabilities, including 178 vulnerabilities that have never been reported before, at a false positive rate of 21.86%. We reported all newly identified vulnerabilities to the corresponding maintainers. To date, 155 vulnerabilities have been confirmed, with 52 CVE IDs granted.

## [17] BACFuzz: Exposing the Silence on Broken Access Control Vulnerabilities in Web Applications

- **cite_key**: `Dha25`
- **year**: 2025 | **venue**: ArXiv
- **authors**: I. P. A. Dharmaadi, Mohannad Alhanahnah, Van-Thuan Pham, Fadi Mohsen, Fatih Turkmen
- **doi**: https://doi.org/10.48550/arXiv.2507.15984
- **cited-by**: 3 | **source**: Undermind | **tag**: API-越权
- **pdf**: 有

> Broken Access Control (BAC) remains one of the most critical and widespread vulnerabilities in web applications, allowing attackers to access unauthorized resources or perform privileged actions. Despite its severity, BAC is underexplored in automated testing due to key challenges: the lack of reliable oracles and the difficulty of generating semantically valid attack requests. We introduce BACFuzz, the first gray-box fuzzing framework specifically designed to uncover BAC vulnerabilities, including Broken Object-Level Authorization (BOLA) and Broken Function-Level Authorization (BFLA) in PHP-based web applications. BACFuzz combines LLM-guided parameter selection with runtime feedback and SQL-based oracle checking to detect silent authorization flaws. It employs lightweight instrumentation to capture runtime information that guides test generation, and analyzes backend SQL queries to verify whether unauthorized inputs flow into protected operations. Evaluated on 20 real-world web applications, including 15 CVE cases and 2 known benchmarks, BACFuzz detects 16 of 17 known issues and uncovers 26 previously unknown BAC vulnerabilities with low false positive rates. All identified issues have been responsibly disclosed, and artifacts will be publicly released.

## [18] BACScan: Automatic Black-Box Detection of Broken-Access-Control Vulnerabilities in Web Applications

- **cite_key**: `Liu25b`
- **year**: 2025 | **venue**: Proceedings of the 2025 ACM SIGSAC Conference on Computer and Communications Security
- **authors**: Feng Liu, Yuan Zhang, Enhao Li, Wei Meng, You-Qun Shi, Qianheng Wang, and Min Yang
- **doi**: https://doi.org/10.1145/3719027.3744825
- **cited-by**: 5 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> Broken-Access-Control (BAC) vulnerabilities have consistently been ranked among the most critical security risks in web applications, occupying the top positions in the OWASP Top 10 over the past several years. These vulnerabilities allow attackers to bypass access control mechanisms and perform unauthorized operations, posing serious security and privacy threats to sensitive business and user data. Despite substantial attention given to BAC vulnerabilities, effective and reliable approaches to detecting these issues remain limited. In this work, we present BACScan, a novel black-box approach to detect BAC vulnerabilities in web applications. Unlike existing response similarity-based oracles that check only unauthorized read accesses, BACScan introduces an innovative feedback-driven oracle, which determines whether unauthorized read or modification operations have occurred by inferring operationally-dependent web pages and analyzing the operational feedback. We evaluated BACScan on 20 real-world applications and successfully identified 89 vulnerabilities, including 54 previously unreported ones, outperforming state-of-the-art tools. We reported all newly identified vulnerabilities to the affected vendors. To date, 35 new CVE IDs have been assigned.

## [19] MOCGuard: Automatically Detecting Missing-Owner-Check Vulnerabilities in Java Web Applications

- **cite_key**: `Liu25e`
- **year**: 2025 | **venue**: 2025 IEEE Symposium on Security and Privacy (SP), pp. 903-919
- **authors**: Feng Liu, You-Qun Shi, Yuan Zhang, Guangliang Yang, Enhao Li, Min Yang
- **doi**: https://doi.org/10.1109/SP61157.2025.00010
- **cited-by**: 10 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> Java web applications have been extensively utilized for hosting and powering high-value commercial websites. However, their intricate complexities leave them susceptible to a critical security flaw, named Missing-Owner-Check (MOC), that may expose websites to unauthorized access and data breaches. However, the research on identifying and analyzing MOC vulnerabilities has been limited over the years. In this work, we propose a novel end-to-end vulnerability analysis approach, called MOCGuard, that can effectively vet Java web applications against MOC issues. Different from related techniques, MOCGuard pinpoints MOC vulnerabilities from a new perspective of database-centric analysis. MOCGuard first applies database structure analysis to infer user table and user-owned data. Then, MOCGuard conducts insecure access checks across both the Java and SQL layers. To thoroughly evaluate the effectiveness of MOCGuard, we collaborated with a world-leading tech company. Through our evaluation of 30 high-profile open-source Java web applications and 7 industrial Java web applications, we demonstrate that MOCGuard is automatic and effective. Consequently, it successfully uncovered 161 (confirmed) 0-day MOC vulnerabilities, leading to the assignment of 73 CVE identifiers.

## [20] Facilitating Access Control Vulnerability Detection in Modern Java Web Applications With Accurate Permission Check Identification

- **cite_key**: `Shi25`
- **year**: 2025 | **venue**: IEEE Transactions on Information Forensics and Security, pp. 10683-10698
- **authors**: You-Qun Shi, Feng Liu, Guangliang Yang, Yuan Zhang, Yinzhi Cao, Enhao Li, and Siyi Chen
- **doi**: https://doi.org/10.1109/TIFS.2025.3614424
- **cited-by**: 1 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> Access-control vulnerabilities have emerged as a significant concern in recent years, posing considerable security risks to a wide range of critical systems. The detection of access-control vulnerabilities in Java web applications poses unique challenges, because heuristics used in the past, e.g., access-control specifications or format-specific runtime logs, may not exist in modern Java web applications using web frameworks. Therefore, to date, there is no effective approach to detecting such vulnerabilities in modern Java web applications. In this paper, we introduce a novel approach, called PCFinder, which leverages multi-level semantics- and context-analysis to conduct accurate permission-check identifications against real-world Java web infrastructures for access-control vulnerability detection. PCFinder successfully discovered 58 high-risk broken access control vulnerabilities, with 30 having been assigned CVE identifiers thus far, in analyzing 50 popular, real-world Java web applications. We also evaluate PCFinder on manually constructed ground-truth data and show that PCFinder achieved a high level of accuracy, i.e., a precision of 94.12% and a recall of 96.97% in identifying permission checks.

## [21] JAuthGuard: Automatic Detection for Broken Access Control in Java Web APIs

- **cite_key**: `Fen25`
- **year**: 2025 | **venue**: 2025 IEEE International Conference on Systems, Man, and Cybernetics (SMC), pp. 3102-3107
- **authors**: Ruizhi Feng, Mengjun Zhang, Ang Xia, Jie Cheng, Yunpeng Li, Yue Zhang, Yuling Liu
- **doi**: https://doi.org/10.1109/SMC58881.2025.11343625
- **cited-by**: 1 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> Java Web applications are widely used across various industries, however, they are increasingly threatened by Broken Access Control (BAC) vulnerabilities, which may allow unauthorized users to access restricted resources. This paper proposed an automated detection method for BAC vulnerabilities at the API level in Java Web applications. We proposed JAuthGuard, a novel detection framework that combines rule-based analysis and graph-based path analysis to identify potential vulnerabilities. Our approach leverages prior knowledge of common Java Web development patterns and access control mechanisms to define target function rules, precisely locating critical functions that require strict access control checks. Additionally, based on an analysis of historical vulnerabilities, we proposed a control defect (i.e., flaws in access control mechaisms that allows unauthorized access) detection algorithm based on authentication paths. This algorithm constructs authentication paths through static analysis and incorporates LLM prompt techniques to identify control defects. We implemented the JAuthGuard and conducted an empirical evaluation, demonstrating its effectiveness, with results showing superior performance compared to the commercial tool Fortify SCA. Furthermore, the system successfully detected multiple BAC vulnerabilities in high-profile projects on GitHub, earning six CVE identifiers. By providing an automated, efficient, and accurate BAC vulnerability detection tool, this research contributes to enhancing the security of Java Web applications.

## [22] A2CT: Automated Detection of Function and Object-Level Access Control Vulnerabilities in Web Applications

- **cite_key**: `Sch25`
- **year**: 2025 | **venue**: International Conference on Information Systems Security and Privacy, pp. 425-436
- **authors**: Michael Schlaubitz, Onur Veyisoglu, Marc Rennhard
- **doi**: https://doi.org/10.5220/0013092700003899
- **cited-by**: 2 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> : In view of growing security risks, automated security testing of web applications is getting more and more important. There already exist capable tools to detect common vulnerability types such as SQL injection or cross-site scripting. Access control vulnerabilities, however, are still a vulnerability category that is much harder to detect in an automated fashion, while at the same time representing a highly relevant security problem in practice. In this paper, we present A2CT, a practical approach for the automated detection of access control vulnerabilities in web applications. A2CT supports most web applications and can detect vulnerabilities in the context of all HTTP request types (GET, POST, PUT, PATCH, DELETE). To demonstrate the practical usefulness of A2CT, an evaluation based on 30 publicly available web applications was done. Overall, A2CT managed to uncover 14 previously unknown vulnerabilities in two of these web applications, which resulted in six published CVE records. To encourage further research, the source code of A2CT is made available under an open-source license.

## [23] Metamorphic Testing for Web System Security

- **cite_key**: `Cha22`
- **year**: 2022 | **venue**: IEEE Transactions on Software Engineering, pp. 3430-3471
- **authors**: N. B. Chaleshtari, F. Pastore, Arda Goknil, L. Briand
- **doi**: https://doi.org/10.1109/TSE.2023.3256322
- **cited-by**: 37 | **source**: Undermind | **tag**: Oracle-理论
- **pdf**: 有

> Security testing aims at verifying that the software meets its security properties. In modern Web systems, however, this often entails the verification of the outputs generated when exercising the system with a very large set of inputs. Full automation is thus required to lower costs and increase the effectiveness of security testing. Unfortunately, to achieve such automation, in addition to strategies for automatically deriving test inputs, we need to address the oracle problem, which refers to the challenge, given an input for a system, of distinguishing correct from incorrect behavior (e.g., the response to be received after a specific HTTP GET request). In this paper, we propose Metamorphic Security Testing for Web-interactions (MST-wi), a metamorphic testing approach that integrates test input generation strategies inspired by mutational fuzzing and alleviates the oracle problem in security testing. It enables engineers to specify metamorphic relations (MRs) that capture many security properties of Web systems. To facilitate the specification of such MRs, we provide a domain-specific language accompanied by an Eclipse editor. MST-wi automatically collects the input data and transforms the MRs into executable Java code to automatically perform security testing. It automatically tests Web systems to detect vulnerabilities based on the relations and collected data. We provide a catalog of 76 system-agnostic MRs to automate security testing in Web systems. It covers 39% of the OWASP security testing activities not automated by state-of-the-art techniques; further, our MRs can automatically discover 102 different types of vulnerabilities, which correspond to 45% of the vulnerabilities due to violations of security design principles according to the MITRE CWE database. We also define guidelines that enable test engineers to improve the testability of the system under test with respect to our approach. We evaluated MST-wi effectiveness and scalability with two well-known Web systems (i.e., Jenkins and Joomla). It automatically detected 85% of their vulnerabilities and showed a high specificity (99.81% of the generated inputs do not lead to a false positive); our findings include a new security vulnerability detected in Jenkins. Finally, our results demonstrate that the approach scale, thus enabling automated security testing overnight.

## [24] Metamorphic Security Testing for Web Systems

- **cite_key**: `Mai19`
- **year**: 2019 | **venue**: 2020 IEEE 13th International Conference on Software Testing, Validation and Verification (ICST), pp. 186-197
- **authors**: Phu X. Mai, F. Pastore, Arda Goknil, L. Briand
- **doi**: https://doi.org/10.1109/icst46399.2020.00028
- **cited-by**: 29 | **source**: Undermind | **tag**: Oracle-理论
- **pdf**: 有

> Security testing verifies that the data and the resources of software systems are protected from attackers. Unfortunately, it suffers from the oracle problem, which refers to the challenge, given an input for a system, of distinguishing correct from incorrect behavior. In many situations where potential vulnerabilities are tested, a test oracle may not exist, or it might be impractical due to the many inputs for which specific oracles have to be defined. In this paper, we propose a metamorphic testing approach that alleviates the oracle problem in security testing. It enables engineers to specify metamorphic relations (MRs) that capture security properties of the system. Such MRs are then used to automate testing and detect vulnerabilities. We provide a catalog of 22 system-agnostic MRs to automate security testing in Web systems. Our approach targets 39% of the OWASP security testing activities not automated by state-of-the-art techniques. It automatically detected 10 out of 12 vulnerabilities affecting two widely used systems, one commercial and the other open source (Jenkins).

## [25] RESTler: Stateful REST API Fuzzing

- **cite_key**: `Atl19`
- **year**: 2019 | **venue**: 2019 IEEE/ACM 41st International Conference on Software Engineering (ICSE), pp. 748-758
- **authors**: Vaggelis Atlidakis, Patrice Godefroid, M. Polishchuk
- **doi**: https://doi.org/10.1109/ICSE.2019.00083
- **cited-by**: 322 | **source**: Undermind | **tag**: API-模糊测试
- **pdf**: -

> This paper introduces RESTler, the first stateful REST API fuzzer. RESTler analyzes the API specification of a cloud service and generates sequences of requests that automatically test the service through its API. RESTler generates test sequences by (1) inferring producer-consumer dependencies among request types declared in the specification (e.g., inferring that "a request B should be executed after request A" because B takes as an input a resource-id x produced by A) and by (2) analyzing dynamic feedback from responses observed during prior test executions in order to generate new tests (e.g., learning that "a request C after a request sequence A;B is refused by the service" and therefore avoiding this combination in the future). We present experimental results showing that these two techniques are necessary to thoroughly exercise a service under test while pruning the large search space of possible request sequences. We used RESTler to test GitLab, an open-source Git service, as well as several Microsoft Azure and Office365 cloud services. RESTler found 28 bugs in GitLab and several bugs in each of the Azure and Office365 cloud services tested so far. These bugs have been confirmed and fixed by the service owners.

## [26] LLM-Assisted IDOR Detection in Hospital Mini-Programs: Risks to PII and PHI

- **cite_key**: `Sun25b`
- **year**: 2025 | **venue**: 2025 IEEE 24th International Conference on Trust, Security and Privacy in Computing and Communications (TrustCom), pp. 2078-2086
- **authors**: Jiawen Sun, R. Tian, Shangru Zhao, Xiangming Zhou, He Wang, Yuqing Zhang
- **doi**: https://doi.org/10.1109/Trustcom66490.2025.00242
- **cited-by**: 0 | **source**: Undermind | **tag**: LLM-越权
- **pdf**: -

> Hospital mini-programs have become widely adopted as lightweight portals for medical services, handling large volumes of personally identifiable information (PII) and protected health information (PHI). Among the most critical threats to such systems is the insecure direct object reference (IDOR) vulnerability, which allows unauthorized access to sensitive resources due to improper object–level access control. However, systematic detection of IDOR in the wild, especially within hospital mini-programs, remains underexplored due to restricted server access and stringent ethical regulations. To address this challenge, we propose a black–box detection framework designed for hospital mini-programs operating in sensitive data environments. Our framework introduces a novel token–substitution probing strategy that adheres to ethical standards and pioneers the use of Large Language Models (LLMs) for automated IDOR vulnerability detection in API endpoints, enabling token field identification, request classification and differential response analysis. We evaluated the framework on 80 real-world mini-programs and identified 114 vulnerable endpoints across 38 applications. Among these, 55 involved sensitive data disclosure, and 34 enabled unauthorized execution of sensitive operations. All findings were responsibly disclosed to the CNVD, and 15 cases have been officially confirmed.

## [27] A hybrid LLM workflow can help identify user privilege related variables in programs of any size

- **cite_key**: `Wan24b`
- **year**: 2024 | **venue**: ArXiv
- **authors**: Haizhou Wang, Zhilong Wang, Peng Liu
- **doi**: https://doi.org/10.48550/arXiv.2403.15723
- **cited-by**: 4 | **source**: Undermind | **tag**: LLM-越权
- **pdf**: 有

> Many programs involves operations and logic manipulating user privileges, which is essential for the security of an organization. Therefore, one common malicious goal of attackers is to obtain or escalate the privileges, causing privilege leakage. To protect the program and the organization against privilege leakage attacks, it is important to eliminate the vulnerabilities which can be exploited to achieve such attacks. Unfortunately, while memory vulnerabilities are less challenging to find, logic vulnerabilities are much more imminent, harmful and difficult to identify. Accordingly, many analysts choose to find user privilege related (UPR) variables first as start points to investigate the code where the UPR variables may be used to see if there exists any vulnerabilities, especially the logic ones. In this paper, we introduce a large language model (LLM) workflow that can assist analysts in identifying such UPR variables, which is considered to be a very time-consuming task. Specifically, our tool will audit all the variables in a program and output a UPR score, which is the degree of relationship (closeness) between the variable and user privileges, for each variable. The proposed approach avoids the drawbacks introduced by directly prompting a LLM to find UPR variables by focusing on leverage the LLM at statement level instead of supplying LLM with very long code snippets. Those variables with high UPR scores are essentially potential UPR variables, which should be manually investigated. Our experiments show that using a typical UPR score threshold (i.e., UPR score>0.8), the false positive rate (FPR) is only 13.49%, while UPR variable found is significantly more than that of the heuristic based method.

## [28] Enchanting Program Specification Synthesis by Large Language Models using Static Analysis and Program Verification

- **cite_key**: `Wen24`
- **year**: 2024 | **venue**: International Conference on Computer Aided Verification, pp. 302-328
- **authors**: Cheng Wen, Jialun Cao, Jie Su, Zhiwu Xu, Shengchao Qin, Mengda He, and Cong Tian
- **doi**: https://doi.org/10.48550/arXiv.2404.00762
- **cited-by**: 131 | **source**: Undermind | **tag**: LLM-规格
- **pdf**: 有

> Formal verification provides a rigorous and systematic approach to ensure the correctness and reliability of software systems. Yet, constructing specifications for the full proof relies on domain expertise and non-trivial manpower. In view of such needs, an automated approach for specification synthesis is desired. While existing automated approaches are limited in their versatility, i.e., they either focus only on synthesizing loop invariants for numerical programs, or are tailored for specific types of programs or invariants. Programs involving multiple complicated data types (e.g., arrays, pointers) and code structures (e.g., nested loops, function calls) are often beyond their capabilities. To help bridge this gap, we present AutoSpec, an automated approach to synthesize specifications for automated program verification. It overcomes the shortcomings of existing work in specification versatility, synthesizing satisfiable and adequate specifications for full proof. It is driven by static analysis and program verification, and is empowered by large language models (LLMs). AutoSpec addresses the practical challenges in three ways: (1) driving \name by static analysis and program verification, LLMs serve as generators to generate candidate specifications, (2) programs are decomposed to direct the attention of LLMs, and (3) candidate specifications are validated in each round to avoid error accumulation during the interaction with LLMs. In this way, AutoSpec can incrementally and iteratively generate satisfiable and adequate specifications. The evaluation shows its effectiveness and usefulness, as it outperforms existing works by successfully verifying 79% of programs through automatic specification synthesis, a significant improvement of 1.592x. It can also be successfully applied to verify the programs in a real-world X509-parser project.

## [29] Automated Generation of Microservice Authorization Tests Using Large Language Models

- **cite_key**: `Udd26`
- **year**: 2026 | **venue**: 2026 International Conference on Service-Oriented System Engineering (SOSE), pp. 41-50
- **authors**: Md Arfan Uddin, Shakthi Weerasinghe, Connor Wojtak, Tomás Cerný, Deuslirio Silva-Junior, Mateus Eduardo S. Ribeiro, and Amr S. Abdelfattah
- **doi**: https://doi.org/10.1109/SOSE71128.2026.00014
- **cited-by**: 0 | **source**: Undermind | **tag**: LLM-越权
- **pdf**: -

> Microservice architectures are inherently plagued by "authorization blindspots"–divergent security policies across independent services that create undetectable downstream security drifts. As systems evolve, these invisible vulnerabilities leave applications highly susceptible to privilege escalation and catastrophic data breaches. To eliminate these blindspots, we introduce a novel, fully automated framework that bridges the precision of formal static analysis with the adaptiveness of Generative AI. By extracting a policy-enriched Intermediate Representation of the microservice system, our approach deterministically guides GPT-5 to synthesize executable, downstream-aware policy test suites targeting specific policy inconsistencies. Evaluation on the Train-Ticket benchmark denotes that our method outperforms state-of-the-art tools such as EvoMaster and EvoSuite by generating 100% semantically valid authorization policy tests. Further, this research provides vital empirical validation for formal methods. By producing 97.4% error-free drift validation tests, our approach systematically neutralizes static analysis noise. Ultimately, these results establish a rigorous, highly effective pathway for hybridizing formal structures with Large Language Models to definitively verify complex, distributed authorization policies.

## [30] Large Language Model-Powered Protected Interface Evasion: Automated Discovery of Broken Access Control Vulnerabilities in Internet of Things Devices

- **cite_key**: `Wan25d`
- **year**: 2025 | **venue**: Sensors (Basel, Switzerland)
- **authors**: Enze Wang, Wei Xie, Shuhuan Li, Runhao Liu, Yuan Zhou, Zhenhua Wang, and Baosheng Wang
- **doi**: https://doi.org/10.3390/s25092913
- **cited-by**: 4 | **source**: Undermind | **tag**: LLM-越权
- **pdf**: 有

> Broken access control vulnerabilities pose significant security risks to the protected web interfaces of IoT devices, enabling adversaries to gain unauthorized access to sensitive configurations and even use them as stepping stones for attacking the intranet. Despite its ranking as the first in the latest OWASP Top 10, there remains a lack of effective methodologies to detect these vulnerabilities systematically. We present ACBreaker, a novel methodology powered by a large language model (LLM), to effectively identify broken access control vulnerabilities in the protected web interfaces of IoT devices. Our methodology consists of three stages. The initial stage transforms firmware code that exceeds the LLM context window into semantically intact code snippets. The second stage involves using an LLM to extract device-specific information from firmware code. The final stage integrates this information into the mutation-based fuzzer to improve fuzzing effectiveness and employ differential analysis to identify vulnerabilities. We evaluated ACBreaker across 11 IoT devices, analyzing 1,274,646 lines of code and discovering 39 previously unknown vulnerabilities. We further analyzed these vulnerabilities, categorizing them into three types that contribute to protected interface evasion, and provided mitigation suggestions. These vulnerabilities were responsibly disclosed to vendors, with CVE IDs assigned to those in six IoT devices.

## [31] Measuring the Reasoning Boundaries of Large Language Models for Implicit Security Invariants in Code: A Controlled Empirical Study

- **cite_key**: `Wan26`
- **year**: 2026 | **venue**: 2026 IEEE 50th Annual Computers, Software, and Applications Conference (COMPSAC), pp. 3146-3157
- **authors**: Ruofei Wang, Honglin Zhuang, Huayang Cao, Siqi Chen
- **doi**: https://doi.org/10.1109/COMPSAC69091.2026.00467
- **cited-by**: 0 | **source**: Undermind | **tag**: LLM-评测
- **pdf**: -

> This paper investigates the trust boundary of LLMassisted code security auditing, focusing on implicit security properties (security invariants) that are not expressed as explicit local rules but must hold throughout correct workflows. We propose a six-level semantic taxonomy spanning from explicit defects to workflow/state-machine invariants, and construct an evaluation suite that combines real-world, commit-traced vulnerable code fragments with controlled synthetic samples. We employ two prompting regimes and two context levels to compare auditing capability under natural versus strengthened conditions, and use a layered annotation scheme to characterize hit quality by separating vulnerability identification, localization, and invariant reconstruction. Our results show that richer context and task-focused prompting can partially improve reasoning for some implicit properties; however, when vulnerabilities hinge on missing constraints (absent guards/checks) and multi-step state dependencies required to recover workflow invariants, LLMs exhibit a stable failure regime and tend to produce coherent yet ground-truth-inconsistent alternative vulnerability narratives.

## [32] Can LLMs Reason About Program Semantics? A Comprehensive Evaluation of LLMs on Formal Specification Inference

- **cite_key**: `Lec25`
- **year**: 2025 | **venue**: Annual Meeting of the Association for Computational Linguistics, pp. 21991-22014
- **authors**: Thanh Le-Cong, Bach Le, Toby Murray
- **doi**: https://doi.org/10.48550/arXiv.2503.04779
- **cited-by**: 35 | **source**: Undermind | **tag**: LLM-评测
- **pdf**: 有

> Large Language Models (LLMs) are increasingly being used to automate programming tasks. Yet, LLMs' capabilities in reasoning about program semantics are still inadequately studied, leaving significant potential for further exploration. This paper introduces FormalBench, a comprehensive benchmark designed to evaluate LLMs' reasoning abilities on program semantics, particularly via the task of synthesizing formal program specifications to assist verifying program correctness. This task requires both comprehensive reasoning over all possible program executions and the generation of precise, syntactically correct expressions that adhere to formal syntax and semantics. Using this benchmark, we evaluated the ability of LLMs in synthesizing consistent and complete specifications. Our findings show that LLMs perform well with simple control flows but struggle with more complex structures, especially loops, even with advanced prompting. Additionally, LLMs exhibit limited robustness against semantic-preserving transformations. We also highlight common failure patterns and design self-repair prompts, improving success rates by 25%.

## [33] Data Quality for Software Vulnerability Datasets

- **cite_key**: `Cro23`
- **year**: 2023 | **venue**: 2023 IEEE/ACM 45th International Conference on Software Engineering (ICSE), pp. 121-133
- **authors**: Roland Croft, M. A. Babar, M. M. Kholoosi
- **doi**: https://doi.org/10.1109/ICSE48619.2023.00022
- **cited-by**: 209 | **source**: Undermind | **tag**: 数据集-质量
- **pdf**: 有

> The use of learning-based techniques to achieve automated software vulnerability detection has been of longstanding interest within the software security domain. These data-driven solutions are enabled by large software vulnerability datasets used for training and benchmarking. However, we observe that the quality of the data powering these solutions is currently ill-considered, hindering the reliability and value of produced outcomes. Whilst awareness of software vulnerability data preparation challenges is growing, there has been little investigation into the potential negative impacts of software vulnerability data quality. For instance, we lack confirmation that vulnerability labels are correct or consistent. Our study seeks to address such shortcomings by inspecting five inherent data quality attributes for four state-of-the-art software vulnerability datasets and the subsequent impacts that issues can have on software vulnerability prediction models. Surprisingly, we found that all the analyzed datasets exhibit some data quality problems. In particular, we found 20–71% of vulnerability labels to be inaccurate in real-world datasets, and 17-99% of data points were duplicated. We observed that these issues could cause significant impacts on downstream models, either preventing effective model training or inflating benchmark performance. We advocate for the need to overcome such challenges. Our findings will enable better consideration and assessment of software vulnerability data quality in the future.

## [34] Automated reverse engineering of role-based access control policies of web applications

- **cite_key**: `Le21`
- **year**: 2021 | **venue**: J. Syst. Softw., pp. 111109
- **authors**: H. Le, Lwin Khin Shar, D. Bianculli, L. Briand, Duy Cu Nguyen
- **doi**: https://doi.org/10.1016/j.jss.2021.111109
- **cited-by**: 11 | **source**: Undermind | **tag**: 策略推断
- **pdf**: 有

> Access control (AC) is an important security mechanism used in software systems to restrict access to sensitive resources. Therefore, it is essential to validate the correctness of AC implementations with respect to policy specifications or intended access rights. However, in practice, AC policy specifications are often missing or poorly documented; in some cases, AC policies are hard-coded in business logic implementations. This leads to difficulties in validating the correctness of policy implementations and detecting AC defects. In this paper, we present a semi-automated framework for reverse-engineering of AC policies from Web applications. Our goal is to learn and recover role-based access control (RBAC) policies from implementations, which are then used to validate implemented policies and detect AC issues. Our framework, built on top of a suite of security tools, automatically explores a given Web application, mines domain input specifications from access logs, and systematically generates and executes more access requests using combinatorial test generation. To learn policies, we apply machine learning on the obtained data to characterize relevant attributes that influence AC. Finally, the inferred policies are presented to the security engineer, for validation with respect to intended access rights and for detecting AC issues. Inconsistent and insufficient policies are highlighted as potential AC issues, being either vulnerabilities or implementation errors. We evaluated our approach on four Web applications (three open-source and a proprietary one built by our industry partner) in terms of the correctness of inferred policies. We also evaluated the usefulness of our approach by investigating whether it facilitates the detection of AC issues. The results show that 97.8% of the inferred policies are correct with respect to the actual AC implementation; the analysis of these policies led to the discovery of 64 AC issues that were reported to the developers.

## [35] Static Extraction of Enforced Authorization Policies SeeAuthz

- **cite_key**: `Ber20`
- **year**: 2020 | **venue**: 2020 IEEE 20th International Working Conference on Source Code Analysis and Manipulation (SCAM), pp. 187-197
- **authors**: B. Berger, Rodrigue Wete Nguempnang, K. Sohr, R. Koschke
- **doi**: https://doi.org/10.1109/SCAM51674.2020.00026
- **cited-by**: 3 | **source**: Undermind | **tag**: 策略推断
- **pdf**: -

> Authorization is an intrinsic part of a software’s security. Determining whether a user is allowed to access a resource or not is crucial, not only in safety-critical applications but also in everyday applications to prevent misuse of data or software. There is plenty of research dealing with validating and verifying authorization policies in the security community. Still, an implemented authorization policy does not necessarily match the planned authorization policy, i.e., even a validated and verified authorization policy can pose security issues when implemented incorrectly. This gap between planned and implemented authorization policy poses the risk of unauthorized access to sensitive resources due to insufficient authorization checks. Therefore, it is essential to ensure a system’s security to validate the implemented authorization policy against the planned one. We, therefore, describe the authorization pattern and present an algorithm to extract authorization graphs from implemented authorization policies, which can then be used to compare against the planned authorization policy. To that end, we developed a configurable context-sensitive analysis tailored to Java-based software systems, where the context is the authorization facts that hold on each point. Using a configuration for Apache Shiro, a security library that supports authorization, we evaluated our implementation using an open-source repository system for the management and dissemination of digital content and a closed-source manufacturing execution system. We discuss additional usage scenarios of the analysis results and describe how to transfer the approach to other authorization policies and programming languages.

## [36] Extracting Database Access-control Policies From Web Applications

- **cite_key**: `Zha24b`
- **year**: 2024 | **venue**: ArXiv
- **authors**: Wen Zhang, Dev Bali, Jamison Kerney, Aurojit Panda, S. Shenker
- **doi**: https://doi.org/10.48550/arXiv.2411.11380
- **cited-by**: 1 | **source**: Undermind | **tag**: 策略推断
- **pdf**: 有

> To safeguard sensitive user data, web developers typically rely on implicit access-control policies, which they implement using access checks and query filters. This ad hoc approach is error-prone as these scattered checks and filters are easy to misplace or misspecify, and the lack of an explicit policy precludes external access-control enforcement. More critically, it is difficult for humans to discern what policy is embedded in application code (i.e., what data the application may access) -- an issue that worsens as development teams evolve. This paper tackles policy extraction: the task of extracting the access-control policy embedded in an application by summarizing its data queries. An extracted policy, once vetted for errors, can stand alone as a specification for the application's data access, and can be enforced to ensure compliance as code changes over time. We introduce Ote, a policy extractor for Ruby on Rails web applications. Ote uses concolic execution to explore execution paths through the application, generating traces of SQL queries and conditions that trigger them. It then merges and simplifies these traces into a final policy that aligns with the observed behaviors. We applied Ote to three real-world applications and compared extracted policies to handwritten ones, revealing several errors in the latter.

## [37] Detecting Privilege Escalation in Polyglot Microservices via Agentic Program Analysis

- **cite_key**: `Li26g`
- **year**: 2026 | **venue**: 2026 IEEE Symposium on Security and Privacy (SP), pp. 1747-1765
- **authors**: Penghui Li, H. Chong, Yinzhi Cao, Junfeng Yang
- **doi**: https://doi.org/10.1109/SP63933.2026.00121
- **cited-by**: 2 | **source**: Undermind | **tag**: Agentic分析
- **pdf**: 有

> Microservices are widely adopted in modern cloud systems due to their scalability and fault tolerance. However, microservice architectures introduce significant complexity in privilege and permission control, creating risks of privilege escalation where attackers can gain unauthorized access to resources or operations. Detecting such vulnerabilities is challenging due to complex cross-service interactions, polyglot codebases, and diverse privileged operations and permission checks. We present NeO, an agentic program analysis framework that combines large language models (LLMs) with classic program analysis to address these challenges. Neo leverages an LLM-based agent that dynamically generates analysis plans, adapts code search strategies, and validates semantics. We develop code search primitives that enable NeO to perform scalable and flexible code exploration across services and languages. We evaluated NEO on 25 open-source microservice applications spanning 7 programming languages and 6.2 million lines of code. NeO uncovered 24 zero-day privilege escalation vulnerabilities and achieved 81.0 % precision and 85.0 % recall on a ground-truth dataset. Compared to existing program analysis and agentic solutions, Neo demonstrated significant improvements in both detection accuracy and scalability. We further showcased Neo's extensibility by applying it to other application domains and vulnerability types, uncovering 18 additional zero-day vulnerabilities.

## [38] 403 Forbidden? Ethically Evaluating Broken Access Control in the Wild

- **cite_key**: `Che25c`
- **year**: 2025 | **venue**: 2025 IEEE Symposium on Security and Privacy (SP), pp. 3218-3235
- **authors**: Saiid El Hajj Chehade, Florian Hantke, Ben Stock
- **doi**: https://doi.org/10.1109/SP61157.2025.00252
- **cited-by**: 6 | **source**: Undermind | **tag**: API-越权
- **pdf**: -

> In the context of web applications, the most prevalent vulnerability, according to the OWASP Top Ten, is broken access control. As access control (AC) is implemented on the server side, not having access to the code in live systems limits the ability of researchers to study improper AC issues in the wild. While several works have identified vulnerabilities in open-source applications deployed in researcher-controlled environments, the problem has not been studied in the wild because of ethical and legal considerations to not leak unknowing users' data. We address this gap in research and present the Variable Swapping Framework (VSF), the first ethically sound and scalable black-box framework to test for improper AC patterns in the wild. VSF's design is the result of our indepth ethical stakeholder analysis and risk minimization while maximizing benefits in vulnerability detection. At its core, it relies on two accounts per site and swaps identifiers between them to access one account's resources with the other. On 100 web apps successfully tested, we find a total of 584 potential AC-sensitive HTTP endpoints, out of which 19 (across 7 sites) are exploitable flaws, which we disclosed responsibly.

## [39] AUTHSCOPE: Towards Automatic Discovery of Vulnerable Authorizations in Online Services

- **cite_key**: `Zuo17`
- **year**: 2017 | **venue**: Proceedings of the 2017 ACM SIGSAC Conference on Computer and Communications Security
- **authors**: Chaoshun Zuo, Qingchuan Zhao, Zhiqiang Lin
- **doi**: https://doi.org/10.1145/3133956.3134089
- **cited-by**: 63 | **source**: Undermind | **tag**: 经典-越权
- **pdf**: 有

> Abstract unavailable  PDF symbols - ✓ PDF available; X No PDF available; … PDF download attempt in progress  Locations: 📁 01-BOLA-BFLA 检测/ │   └── 🔍 BOLA BFLA 自动化检测技术全景  [Hua24, Dha25, Liu25e, Arc25, Liu25b, Che25c, Sun25b, Shi25, Sch25, Li26g, Fen25, Zuo17, Udd26, Wan25d, Atl19, Le21, Ber20, Zha24b, Mai19]  … and 129 more 📁 02-LLM 授权语义推理/ │   └── 🔍 LLM 推断授权与访问控制语义  [Hua24, Liu25e, Le21, Wen24, Li26g, Zha24b, Shi25, Wan26, Ber20, Lec25, Wan24b, Dha25, Wan25d, Udd26, Fen25, Sun25b]  … and 106 more 📁 03-Oracle 与差分测试/     └── 🔍 Security Oracle 与差分测试  [Arc25, Che25c, Cha22, Liu25b, Sun25b, Zuo17, Dha25, Cro23, Mai19, Sch25, Hua24, Shi25, Liu25e, Atl19, Wan25d]  … and 151 more  When using cite keys in your reply to the user, format as [[cite_key]](url), where url is https://doi.org/<DOI> for the DOI shown above (or the exact Link shown for papers without one), separating multiple with commas. In workspace files, keep bare [cite_key] markers with no URLs.
