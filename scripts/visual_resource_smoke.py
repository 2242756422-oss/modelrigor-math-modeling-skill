#!/usr/bin/env python3
"""Discover read-only plot_style, or exercise native Matplotlib without it."""
import argparse
import csv
import importlib.util
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

from core import sha256

p = argparse.ArgumentParser()
p.add_argument("--resource-root", type=Path)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
style_path = (a.resource_root or Path(__file__).resolve().parents[2]/'cumcm-step-review') / "scripts" / "plot_style.py"
mod=None; unavailable='optional plot_style resource not found'
if style_path.is_file():
    try:
        spec = importlib.util.spec_from_file_location("legacy_plot_style_readonly", style_path)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        if not all(callable(getattr(mod,k,None)) for k in ('apply_publication_style','publication_subplots','export_figure')):
            raise AttributeError('required plot_style interface unavailable')
    except (ImportError,AttributeError) as e:
        mod=None; unavailable=str(e)
fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "visual_real.csv"
with fixture.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
x = [float(r["x"]) for r in rows]
obs = [float(r["observation"]) for r in rows]
model = [float(r["model"]) for r in rows]
if mod:
    style = mod.apply_publication_style(journal="okabe-ito", lang="en", width="cumcm")
    fig, ax = mod.publication_subplots(width="cumcm", aspect=0.66)
else:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style={'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'}
    plt.rcParams.update(style)
    fig,ax=plt.subplots(figsize=(160/25.4,105/25.4))
ax.plot(x, model, color="#D55E00", label="Model", linewidth=1.4)
ax.scatter(x, obs, color="#4C78A8", label="Observation", s=24)
ax.set(xlabel="Index", ylabel="Response")
ax.legend(frameon=False)
a.out.mkdir(parents=True, exist_ok=True)
if mod:
    outputs = mod.export_figure(fig, a.out / "resource_smoke", dpi=300, svg=True, grayscale_preview=True, strict_layout=True, strict_design=True)
else:
    fig.tight_layout(); outputs={}
    for suffix in ('png','svg'):
        file=a.out/('resource_smoke.'+suffix); fig.savefig(file,dpi=300); outputs[suffix]=str(file)
    from PIL import Image
    preview=a.out/'resource_smoke_gray.png'
    with Image.open(outputs['png']) as im: im.convert('L').save(preview)
    outputs['gray']=str(preview)
record = {
    "capability_id": "legacy.plot_style.production_api" if mod else 'native.matplotlib',
    "resource_path": str(style_path) if mod else None, "source_sha256": sha256(style_path) if mod else None,
    "actual_interface": "apply_publication_style + publication_subplots + export_figure" if mod else 'Figure/Axes + savefig',
    'fallback_reason':None if mod else unavailable,
    "fixture": str(fixture), "fixture_sha256": sha256(fixture),
    "outputs": {k: {"path": v, "sha256": sha256(Path(v))} for k, v in outputs.items()},
    "style_keys": sorted(style.keys()), "status": "PASS"
}
(a.out / "resource_consumption_smoke.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("VISUAL RESOURCE SMOKE PASS")
if not mod: print('OPTIONAL LEGACY RESOURCE UNAVAILABLE; NATIVE MATPLOTLIB FALLBACK EXERCISED (not scientific visual certification)')
