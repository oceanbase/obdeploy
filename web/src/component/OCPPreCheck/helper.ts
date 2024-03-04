import { getUnit, takeNewUnit, UNITS } from '@/constant/unit';
import { isExist } from '@/utils/helper';
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
    let { topology } = _configData.components.oceanbase;
    for (let item of topology) {
      delete item.id;
    }
  }
  for (let key of Object.keys(_configData.components)) {
    let item = _configData.components[key];
    if (item?.parameters?.length) {
      for (let i = 0; i < item.parameters.length; i++) {
        const parameter = item.parameters[i];
        if (
          (!parameter.adaptive && !isExist(parameter.value)) ||
          parameter.adaptive ||
          !parameter.isChanged
        ) {
          item.parameters.splice(i--, 1);
        } else {
          item.parameters[i] = {
            key: item.parameters[i].key,
            value: item.parameters[i].value,
            adaptive: item.parameters[i].adaptive,
          };
        }
      }
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
