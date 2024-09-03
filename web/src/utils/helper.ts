import {
  PARAMETER_TYPE,
  selectOcpexpressConfig,
  showConfigKeys,
} from '@/constant/configuration';
import { getNoUnitValue, getUnit } from '@/constant/unit';
import {
  componentsConfig,
  componentVersionTypeToComponent,
} from '@/pages/constants';
import { intl } from '@/utils/intl'; //与UI无关的函数
import { message } from 'antd';
import copy from 'copy-to-clipboard';
import { clone } from 'lodash';
import { generateRandomPassword as oldGenerateRandomPassword } from '.';
// 不用navigator.clipboard.writeText的原因：该接口需要在HTTPS环境下才能使用
export function copyText(text: string) {
  let inputDom = document.createElement('input');
  inputDom.setAttribute('type', 'text');
  inputDom.value = text;
  //需要将元素添加到文档中去才可以跟文档结构中的其他元素交互
  document.body.appendChild(inputDom);
  inputDom.select();
  //返回false则浏览器不支持该api
  let res = document.execCommand('copy');
  document.body.removeChild(inputDom);
  return res;
}
export function getTailPath() {
  return location.hash.split('/').pop()?.split('?')[0];
}

/**
 *
 * @param dataSource 需要格式化的源数据
 * @param isSelectOcpexpress 是否选中/包含ocpexpress组件
 * 筛选需要展示到页面的参数
 */
export const formatMoreConfig = (
  dataSource: API.ParameterMeta[],
  isSelectOcpexpress = true,
) => {
  return dataSource.map((item) => {
    const component = componentVersionTypeToComponent[item.component]
      ? componentVersionTypeToComponent[item.component]
      : item.component;
    const componentConfig = componentsConfig[component];

    let configParameter = item?.config_parameters.filter((parameter) => {
      let configKeys = { ...showConfigKeys };
      if (!isSelectOcpexpress) {
        configKeys.oceanbase = [
          ...configKeys.oceanbase,
          ...selectOcpexpressConfig,
        ];
      }
      return !configKeys?.[componentConfig.componentKey]?.includes(
        parameter.name,
      );
    });

    const newConfigParameter: API.NewConfigParameter[] = configParameter.map(
      (parameterItem) => {
        let parameterValue: any;
        if (parameterItem.name === 'cluster_id') parameterItem.default = '0';
        parameterValue = {
          value: parameterItem.default,
          defaultValue: getNoUnitValue(parameterItem.default),
          adaptive: parameterItem.auto,
          auto: parameterItem.auto,
          require: parameterItem.require,
          isChanged: parameterItem.is_changed,
          unitDisable: parameterItem.unitDisable,
        };
        if (
          parameterItem.type === 'CapacityMB' ||
          parameterItem.type === 'Capacity'
        ) {
          parameterValue = {
            ...parameterValue,
            defaultUnit: getUnit(parameterItem.default),
          };
        }
        return {
          ...parameterItem,
          parameterValue,
        };
      },
    );

    const result: API.NewParameterMeta = {
      ...item,
      componentKey: componentConfig.componentKey,
      label: componentConfig.labelName,
      configParameter: newConfigParameter,
    };
    result.configParameter.forEach((item) => {
      Object.assign(item.parameterValue, { type: item.type });
    });
    return result;
  });
};

/**
 * 获取server
 */
export const getAllServers = (dataSource: API.DBConfig[]) => {
  const allServersList = dataSource.map((item) => item.servers);
  let newAllOBServer: string[] = [];
  allServersList.forEach((item) => {
    if (item && item.length) {
      newAllOBServer = [...newAllOBServer, ...item];
    }
  });
  return newAllOBServer;
};

export const handleCopy = (content: string) => {
  copy(content);
  message.success(
    intl.formatMessage({
      id: 'OBD.src.utils.helper.CopiedSuccessfully',
      defaultMessage: '复制成功',
    }),
  );
};

