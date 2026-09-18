import importlib.util
import json
from pathlib import Path

from _rpm import Version


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / 'plugins/grafana/7.5.17'
SPEC = importlib.util.spec_from_file_location(
    'grafana_init', PLUGIN_DIR / 'init.py'
)
GRAFANA_INIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GRAFANA_INIT)


class Repository:
    def __init__(self, name, version):
        self.name = name
        self.version = Version(version)


def load_seekdb_dashboard():
    with (PLUGIN_DIR / 'seekdb-metrics_rev1.json').open() as dashboard_file:
        return json.load(dashboard_file)


def test_only_seekdb_1_4_and_later_filters_removed_metrics():
    assert not GRAFANA_INIT.should_filter_seekdb_dashboard([])
    assert not GRAFANA_INIT.should_filter_seekdb_dashboard([
        Repository('seekdb', '1.3.9')
    ])
    assert GRAFANA_INIT.should_filter_seekdb_dashboard([
        Repository('seekdb', '1.4.0')
    ])
    assert GRAFANA_INIT.should_filter_seekdb_dashboard([
        Repository('seekdb', '1.5.0')
    ])


def test_filter_removes_panels_that_only_use_removed_seekdb_views():
    dashboard = GRAFANA_INIT.filter_seekdb_dashboard(load_seekdb_dashboard())
    panel_titles = [panel['title'] for panel in dashboard['panels']]

    assert panel_titles == [
        'SQL and Session',
        'Sessions',
        'Cache',
        'Cache Size',
        'Cache Hit Ratio',
    ]
    assert dashboard['version'] == 21


def test_filter_keeps_supported_targets_in_a_mixed_panel():
    dashboard = GRAFANA_INIT.filter_seekdb_dashboard(load_seekdb_dashboard())
    cache_hit_ratio = next(
        panel for panel in dashboard['panels']
        if panel['title'] == 'Cache Hit Ratio'
    )

    assert len(cache_hit_ratio['targets']) == 1
    assert 'seekdb_plan_cache_hit_total' in cache_hit_ratio['targets'][0]['expr']
    for panel in dashboard['panels']:
        for target in panel.get('targets', []):
            assert not any(
                metric in target.get('expr', '')
                for metric in GRAFANA_INIT.SEEKDB_REMOVED_METRICS
            )


def test_filter_removes_empty_rows_and_compacts_dashboard_layout():
    dashboard = GRAFANA_INIT.filter_seekdb_dashboard(load_seekdb_dashboard())
    panels = dashboard['panels']

    assert panels[0]['gridPos'] == {'h': 1, 'w': 24, 'x': 0, 'y': 0}
    assert panels[1]['gridPos'] == {'h': 8, 'w': 24, 'x': 0, 'y': 1}
    assert panels[2]['gridPos'] == {'h': 1, 'w': 24, 'x': 0, 'y': 9}
    assert panels[3]['gridPos'] == {'h': 8, 'w': 12, 'x': 0, 'y': 10}
    assert panels[4]['gridPos'] == {'h': 8, 'w': 12, 'x': 12, 'y': 10}


def test_filtered_dashboard_is_written_without_changing_source(tmp_path):
    source = PLUGIN_DIR / 'seekdb-metrics_rev1.json'
    original = source.read_bytes()

    filtered_path = GRAFANA_INIT.create_filtered_seekdb_dashboard(str(source))
    try:
        with open(filtered_path) as dashboard_file:
            filtered = json.load(dashboard_file)
        assert len(filtered['panels']) == 5
        assert source.read_bytes() == original
    finally:
        Path(filtered_path).unlink()


def test_temporary_dashboard_cleanup_is_idempotent(tmp_path):
    missing_dashboard = tmp_path / 'already-removed.json'

    GRAFANA_INIT._safe_unlink(str(missing_dashboard))
