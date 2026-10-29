"""Rebuild every data-model deliverable: python tools/data_model/build_all.py

Order matters: model.json first (dump_model), then the workbook, the remap and the dictionary.
Output folder defaults to docs/data_model; override with KRISNNAI_OUT, KRISNNAI_REMAP_OUT, KRISNNAI_DICT_OUT.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
for step in ("dump_model.py", "gen_final.py", "build_remap.py", "build_dictionary.py", "build_sql.py"):
    print("==", step, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, step)], cwd=HERE)
    if r.returncode:
        sys.exit(r.returncode)
print("done")
