import _ from 'lodash';

type UnitType = {
  text: string;
  alias: string;
  lowerCase: string;
  lowerCaseSimple: string;
};

const UNITS: {
  GB: UnitType;
  MB: UnitType;
  KB: UnitType;
} = {
  GB: {
    alias: 'G',
    text: 'GB',
    lowerCase: 'gb',
    lowerCaseSimple: 'g',
  },
  MB: {
    alias: 'M',
    text: 'MB',
    lowerCase: 'mb',
    lowerCaseSimple: 'm',
  },
  KB: {
    alias: 'K',
    text: 'KB',
    lowerCase: 'kb',
    lowerCaseSimple: 'k',
  },
};

const getAllUnits = () => {
  return _.flatten(
    Object.keys(UNITS).map((key) =>
      Object.keys(UNITS[key]).map((_key) => UNITS[key][_key]),
    ),
  );
};

const getAliasUnits = () => {
  return _.flatten(
    Object.keys(UNITS).map((key) => [
      UNITS[key].alias,
      UNITS[key].lowerCaseSimple,
    ]),
  );
};

/**
 * 将容量单位转换为约定格式 KB、MB、GB,统一输出为大写
 */
const changeUnit = (val: string = 'GB'): string => {
  const res = val.match(/\D+/g)?.[0].toUpperCase() || 'GB';
  if (res.includes('K')) return 'KB';
  if (res.includes('M')) return 'MB';
  if (res.includes('G')) return 'GB';
  return res;
};

//是否携带单位
const isTakeUnit = (val: string | undefined): boolean => {
  if (!val || typeof val !== 'string') return false;
  if (/\d+(\.\d+)?(g|G|m|M|k|K|gb|GB|MB|mb|kb|KB)/.test(val)) {
    return true;
  }
  return false;
};

//获取不携带单位的值
const getNoUnitValue = (val: string | undefined): string => {
  if (!val) return '';
  if (!isTakeUnit(val)) return val;
  for (let unit of getAllUnits()) {
    if (val.includes(unit)) {
      return val.replace(unit, '');
    }
  }
  return '';
};

//获取单位
const getUnit = (value: string) => {
  if (!isTakeUnit(value)) {
    //无单位
    return;
  }
  let valArr = value.split('');
  let tailStr = valArr[valArr.length - 1];
  if (getAliasUnits().includes(tailStr)) {
    return tailStr;
  } else {
    return valArr.splice(-2, 2).join('');
  }
};

/**
 *
 * @param target 待转换值
 * @param unit 需添加上的单位
 * @returns 带上新单位的值
 *
 * etc: takeNewUnit(1GB,MB) => 1MB
 */
const takeNewUnit = (target: string, unit: string): string => {
  if (!isTakeUnit(target)) {
    //无单位
    return target + unit;
  }
  let targetArr = target.split('');

  let tailStr = targetArr[targetArr.length - 1];
  if (getAliasUnits().includes(tailStr)) {
    targetArr[targetArr.length - 1] = unit;
    return targetArr.join('');
  } else {
    //'gb', 'GB', 'MB', 'mb', 'kb', 'KB'
    targetArr.splice(-2, 2, unit);
    return targetArr.join('');
  }
};

export {
  UNITS,
  getAllUnits,
  getAliasUnits,
  changeUnit,
  isTakeUnit,
  takeNewUnit,
  getNoUnitValue,
  getUnit,
};
