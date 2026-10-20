from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
for label,path,num in [('letter',ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.pdf',4),('main',ROOT/'03_论文撰写/paper/main.pdf',18)]:
    with pymupdf.open(path) as doc:
        p=doc[num-1];p.get_pixmap(matrix=pymupdf.Matrix(1.35,1.35)).save(OUT/f'{label}_page_{num}.png')
