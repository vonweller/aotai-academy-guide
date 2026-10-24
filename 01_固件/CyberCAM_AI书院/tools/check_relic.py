# -*- coding: utf-8 -*-
"""Read-only preflight for current candidate data and model schema; never claims accuracy."""
import glob
import os
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, APP)
import config
import relic

ROOT = os.path.abspath(os.path.join(APP, "..", "..", "02_数据", "relics"))
RAW = os.path.join(ROOT, "raw")
engine = relic.RelicEngine()
loaded = engine.prototypes is not None and engine.labels is not None
print("recognition_enabled", bool(getattr(config, "RELIC_RECOGNITION_ENABLED", False)))
print("current_schema_model_loaded", loaded)
print("model_names", engine.names)
for cls in relic.CLASS_ORDER:
    folder = os.path.join(RAW, cls)
    files = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        files.extend(glob.glob(os.path.join(folder, ext)))
    print("%s: %d raw files" % (cls, len(files)))
print("NOTE: counts do not verify provenance, rights, representativeness, or accuracy.")
