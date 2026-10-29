"""Build the self-contained HTML data dictionary from build/model.json and dd_template.html."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "data_model"))
OUT = os.environ.get("KRISNNAI_DICT_OUT") or os.path.join(DOCS, "KrisnnAI-Data-Dictionary.html")
tpl = open(os.path.join(HERE, "dd_template.html"), encoding="utf-8").read()
model = json.load(open(os.path.join(HERE, "build", "model.json"), encoding="utf-8"))
data = json.dumps(model, ensure_ascii=False).replace("<", "\\u003c")
open(OUT, "w", encoding="utf-8").write(tpl.replace("__DATA__", data))
print("saved", OUT)
