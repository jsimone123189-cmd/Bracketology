"""Reference results from the Python engine for the JS parity test. Reads JSON cases on stdin, writes results on stdout."""
import json, sys
from bracketology import review, fieldformat, project
cases = json.load(sys.stdin); out = []
for c in cases:
    order, applied, notes = review.apply_edits(c["order"], c["rest"], c["edits"], c["season"], c["info"])
    out.append({"order": order, "applied": applied, "notes": notes})
cfg = {"research_cutoff": review.freeze_deadline(2027).strftime("%Y-%m-%dT%H:%M:%SZ"), "final_deadline": review.freeze_deadline(2027, "final").strftime("%Y-%m-%dT%H:%M:%SZ") if review.FINAL_DEADLINE_ET.get(2027) else None,
       "lines": list(fieldformat.format_for(2027).lines), "selection_sunday": str(project.SELECTION_SUNDAY_LIVE.get(2027) or review.selection_sunday(2027))}
json.dump({"results": out, "config": cfg}, sys.stdout)
