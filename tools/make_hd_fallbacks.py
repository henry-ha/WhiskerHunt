#!/usr/bin/env python3
"""Generate *optional* real 3D fallback meshes from installed HD GLBs.

Never overwrites the HD model. The fallback is a standard (unquantised) glTF 2.0
mesh for the original OpenGL renderer, intended for Filament visibility failures.
Animation/skin data are baked away. Texture detail is retained when Trimesh
can decode the source. Source files and existing fallbacks are not overwritten.

Run from project root: py tools/make_hd_fallbacks.py
Requires: py -m pip install trimesh Pillow numpy
"""
from __future__ import annotations
import io, json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hush_glb_compat import unpack_glb, normalize_webp
SOURCE = ROOT / "WhiskerHunt/Resources/Raw/ar_models"
DEST = ROOT / "WhiskerHunt/Resources/Raw/ar_fallback"

def legacy_compatible(doc):
    if doc.get("extensionsRequired") or doc.get("extensionsUsed") or doc.get("skins"): return False
    access = doc.get("accessors", [])
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4: continue
            attrs=prim.get("attributes", {})
            if "POSITION" not in attrs: return False
            for key in ["POSITION","NORMAL","TEXCOORD_0"]:
                if key in attrs and (attrs[key] >= len(access) or
                                      access[attrs[key]].get("componentType") != 5126):return False
    return True

def main():
    try:
        import trimesh
    except ImportError:
        print("Missing Trimesh: run py -m pip install trimesh pillow numpy")
        return 2
    if not SOURCE.exists():
        print("Run this tool from the Hush Hunt project with installed HD animals.")
        return 2
    DEST.mkdir(parents=True,exist_ok=True)
    results={"converted":[],"already_compatible":[],"skipped":[],"failed":[]}
    for path in sorted(SOURCE.glob("*.glb")):
        try:
            raw=path.read_bytes()
            doc,_=unpack_glb(raw)
            if legacy_compatible(doc):
                results["already_compatible"].append(path.name)
                continue
            destination = DEST / path.name
            if destination.exists():
                results["skipped"].append(path.name+" (existing fallback preserved)")
                continue
            raw,_=normalize_webp(raw)
            scene=trimesh.load(io.BytesIO(raw),file_type="glb",force="scene",process=False)
            count=sum(len(getattr(g,"faces",())) for g in scene.geometry.values())
            if count < 50 or count > 90000:
                raise ValueError(f"geometry out of safe fallback range: {count} triangles")
            fallback=scene.export(file_type="glb")
            candidate,_=unpack_glb(fallback)
            if not legacy_compatible(candidate):
                raise ValueError("exported fallback not compatible with OpenGL renderer")
            if len(fallback)>20*1024*1024:
                raise ValueError("fallback GLB too large")
            destination.write_bytes(fallback)
            results["converted"].append({"name":path.name,"triangles":count,"bytes":len(fallback)})
            print("CREATED standard 3D backup:",path.name, count,"triangles")
        except Exception as exc:
            results["failed"].append({"name":path.name,"reason":str(exc)})
            print("UNCONVERTED",path.name,exc)
    report=ROOT/"HushHunt_Fallback_Conversion_Report.json"
    report.write_text(json.dumps(results,indent=2),encoding="utf-8")
    print("\nResult: {} 3D fallbacks created, {} already compatible, {} need manual attention".format(
        len(results["converted"]),len(results["already_compatible"]),len(results["failed"])))
    print("Report:",report)
    return 0
if __name__=="__main__":raise SystemExit(main())
