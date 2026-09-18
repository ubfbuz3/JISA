# -*- coding: utf-8 -*-
"""把网页检索补到的摘要写回 final_selection.json，并重建内联材料"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(BASE, "_scripts", "final_selection.json")
sel = json.load(open(p, encoding="utf-8"))

FOUND = {
    "10.1016/j.jss.2024.112031":
        "Software vulnerabilities inflict considerable economic and societal harm. Therefore, timely and "
        "accurate detection of these flaws has become vital. Large language models (LLMs) have emerged as a "
        "promising tool for vulnerability detection in recent studies. However, their effectiveness suffers "
        "when limited to plain text source code, which may ignore the syntactic and semantic information of "
        "the code. To address this limitation, we propose a novel vulnerability detection approach GRACE that "
        "empowers LLM-based software vulnerability detection by incorporating graph structural information in "
        "the code and in-context learning. We also design an effective demonstration retrieval approach that "
        "identifies highly relevant code examples by considering semantic, lexical, and syntactic similarities "
        "for the target code to provide better demonstrations for in-context learning. To evaluate the "
        "effectiveness of GRACE, we conducted an empirical study on three vulnerability detection datasets "
        "(i.e., Devign, Reveal, and Big-Vul). The results demonstrate that GRACE outperforms six "
        "state-of-the-art vulnerability detection baselines by at least 28.65% in terms of the F1 score "
        "across these three datasets. Keywords: Graph structure; In-context learning; Large language model; "
        "Source code representation; Vulnerability detection. [来源：ScienceDirect/ACM 官方摘要页]",
    "10.1016/j.jss.2024.112234":
        "Software vulnerability detection is generally supported by automated static analysis tools, which have "
        "recently been reinforced by deep learning (DL) models. However, despite the superior performance of "
        "DL-based approaches over rule-based ones in research, applying DL approaches to software vulnerability "
        "detection in practice remains a challenge. This is due to the complex structure of source code, the "
        "black-box nature of DL, and the extensive domain knowledge required to understand and validate the "
        "black-box results for addressing tasks after detection. Conventional DL models are trained by specific "
        "projects and, hence, excel in identifying vulnerabilities in these projects but not in others. These "
        "models with poor performance in vulnerability detection would impact the downstream tasks such as "
        "location and repair. More importantly, these models do not provide explanations for developers to "
        "comprehend detection results. In contrast, Large Language Models (LLMs) with prompting techniques "
        "achieve stable performance across projects and provide explanations for results. However, using "
        "existing prompting techniques, the detection performance of LLMs is relatively low and cannot be used "
        "for real-world vulnerability detections. This paper contributes DLAP, a Deep Learning Augmented LLMs "
        "Prompting framework that combines the best of both DL models and LLMs to achieve exceptional "
        "vulnerability detection performance. Experimental evaluation results confirm that DLAP outperforms "
        "state-of-the-art prompting frameworks, including role-based prompts, auxiliary information prompts, "
        "chain-of-thought prompts, and in-context learning prompts, as well as fine-tuning, on multiple "
        "metrics. [来源：ScienceDirect/arXiv:2405.01202]",
    "10.1016/j.cose.2024.104151":
        "Identifying vulnerabilities in software code is crucial for ensuring the security of modern systems. "
        "However, manual detection requires expert knowledge and is time-consuming, underscoring the need for "
        "automated techniques. In this paper, we present SecureQwen, a novel vulnerability detection tool "
        "leveraging large language models (LLMs) with a context length of 64K tokens to identify potential "
        "security threats in large-scale Python codebases. Utilizing a decoder-only transformer architecture, "
        "SecureQwen captures complex relationships between code tokens, enabling accurate classification of "
        "vulnerable code sequences across 14 common weakness enumerations (CWEs), including OS Command "
        "Injection, SQL Injection, Improper Check or Handling of Exceptional Conditions, Path Traversal, Broken "
        "or Risky Cryptographic Algorithm, Deserialization of Untrusted Data, and Cleartext Transmission of "
        "Sensitive Information. We evaluate SecureQwen on a large Python dataset with over 1.875 million "
        "function-level code snippets from different sources, including GitHub repositories, Codeparrot's "
        "dataset, and synthetic data generated by GPT-4o. The experimental evaluation demonstrates high "
        "accuracy, with F1 scores ranging from 84% to 99%. [来源：ScienceDirect 官方摘要页]",
    "10.1016/j.jisa.2024.103925":
        "Vulnerability detection is a critical research topic. However, the performance of existing neural "
        "network-based approaches requires further improvement. The emergence of large language models (LLMs) "
        "has demonstrated their superior performance in natural language processing (NLP) compared to "
        "conventional neural architectures, motivating researchers to apply LLMs for vulnerability detection. "
        "This paper focuses on evaluating the performance of various Transformer-based LLMs for "
        "source-code-level vulnerability detection. We propose a framework named VulACLLM (AST & CFG-based "
        "LLMs Vulnerability Detection), which leverages combined feature sets derived from Abstract Syntax "
        "Tree (AST) and Control Flow Graph (CFG). The recall rate of VulACLLM in the field of vulnerability "
        "detection reached 0.73, while the F1-score achieved 0.725. Experimental results show that the "
        "proposed feature sets significantly enhance detection performance. To further improve the efficiency "
        "of LLM-based detection, we examine the performance of LLMs compressed using two techniques: Knowledge "
        "Distillation (KD) and Low-Rank Adaptation (LoRA). To assess the performance of these compressed "
        "models, we introduce efficiency metrics that quantify both performance loss and efficiency gains "
        "achieved through compression. Our findings reveal that, compared to KD, LLMs compressed with LoRA "
        "achieve higher recall, achieving a maximum recall rate of 0.82, while substantially reducing training "
        "time, taking only 20 min to complete one epoch, and disk size, requiring only 4.89 MB of memory. "
        "[来源：ScienceDirect 官方摘要页]",
    "10.1016/j.cose.2024.103802":
        "Vulnerabilities within source code have grown over the last 20 years to become a common threat to "
        "systems and networks. As the implementation of open-source software continues to develop, more unknown "
        "vulnerabilities will exist throughout system networks. This research proposes an enhanced "
        "vulnerability detection method specific to Python source code that utilizes pre-trained, BERT-based "
        "transformer models to apply tokenization, embedding, and named entity recognition (a natural language "
        "processing technique). The use of named entity recognition not only allows for the detection of "
        "potential vulnerabilities, but also for the classification of different vulnerability types. This "
        "research uses the publicly available CodeBERT, RoBERTa, and DistilBERT models to fine-tune for the "
        "downstream task of token classification for six different common weakness enumeration specifications. "
        "The results achieved in this research outperform previous Python-based vulnerability detection "
        "methods. 代码开源：github.com/sonhai1401/PyVulDet-NER [来源：ScienceDirect/PlumX 官方摘要]",
}

for it in sel["core"]:
    doi = it["doi"].replace("https://doi.org/", "")
    if doi in FOUND:
        it["abstract"] = FOUND[doi]

json.dump(sel, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

still = [it["doi"] for it in sel["core"] if not (it["abstract"] or "").strip()]
print("仍缺摘要：", still if still else "无")

# 重建内联材料
out = []
for i, it in enumerate(sel["core"], 1):
    ab = (it["abstract"] or "(无公开摘要，需核对原文)")
    if len(ab) > 1400:
        ab = ab[:1400] + " ...[truncated]"
    out.append(
        f'[{i}] {it["title"]}\n'
        f'    venue={it["venue"]} | year={it["year"]} | cites={it["citations"]} | tag={it["_tag"]}\n'
        f'    doi={it["doi"]}\n'
        f'    abstract: {ab}'
    )
txt = "\n\n".join(out)
p2 = os.path.join(BASE, "for_codex", "_digest_inline.txt")
open(p2, "w", encoding="utf-8").write(txt)
print("内联材料长度:", len(txt))
