//与UI无关的逻辑处理

/**
 * 将容量单位转换为约定格式 KB、MB、GB,统一输出为大写
 */
const getUnit = (val: string = 'GB'): string => {
  const res = val.match(/\D+/g)?.[0].toUpperCase() || 'GB';
  if (res.includes('K')) return 'KB';
  if (res.includes('M')) return 'MB';
  if (res.includes('G')) return 'GB';
  return res;
};

//是否携带单位
const isTakeUnit = (val: string | undefined): boolean => {
  if (!val) return false;
  const upperVal = val.toUpperCase();
  if (
    upperVal.includes('M') ||
    upperVal.includes('MB') ||
    upperVal.includes('K') ||
    upperVal.includes('KB') ||
    upperVal.includes('G') ||
    upperVal.includes('GB')
  ) {
    return true;
  }
  return false;
};

//换新单位
const takeNewUnit = (target: string, unit: string): string => {
  if (!isTakeUnit(target)) {
    //无单位
    return target + unit;
  }
  let targetArr = target.split('');
  let tailStr = targetArr[targetArr.length - 1].toUpperCase();
  if (tailStr === 'K' || tailStr === 'M' || tailStr === 'G') {
    //以K|M|G结尾
    targetArr[targetArr.length - 1] = unit;
    return targetArr.join('');
  } else {
    //以KB|MB|GB结尾
    targetArr.splice(-2, 2, unit);
    return targetArr.join('');
  }
};

export { getUnit, isTakeUnit, takeNewUnit };
