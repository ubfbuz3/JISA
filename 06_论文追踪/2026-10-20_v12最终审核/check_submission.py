"""Check the five physical submission files and original-title field."""
from pathlib import Path
import hashlib,json,re,zipfile,xml.etree.ElementTree as ET
import pymupdf
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
SUB=ROOT/'07_投稿_v12'
canonical={'response_to_reviewers.pdf':ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.pdf','main_highlighted.pdf':ROOT/'03_论文撰写/response_to_reviewers/main_highlighted.pdf','main.pdf':ROOT/'03_论文撰写/paper/main.pdf','latex_source_files_submission.zip':ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'}
hashes={}
for line in (SUB/'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
    h,n=line.split(maxsplit=1);hashes[n.strip()]=h
result={'files':{},'authors':{},'byline':{}}
for n,p in canonical.items():
    content=(SUB/n).read_bytes();h=hashlib.sha256(content).hexdigest()
    result['files'][n]={'bytes':len(content),'sha256':h,'matches_canonical':content==p.read_bytes(),'matches_manifest':h==hashes[n]}
    assert result['files'][n]['matches_canonical'] and result['files'][n]['matches_manifest']
    if n.endswith('.pdf'):
        with pymupdf.open(SUB/n) as doc:
            result['authors'][n]={'metadata':doc.metadata.get('author'),'first_page_names':{name:name.lower() in doc[0].get_text().lower() for name in ['Qiulong Lin','Xiaoyu Ke','Nanlei Chen']}}
original=(ROOT/'06_论文追踪/2026-10-18_IEEEAccess重投诊断/本轮决定信与审稿意见_原文.txt').read_text(encoding='utf8')
original_title=re.search(r'entitled "([^"]+)"',original).group(1)
docx=SUB/'Request_for_Byline_Change_Access-2026-49387.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(docx) as z:
    root=ET.fromstring(z.read('word/document.xml'))
    paras=[''.join(t.itertext()) for t in root.findall('.//w:p',ns)]
text='\n'.join(paras)
(OUT/'byline_text.txt').write_text(text,encoding='utf8')
field=next(p for p in paras if p.startswith('Original Article Title:'))
result['byline']={'file':str(docx),'sha256':hashlib.sha256(docx.read_bytes()).hexdigest(),'original_title_from_editor':original_title,'field':field,'original_title_correct':original_title in field,'old_list_present':'Qiulong Lin; Nanlei Chen (corresponding author)' in text,'new_list_present':'Qiulong Lin; Xiaoyu Ke; Nanlei Chen (corresponding author)' in text}
(OUT/'submission_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
