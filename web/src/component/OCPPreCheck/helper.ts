import { getUnit, takeNewUnit, UNITS } from '@/constant/unit';
import _ from 'lodash';

export const changeParameterUnit = (parameter: any) => {
  let _parameter = _.clone(parameter);
  let unit = getUnit(_parameter.value);
  if (unit && unit.length === 2) {
    _parameter.value = takeNewUnit(
      _parameter.value,
      UNITS[unit.toUpperCase()].alias,
    );
  }
  return _parameter;
};

export const formatPreCheckData = (configData: any) => {
  let _configData = _.cloneDeep(configData);
  let { memory_size } = _configData.components.ocpserver;
  _configData.components.oceanbase.mode = 'PRODUCTION';
  if (typeof memory_size === 'number') {
    _configData.components.ocpserver.memory_size = memory_size + 'G';
  }
  if (
    _configData.components.oceanbase &&
    _configData.components.oceanbase.topology
  ) {
    let { parameters, topology } = _configData.components.oceanbase;
    for (let item of topology) {
      delete item.id;
    }
    for (let idx = 0; idx < parameters.length; idx++) {
      if (
        parameters[idx].key === 'cluster_id' &&
        parameters[idx].value == '0'
      ) {
        parameters.splice(idx, 1);
      }
    }
  }
  for (let key of Object.keys(_configData.components)) {
    let item = _configData.components[key];
    if (item?.parameters?.length) {
      item.parameters = item?.parameters.map((parameter: any) => {
        return {
          key: parameter.key,
          value: parameter.value,
          adaptive: parameter.adaptive,
        };
      });
    }
    if (
      (key === 'oceanbase' || key === 'obproxy') &&
      item.home_path &&
      !item.home_path.split('/').includes(key)
    ) {
      item.home_path += `/${key}`;
    }
    if (
      key === 'ocpserver' &&
      !item.home_path.split('/').includes('ocpserver')
    ) {
      item.home_path += '/ocp';
    }
  }

  if (location.hash.split('/').pop() !== 'install') {
    return {
      ..._configData,
      auth: _configData.auth,
      components: {
        ocpserver: _configData.components.ocpserver,
      },
    };
  }
  return _configData;
};
