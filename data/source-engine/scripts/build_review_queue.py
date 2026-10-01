import argparse, json
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument("questions_json")
ap.add_argument("--out",required=True)
args=ap.parse_args()

data=json.loads(Path(args.questions_json).read_text(encoding="utf-8"))
queue=[]
for q in data.get("blocks",[]):
    queue.append({
        "question_number":q.get("question_number"),
        "page_start":q.get("page_start"),
        "page_end":q.get("page_end"),
        "status":"NEEDS_REVIEW",
        "checks":{
            "source_verified":False,
            "year_verified":False,
            "booklet_verified":False,
            "question_number_verified":False,
            "text_verified":False,
            "options_verified":False,
            "answer_key_verified":q.get("answer_match_status")=="MATCHED",
            "curriculum_verified":False,
            "solution_verified":False,
            "duplicate_checked":False
        }
    })
Path(args.out).write_text(json.dumps({"count":len(queue),"items":queue},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"review items: {len(queue)}")
