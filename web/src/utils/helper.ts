import { intl } from '@/utils/intl'; //与UI无关的函数
import {
  componentVersionTypeToComponent,
  componentsConfig,
} from '@/pages/constants';
import {
  showConfigKeys,
  selectOcpexpressConfig,
} from '@/constant/configuration';
import { message } from 'antd';
import { getNoUnitValue, getUnit } from '@/pages/Obdeploy/ClusterConfig/helper';
import copy from 'copy-to-clipboard';
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
 * @returns
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
    // filter out existing parameters
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
