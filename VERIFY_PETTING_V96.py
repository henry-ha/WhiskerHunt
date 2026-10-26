"""Lightweight static checks, no claim of native Android compile/test."""
from pathlib import Path
import sys
r=Path(__file__).resolve().parent
source=(r/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
glb=(r/'WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs').read_text()
project=(r/'WhiskerHunt/WhiskerHunt.csproj').read_text()
checks={
    'v3.10.33 and build 96': '<ApplicationDisplayVersion>3.10.33</ApplicationDisplayVersion>' in project and '<ApplicationVersion>96</ApplicationVersion>' in project,
    'tap and stroke gesture handlers': all(x in source for x in ['MotionEventActions.Down', 'MotionEventActions.Move','MotionEventActions.Up','PetAnimal(isStroke: true)', 'PetAnimal(isStroke: false)']),
    'projected GLB bounds': 'TryGetScreenBounds' in glb and 'UpdatePetBounds' in source,
    'pet reaction animation': all(x in glb for x in ['petProgress','swayDegrees','bounce','pulse']),
    'feedback and short hint': '💚 Gentle pat!' in source and 'Stroke to pet 💚' in source,
    'pinch functionality retained': 'AdjustAnimalSize(Math.Clamp(ratio' in source,
    'ARCore placement and capture retained': all(x in source for x in ['TryPlace(frame','PixelCopy.Request','_collect.Click']),
    'source syntax basic balance': source.count('{') == source.count('}') and glb.count('{') == glb.count('}'),
    'GLB models intact (at least 5)': len(list((r/'WhiskerHunt/Resources/Raw/ar_models').glob('*.glb'))) >= 5,
}
for key, result in checks.items(): print(('PASS ' if result else 'FAIL ')+key)
sys.exit(0 if all(checks.values()) else 1)
