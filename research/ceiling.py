"""Diagnostic: how many exact seeds can v2.0's features explain if the model is fit on ALL seasons (in-sample ceiling)? Actual field given."""
import numpy as np
from bracketology import history, model, project, fieldformat
from sklearn.ensemble import GradientBoostingClassifier
Y = sorted(history.SELECTION_SUNDAY); allrows = project.training_rows(); m = model.Model().fit(allrows)
fld = [r for r in allrows if r["in_field"]]; sd = m.s_seed
dX, dy = [], []
for y in Y:
    rs = [r for r in fld if r["year"] == y]; Z = sd.transform(model._X(rs, model.SEED))
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            d = rs[i]["ov"] - rs[j]["ov"]
            if d and abs(d) <= 16: dX += [Z[i] - Z[j], Z[j] - Z[i]]; dy += [d < 0, d > 0]
gb = GradientBoostingClassifier(n_estimators=400, max_depth=4, learning_rate=.1, random_state=0).fit(np.array(dX), np.array(dy, int))
for y in Y:
    rs = [r for r in fld if r["year"] == y and r.get("ov")]; slots = fieldformat.format_for(y).slots; Z = sd.transform(model._X(rs, model.SEED))
    def ex(score): o = np.argsort(-np.array(score), kind="stable"); return sum(slots[p] == rs[i]["seed"] for p, i in enumerate(o))
    lin = Z @ m.rank.coef_[0]; nl = [gb.predict_proba(np.array([Z[i] - Z[j] for j in range(len(rs)) if j != i]))[:, 1].mean() for i in range(len(rs))]
    print(y, "in-sample exact: linear", ex(lin), "| deep GBM", ex(nl), "| perfect", len(rs), flush=True)
