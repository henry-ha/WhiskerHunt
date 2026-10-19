from pathlib import Path

ROOT = Path('/mnt/data/work_v33')
APP = (ROOT / 'BrowserPreview' / 'app.js').read_text()
CSS = (ROOT / 'BrowserPreview' / 'style.css').read_text()


def test_build_bumped():
    assert "WHISKER_BUILD='3.4.0'" in APP
    assert 'WHISKER_BUILD_NUMBER=36' in APP


def test_location_helper_present():
    assert 'function wireLocationOptIn(prefix,checkboxId)' in APP
    assert 'case "app-settings"' in (ROOT / 'WhiskerHunt' / 'MainPage.xaml.cs').read_text()
    assert 'id="pin-helper"' in APP
    assert 'id="virtual-pin-helper"' in APP


def test_catalog_is_over_120_and_weighted():
    assert 'return out.slice(0,128)' in APP
    assert 'function rarityWeight(rarity)' in APP
    assert 'legendary' in APP


def test_claws_animate_and_realish_cats_added():
    assert '.paw-claw' in CSS
    assert '#encounter-orb.grab-2 .claw-1' in CSS
    assert 'ar-cat-realish' in APP