export const SPECIAL_SYMBOLS_OB = '~!@#%^&*_-+=|(){}[]:;,.?/';
// export const SPECIAL_SYMBOLS_OCP = '~!@#%^&*_-+=|(){}[]:;,.?/$`\'"<>';
export const SPECIAL_SYMBOLS_OCP = '~^*{}[]_-+';
const SPECIAL_SYMBOLS_REG_OB = /^[~!@#%^&*()_+\-=|{}\:[\];,.?\/]+$/;
export const SPECIAL_SYMBOLS_REG_OCP = /^[~^*{}[\]_\-+]+$/;
// const SPECIAL_SYMBOLS_REG_OCP = /^[~!@#%^&*()_\-+=|:{}[\];,.<>?\/$`'"\\]+$/;
const REG_NUMBER = /^[0-9]$/;
const REG_LOWER_CASE = /^[a-z]$/;
const REG_UPPER_CASE = /^[A-Z]$/;

export const passwordRangeCheck = (password: string, useFor: 'ob' | 'ocp') => {
  if (!password) return false;
  const passwordChar = password.split('');
  const SPECIAL_SYMBOLS_REG =
    useFor === 'ob' ? SPECIAL_SYMBOLS_REG_OB : SPECIAL_SYMBOLS_REG_OCP;
  //检验内容是否超出范围
  for (let char of passwordChar) {
    if (
      !SPECIAL_SYMBOLS_REG.test(char) &&
      !REG_NUMBER.test(char) &&
      !REG_LOWER_CASE.test(char) &&
      !REG_UPPER_CASE.test(char)
    ) {
      return false;
    }
  }
  return true;
};

export const passwordSymbolsCheck = (
  password: string,
  useFor: 'ob' | 'ocp',
) => {
  let passwordChar = password.split(''),
    haveSymbols = false,
    haveNumber = false,
    haveLowerCase = false,
    haveUpperCaseReg = false;
  const SPECIAL_SYMBOLS_REG =
    useFor === 'ob' ? SPECIAL_SYMBOLS_REG_OB : SPECIAL_SYMBOLS_REG_OCP;

  for (let char of passwordChar) {
    if (SPECIAL_SYMBOLS_REG.test(char)) {
      haveSymbols = true;
    }
    if (REG_NUMBER.test(char)) {
      haveNumber = true;
    }
    if (REG_LOWER_CASE.test(char)) {
      haveLowerCase = true;
    }
    if (REG_UPPER_CASE.test(char)) {
      haveUpperCaseReg = true;
    }
  }
  if (
    [haveSymbols, haveNumber, haveLowerCase, haveUpperCaseReg].filter(
      (val) => val === true,
    ).length < 3
  ) {
    return false;
  }
  return true;
};

/**
 *
 * @param str 待校验密码
 * @param type 校验类型 ob | ocp
 * @returns Boolean 是否通过校验
 */
export const passwordCheck = (str: string, type: 'ob' | 'ocp') => {
  const SPECIAL_SYMBOLS_REG =
    type === 'ob' ? SPECIAL_SYMBOLS_REG_OB : SPECIAL_SYMBOLS_REG_OCP;
  let strArr = str.split(''),
    haveSymbols = false,
    haveNumber = false,
    haveLowerCase = false,
    haveUpperCaseReg = false;
  if (typeof str !== 'string') {
    throw new Error('type error');
  }

  //检验长度
  if (str.length < 8 || str.length > 32) {
    return false;
  }
  //检验内容是否超出范围
  for (let str of strArr) {
    if (
      !SPECIAL_SYMBOLS_REG.test(str) &&
      !REG_NUMBER.test(str) &&
      !REG_LOWER_CASE.test(str) &&
      !REG_UPPER_CASE.test(str)
    ) {
      return false;
    }
  }
  for (let str of strArr) {
    if (SPECIAL_SYMBOLS_REG.test(str)) {
      haveSymbols = true;
    }
    if (REG_NUMBER.test(str)) {
      haveNumber = true;
    }
    if (REG_LOWER_CASE.test(str)) {
      haveLowerCase = true;
    }
    if (REG_UPPER_CASE.test(str)) {
      haveUpperCaseReg = true;
    }
  }
  if (
    [haveSymbols, haveNumber, haveLowerCase, haveUpperCaseReg].filter(
      (val) => val === true,
    ).length < 3
  ) {
    return false;
  }
  return true;
};

export const passwordCheckLowVersion = (pwd: string) => {
  let strArr = pwd.split(''),
    symbolsCount = 0,
    numberCount = 0,
    lowerCaseCount = 0,
    upperCaseCount = 0;
  if (typeof pwd !== 'string') {
    throw new Error('type error');
  }

  //检验长度
  if (pwd.length < 8 || pwd.length > 32) {
    return false;
  }

  //检验内容是否超出范围
  for (let str of strArr) {
    if (
      !SPECIAL_SYMBOLS_REG_OCP.test(str) &&
      !REG_NUMBER.test(str) &&
      !REG_LOWER_CASE.test(str) &&
      !REG_UPPER_CASE.test(str)
    ) {
      return false;
    }
  }
  for (let str of strArr) {
    if (SPECIAL_SYMBOLS_REG_OCP.test(str)) {
      symbolsCount += 1;
    }
    if (REG_NUMBER.test(str)) {
      numberCount += 1;
    }
    if (REG_LOWER_CASE.test(str)) {
      lowerCaseCount += 1;
    }
    if (REG_UPPER_CASE.test(str)) {
      upperCaseCount += 1;
    }
  }
  // 是否每种类型都有且数量大于等于2
  if (
    [symbolsCount, numberCount, lowerCaseCount, upperCaseCount].filter(
      (count) => count >= 2,
    ).length !== 4
  ) {
    return false;
  }
  return true;
};

export function generateRandomPassword(
  type: 'ob' | 'ocp',
  useOldRuler?: boolean,
) {
  if (useOldRuler) {
    return oldGenerateRandomPassword();
  }

  const length = Math.floor(Math.random() * 25) + 8; // 生成8到32之间的随机长度
  const characters =
    type === 'ob'
      ? `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789${SPECIAL_SYMBOLS_OB}`
      : `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789${SPECIAL_SYMBOLS_OCP}`;

  let password = '';
  let haveUppercase = false;
  let havetLowercase = false;
  let haveNumber = false;
  let haveSpecialChar = false;

  // 生成随机密码
  for (let i = 0; i < length; i++) {
    const randomIndex = Math.floor(Math.random() * characters.length);
    const randomChar = characters[randomIndex];
    password += randomChar;

    // 判断字符类型并增加相应计数器
    if (/[A-Z]/.test(randomChar)) {
      haveUppercase = true;
    } else if (/[a-z]/.test(randomChar)) {
      havetLowercase = true;
    } else if (/[0-9]/.test(randomChar)) {
      haveNumber = true;
    } else {
      haveSpecialChar = true;
    }
  }

  // 检查计数器是否满足要求
  if (
    [haveSpecialChar, haveNumber, havetLowercase, haveUppercase].filter(
      (val) => val === true,
    ).length < 3
  ) {
    return generateRandomPassword(type); // 重新生成密码
  }

  return password;
}
export const OB_PASSWORD_ERROR_REASON = intl.formatMessage({
  id: 'OBD.src.utils.helper.TheLengthIsToAnd.2',
  defaultMessage:
    '长度8~32  且至少包含 大写字母、小写字母、数字和特殊字符 ~!@#%^&*_-+=|(){}[]:;,.?/ 中的三种',
});
export const OCP_PASSWORD_ERROR_REASON = intl.formatMessage({
  id: 'OBD.src.utils.helper.TheLengthIsToAnd.3',
  defaultMessage:
    '长度8~32  且至少包含 大写字母、小写字母、数字和特殊字符 ~^*{}[]_-+ 中的三种',
});

// ocp版本小于422部分密码采用老版本校验规则
export const OCP_PASSWORD_ERROR_REASON_OLD = intl.formatMessage({
  id: 'OBD.src.utils.helper.ItIsToCharactersIn',
  defaultMessage:
    '长度为 8~32 个字符，支持字母、数字和特殊字符，且至少包含大、小写字母、数字和特殊字符各 2 个，支持的特殊字符为~^*{}[]_-+',
});

export const getPasswordRules = (useFor: 'ob' | 'ocp') => [
  {
    required: true,
    message: intl.formatMessage({
      id: 'OBD.src.utils.EnterAPassword',
      defaultMessage: '请输入密码',
    }),
  },
  () => ({
    validator(_: any, originValue: string | API.ParameterValue) {
      let value =
        typeof originValue === 'object' ? originValue.value! : originValue;
      const REASON =
        useFor === 'ob' ? OB_PASSWORD_ERROR_REASON : OCP_PASSWORD_ERROR_REASON;
      if (!passwordCheck(value, useFor)) {
        return Promise.reject(new Error(REASON));
      }
      return Promise.resolve();
    },
  }),
];

/**
 * 判断一个字符串或者数字是否有值,避免判断 0 为 false
 */
export const isExist = (val: string | number | undefined): boolean => {
  if (typeof val === 'number') return true;
  return !!val;
};

/**
 *  当检测到系统中存在失败历史信息，重新部署时；
 *  给历史数据的组件参数添加 isChanged 字段
 */
export const formatConfigData = (configData: any) => {
  let _config = clone(configData);
  Object.keys(_config?.components).forEach((compKey) => {
    _config?.components[compKey]?.parameters?.forEach((parameter: any) => {
      parameter.isChanged = true;
    });
  });
  return _config;
};

export const getInitialParameters = (
  currentComponent: string,
  dataSource: API.MoreParameter[],
  data: API.NewParameterMeta[],
) => {
  const currentComponentNameConfig = data?.filter(
    (item) => item.component === currentComponent,
  )?.[0];
  if (currentComponentNameConfig) {
    const parameters: any = {};
    currentComponentNameConfig.configParameter.forEach((item) => {
      let parameter = {
        ...item,
        key: item.name,
        params: {
          value: item.default,
          adaptive: item.auto,
          auto: item.auto,
          require: item.require,
          type: item.type,
          isChanged: item.is_changed,
          unitDisable: item?.unitDisable,
        },
      };
      dataSource?.some((dataItem) => {
        if (item.name === dataItem.key) {
          parameter = {
            key: dataItem.key,
            description: parameter.description,
            params: {
              ...parameter.params,
              ...dataItem,
            },
          };
          return true;
        }
        return false;
      });
      if (
        (parameter.params.type === PARAMETER_TYPE.capacity ||
          parameter.params.type === PARAMETER_TYPE.capacityMB) &&
        parameter.params.value == '0'
      ) {
        parameter.params.value += 'GB';
      }
      parameters[item.name] = parameter;
    });
    return parameters;
  } else {
    return undefined;
  }
};

export const getQueryFromComps = (comps: string[]) => {
  return comps
    .reduce((pre, cur) => pre + `components=${cur}&`, '')
    .slice(0, -1);
};
/**
 * abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
 * 从这些字符里面随机取10个
 */
export const generatePwd = () => {
  const allLetters =
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let pwd = '';
  for (let i = 0; i < 10; i++) {
    const randomIdx = Math.floor(Math.random() * (allLetters.length - 1));
    pwd += allLetters[randomIdx];
  }
  return pwd;
};

export const generateComplexPwd = (
  lowercaseLength = 2,
  uppercaseLength = 2,
  digitsLength = 2,
  punctuationLength = 2,
  punctuationChars = '(._+@#%)',
) => {
  let pwd = '';
  const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const digits = '0123456789';
  const punctuation = punctuationChars;

  for (let i = 0; i < lowercaseLength; i++) {
    pwd += lowercase.charAt(Math.floor(Math.random() * lowercase.length));
  }
  for (let i = 0; i < uppercaseLength; i++) {
    pwd += uppercase.charAt(Math.floor(Math.random() * uppercase.length));
  }
  for (let i = 0; i < digitsLength; i++) {
    pwd += digits.charAt(Math.floor(Math.random() * digits.length));
  }
  for (let i = 0; i < punctuationLength; i++) {
    pwd += punctuation.charAt(Math.floor(Math.random() * punctuation.length));
  }

  let pwdArray = pwd.split('');
  for (let i = pwdArray.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pwdArray[i], pwdArray[j]] = [pwdArray[j], pwdArray[i]];
  }

  return pwdArray.join('');
};

const insertPwd = (url: string, pwd: string) => {
  const urlArr = url.split(' ');
  for (let i = 0; i < urlArr.length; i++) {
    if (urlArr[i].includes('-u')) {
      urlArr.splice(i + 1, 0, `-p'${pwd}'`);
      break;
    }
  }
  return urlArr.reduce((pre, cur) => pre + ' ' + cur);
};
export const connectInfoForPwd = (
  connectInfo: API.ConnectionInfo[],
  components: any = {},
) => {
  connectInfo?.forEach((item) => {
    if (item.component === 'oceanbase-ce' && components.oceanbase) {
      item.password = components.oceanbase?.root_password;
      item.connect_url = insertPwd(item.connect_url, item.password);
    }
    if (item.component === 'obproxy-ce') {
      if (components.obproxy.obproxy_sys_password) {
        item.password = components.obproxy.obproxy_sys_password;
      } else {
        item.password = components.obproxy?.parameters?.find(
          (item) => item.key === 'obproxy_sys_password',
        )?.value;
      }
      item.connect_url = insertPwd(item.connect_url, item.password);
    }
    if (item.component === 'ocp-express' && components.ocpexpress) {
      item.password = components.ocpexpress?.admin_passwd;
    }
  });
  return connectInfo;
};
