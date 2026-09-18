from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCEANBASE_PLUGIN_ROOT = PROJECT_ROOT / 'plugins' / 'oceanbase'


def test_zone_region_default_is_spelled_correctly_for_all_oceanbase_plugins():
    checked = []

    for parameter_file in OCEANBASE_PLUGIN_ROOT.glob('*/parameter.yaml'):
        parameters = yaml.safe_load(parameter_file.read_text())
        zone_region = next(
            (parameter for parameter in parameters if parameter.get('name') == 'zone_region'),
            None,
        )
        if zone_region is None:
            continue

        checked.append(parameter_file.parent.name)
        assert zone_region.get('default') == 'default_region', parameter_file

    assert checked, 'No OceanBase zone_region parameter was found'
