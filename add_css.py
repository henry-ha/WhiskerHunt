from pathlib import Path
root=Path('/mnt/data/hush_v3111')
ADD=r'''

/* v3.10.11 — theme and camera redesign, overrides supersede legacy camera geometry */
body:has(.hush-immersive-home) .topbar{display:none!important}
body:has(.hush-immersive-home) .view{padding:4px 10px 30px!important}
.hush-story-hero.hush-immersive-home{position:relative;overflow:hidden;isolation:isolate;border-radius:24px!important;min-height:clamp(570px,calc(100dvh - 135px),860px)!important;padding:calc(18px + env(safe-area-inset-top,0px)) 14px 16px!important;display:flex!important;flex-direction:column!important;justify-content:flex-start!important;background:#211b47!important;border:1px solid #ffffff24}
.hush-story-hero.hush-immersive-home::before{content:'';position:absolute;inset:0;background-image:var(--hush-wallpaper)!important;background-position:50% 42%!important;background-size:cover!important;background-repeat:no-repeat!important;opacity:1!important;filter:none!important;z-index:-2}
.hush-story-hero.hush-immersive-home::after{content:'';position:absolute;inset:0;height:auto!important;background:linear-gradient(180deg,#0b0c2799 0%,#15132224 22%,transparent 37%,#0b172011 52%,#06121ccc 70%,#051018f4 100%)!important;z-index:-1;pointer-events:none}
.hush-story-hero.hush-immersive-home.hush-motion::before{animation:hushBreathingScene 18s ease-in-out infinite alternate;transform-origin:50% 48%}
@keyframes hushBreathingScene{0%{transform:scale(1)}100%{transform:scale(1.035)}}
@media(prefers-reduced-motion:reduce){.hush-story-hero.hush-immersive-home.hush-motion::before{animation:none}}
.hush-immersive-home .hush-story-topbar{margin:0!important;min-height:36px!important}
.hush-immersive-home .hush-story-icon{width:42px;height:42px;border-radius:50%;background:#101b339c;border:1px solid #ffffff5d;color:#fff;backdrop-filter:blur(10px)}
.hush-immersive-home .hush-story-brand{margin:0!important;text-align:center;text-shadow:0 2px 10px #080d2399}
.hush-immersive-home .hush-story-brand h1{font-size:clamp(30px,8vw,43px)!important;letter-spacing:-.025em!important;line-height:1.02;margin:0;color:#fff!important}
.hush-immersive-home .hush-story-brand h1 em{font-style:normal;color:var(--hush-theme-accent,#ffa6dd)}
.hush-immersive-home .hush-story-brand p{font-size:10px!important;letter-spacing:.13em!important;margin:6px 0 0;font-weight:900}
.hush-immersive-home .hush-story-paw{display:block;font-size:33px!important;line-height:1.15}
.hush-home-hero-spacer{flex:1 1 auto;min-height:250px}
.hush-home-action-zone{position:relative;z-index:2;display:flex;flex-direction:column;gap:10px}
.hush-theme-tag{background:#141b31aa;border:1px solid #ffffff3b;color:#fff;text-transform:none;font-size:11px;font-weight:800;letter-spacing:.08em;width:max-content;max-width:100%;margin:0 auto 2px;border-radius:99px;padding:6px 13px;backdrop-filter:blur(8px)}
.hush-immersive-home .hush-story-main-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:0!important}
.hush-immersive-home .hush-story-main{border-radius:19px!important;min-height:132px!important;padding:13px 8px 12px!important;justify-content:center;gap:6px!important;backdrop-filter:blur(12px);box-shadow:0 8px 25px #0007,inset 0 1px 0 #ffffff5c;border:1.5px solid #ffffff6b!important}
.hush-immersive-home .hush-story-main-live{background:linear-gradient(160deg,color-mix(in srgb,var(--hush-live) 92%,#062a22),color-mix(in srgb,var(--hush-live) 65%,#0a1b29))!important}
.hush-immersive-home .hush-story-main-ar{background:linear-gradient(160deg,color-mix(in srgb,var(--hush-ar) 94%,#0a255c),color-mix(in srgb,var(--hush-ar) 61%,#08172a))!important}
.hush-immersive-home .hush-story-main .emoji{font-size:30px!important}
.hush-immersive-home .hush-story-main strong{font-size:16px!important}
.hush-immersive-home .hush-story-main small{font-size:12px!important;color:#e7f6ff}
.hush-immersive-home .hush-story-mini-actions{margin:0!important;gap:8px!important}
.hush-immersive-home .hush-story-mini{background:#16223cbd!important;border:1px solid #ffffff4a;min-height:62px!important;padding:8px 4px!important;gap:5px!important;border-radius:15px!important;backdrop-filter:blur(12px)}
.hush-immersive-home .hush-story-mini span{font-size:20px!important}
.hush-immersive-home .hush-story-mini strong{font-size:11px!important;color:#fff}
.hush-story-home .hush-story-stats{margin:0!important;padding:0!important}
.hush-story-home .hush-story-stats>div{padding:8px!important}
.hush-story-home .hush-story-stats strong{font-size:18px}
.hush-story-home .hush-release-caption{color:#9ca6ca}
@media(max-height:750px){.hush-story-hero.hush-immersive-home{min-height:510px!important}.hush-home-hero-spacer{min-height:195px}.hush-immersive-home .hush-story-main{min-height:110px!important}}

.hush-theme-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:12px 0}
.hush-theme-choice{border:2px solid #566075;border-radius:15px;padding:4px;background:#192c3b;color:#edf9fb;text-align:center;overflow:hidden;display:flex;flex-direction:column;gap:5px}
.hush-theme-choice.active{border-color:#a0f4e3;box-shadow:0 0 0 1px #a0f4e3}
.hush-theme-choice img{display:block;width:100%;aspect-ratio:.8;object-fit:cover;border-radius:10px}
.hush-theme-choice span{font-weight:750;font-size:11px;line-height:1.3;padding:0 1px 6px}
.hush-theme-mode{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.hush-theme-mode button.active{color:#082c2b;background:#a6f3e2;border-color:#a6f3e2}
.hush-theme-sheet{padding-bottom:calc(28px + env(safe-area-inset-bottom,18px))!important}

.visual-change,#change-species{white-space:nowrap!important;min-width:max-content!important;width:auto!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;font-size:12px!important;line-height:1!important;padding:12px 10px!important;gap:5px}
.species-picker .visual-field-heading{align-items:center;gap:10px}
.species-picker .visual-field-heading h3{font-size:17px!important}
.hush-other-tile .field-guide-figure{background:#1c5660}
.field-guide-tile .field-guide-figure img{display:block;object-fit:cover!important}

.hush-mystery-help{font-size:12px;line-height:1.45;color:#344c5d;background:#f1f8f5;border-radius:12px;padding:10px;margin:13px 0 0}
.sheet.identified-sheet .hush-identified-hero,.sheet.identified-sheet .hush-identified-hero img{min-height:0!important;height:190px!important}
.sheet.identified-sheet .hush-identified-card{padding:15px 14px!important}
.sheet.identified-sheet .hush-identified-header h3{font-size:23px!important}
.sheet.identified-sheet .hush-identified-panel{margin:5px 12px 12px!important}
.sheet.identified-sheet .whisker-build-stamp{display:none!important}
.sheet.identified-sheet .sheet-head{padding:8px 12px 0!important}

/* Keep Live Capture INSIDE Android status and navigation bars; camera preview is full usable viewport. */
.modal-layer:has(.hush-camera-clean){align-items:flex-start!important;overflow:hidden!important}
.modal-layer .sheet.live-sheet.hush-camera-clean{
 --hush-top-safe:max(env(safe-area-inset-top,0px),35px);
 --hush-bottom-safe:max(env(safe-area-inset-bottom,0px),26px);
 position:relative!important;margin-top:var(--hush-top-safe)!important;margin-bottom:var(--hush-bottom-safe)!important;
 height:calc(100dvh - var(--hush-top-safe) - var(--hush-bottom-safe))!important;
 min-height:0!important;max-height:none!important;padding:0!important;overflow:hidden!important;
 background:#0b1420!important;border-radius:0!important
}
.sheet.live-sheet.hush-camera-clean .encounter-stage{height:100%!important;min-height:0!important;border-radius:0!important;margin:0!important}
.sheet.live-sheet.hush-camera-clean .encounter-backdrop,.sheet.live-sheet.hush-camera-clean .encounter-live-video{height:100%!important;min-height:0!important;width:100%!important;object-fit:cover!important}
.sheet.live-sheet.hush-camera-clean .sheet-head{top:8px!important;left:10px!important;right:10px!important;min-height:49px;padding:11px 54px!important;z-index:19!important;border-radius:18px!important;align-items:center;background:#071a2db3!important}
.sheet.live-sheet.hush-camera-clean .sheet-head h2{font-size:18px!important}
.sheet.live-sheet.hush-camera-clean .sheet-head .close-btn{top:6px!important;left:6px!important}
.sheet.live-sheet.hush-camera-clean .whisker-build-stamp{display:none!important}
.sheet.live-sheet.hush-camera-clean .encounter-quick-help,.sheet.live-sheet.hush-camera-clean .encounter-help,.sheet.live-sheet.hush-camera-clean .encounter-launch,.sheet.live-sheet.hush-camera-clean .encounter-quality,.sheet.live-sheet.hush-camera-clean .encounter-status,.sheet.live-sheet.hush-camera-clean .encounter-photo-actions,.sheet.live-sheet.hush-camera-clean .encounter-capture-tag,.sheet.live-sheet.hush-camera-clean .encounter-cat,.sheet.live-sheet.hush-camera-clean .encounter-tool-dock,.sheet.live-sheet.hush-camera-clean .actions,.sheet.live-sheet.hush-camera-clean .hush-pinch-hint{display:none!important}
.sheet.live-sheet.hush-camera-clean .hush-live-zoom{position:absolute!important;top:auto!important;bottom:112px!important;left:50%!important;transform:translateX(-50%)!important;z-index:24!important;max-width:calc(100% - 14px)!important;background:#061a28dc!important;padding:7px!important;border-radius:999px!important;white-space:nowrap!important}
.sheet.live-sheet.hush-camera-clean .hush-quick-shutter{position:absolute!important;top:auto!important;bottom:18px!important;left:50%!important;right:auto!important;transform:translateX(-50%)!important;z-index:23!important;width:80px!important;height:80px!important;border-radius:50%!important;background:#fff!important;border:5px solid #ffffff66!important}
.sheet.live-sheet.hush-camera-clean .hush-quick-shutter span{width:60px!important;height:60px!important;background:#f3f9ff!important;color:#f3f9ff!important;border:3px solid #0e1b33!important}
.sheet.live-sheet.hush-camera-clean .hush-game-toggle{position:absolute;z-index:23;right:12px;bottom:27px;min-height:54px;border-radius:15px;border:1px solid #ffffff62;color:#fff;background:#092339d9;font-weight:900;padding:10px 12px;backdrop-filter:blur(10px)}
.sheet.live-sheet.hush-camera-clean.hush-game-open .encounter-cat{display:block!important}
.sheet.live-sheet.hush-camera-clean.hush-game-open .encounter-tool-dock{display:flex!important;left:50%!important;right:auto!important;bottom:185px!important;top:auto!important;transform:translateX(-50%)!important;width:max-content!important;height:auto!important;min-height:0!important;flex-direction:row!important;align-items:center!important;gap:7px!important;padding:7px!important;border-radius:18px!important;background:#08192ad5!important}
.sheet.live-sheet.hush-camera-clean.hush-game-open .encounter-status{display:block!important;bottom:278px!important;left:12px!important;right:12px!important;top:auto!important;font-size:12px!important;padding:8px!important}
.sheet.live-sheet.hush-camera-clean.hush-game-open .actions:has(#encounter-continue:not(.hidden)){display:flex!important;position:absolute;bottom:15px!important;left:10px!important;right:10px!important;z-index:25!important}
@media(max-height:680px){.sheet.live-sheet.hush-camera-clean .hush-live-zoom{bottom:98px!important}.sheet.live-sheet.hush-camera-clean .hush-quick-shutter{bottom:9px!important;width:74px!important;height:74px!important}.sheet.live-sheet.hush-camera-clean.hush-game-open .encounter-tool-dock{bottom:165px!important}}
'''
for folder in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
 p=folder/'style_v73.css';css=p.read_text()+ADD
 (folder/'style_v74.css').write_text(css)
 (folder/'style.css').write_text(css)
 p.unlink()
print('CSS added')
