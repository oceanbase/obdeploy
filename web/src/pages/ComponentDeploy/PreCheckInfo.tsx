import CustomFooter from '@/component/CustomFooter';
import {
  CompDetailCheckInfo,
  CompNodeCheckInfo,
  DeployedCompCheckInfo,
  PathCheckInfo,
  UserCheckInfo,
} from '@/component/PreCheckComps';
import { componentChangeConfig } from '@/services/component-change/componentChange';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import { getErrorInfo, handleQuit } from '@/utils';
import { generateComplexPwd, generatePwd } from '@/utils/helper';
import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { getLocale, useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import { Alert, Button, Row, Space } from 'antd';
import { useEffect } from 'react';
import { ExclamationCircleFilled } from '@ant-design/icons';
import {
  allComponentsKeys,
  componentsConfig,
  componentVersionTypeToComponent,
  configServerComponent,
  configServerComponentKey,
  obagentComponent,
  obproxyComponent,
  ocpexpressComponent,
  ocpexpressComponentKey,
  onlyComponentsKeys,
} from '../constants';
import { formatConfigData as handleConfigData } from '../Obdeploy/CheckInfo';
import { DeployedUserTitle } from './ComponentConfig';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
interface ComponentsNodeConfig {
  name: string;
  servers: string[];
  key: string;
  isTooltip: boolean;
}
const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export const formatConfigData = async (componentConfig: any) => {
  const newConfig = { mode: 'add_component', ...componentConfig };
  const { data: publicKey } = await getPublicKey();
  delete newConfig.appname;
  delete newConfig.deployUser;
  return handleConfigData(newConfig, null, publicKey);
};

export default function PreCheckInfo() {
  const {
    componentConfig,
    setComponentConfig,
    selectedConfig,
    lowVersion,
    current,
    setCurrent,
    setPreCheckInfoOk,
  } = useModel('componentDeploy');
  const { handleQuitProgress, setErrorVisible, setErrorsList, errorsList } =
    useModel('global');
  const {
    obproxy = {},
    ocpexpress = {},
    obagent = {},
    obconfigserver = {},
    home_path,
    deployUser,
  } = componentConfig;
  const components = {
    obproxy,
    ocpexpress,
    obagent,
    obconfigserver,
  };

  const { run: handleCreateConfig, loading } = useRequest(
    componentChangeConfig,
    {
      manual: true,
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          setPreCheckInfoOk(true);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const getComponentsList = () => {
    const componentsList: API.TableComponentInfo[] = [];
    allComponentsKeys.forEach((key) => {
      if (components?.[key]) {
        const component = componentsConfig?.[key] || {};
        componentsList.push({
          ...component,
          version: components?.[key].version,
          key,
        });
      }
    });
    return componentsList.filter((item) =>
      selectedConfig.some(
        (selectedComp) =>
          item.key === componentVersionTypeToComponent[selectedComp] ||
          item.key === selectedComp,
      ),
    );
  };
  const getComponentsNodeConfigList = () => {
    const componentsNodeConfigList: ComponentsNodeConfig[] = [];
    const tempSelectedConfig = selectedConfig.map(
      (item) => componentVersionTypeToComponent[item] || item,
    );

    let currentOnlyComponentsKeys = onlyComponentsKeys.filter(
      (key) => key !== 'obagent' && tempSelectedConfig.includes(key),
    );

    if (lowVersion) {
      currentOnlyComponentsKeys = currentOnlyComponentsKeys.filter(
        (key) => key !== 'ocpexpress',
      );
    }

    currentOnlyComponentsKeys.forEach((key) => {
      if (componentsConfig?.[key]) {
        componentsNodeConfigList.push({
          key,
          name: componentsConfig?.[key]?.name,
          servers: components?.[key]?.servers?.join('，'),
          isTooltip: key === obproxyComponent,
        });
      }
    });
    return componentsNodeConfigList;
  };
  const preStep = () => {
    setCurrent(current - 1);
  };

  const handlePreCheck = async () => {
    handleCreateConfig(
      { name: componentConfig?.appname },
      await formatConfigData(componentConfig),
    );
  };

  const componentsList = getComponentsList();
  const componentsNodeConfigList = getComponentsNodeConfigList();
  const clusterConfigInfo = [];
  if (selectedConfig.length) {
    let content: any[] = [],
      more: any = [];
    if (
      selectedConfig.includes(obproxyComponent) ||
      selectedConfig.includes('obproxy-ce')
    ) {
      content = content.concat(
        {
          label: intl.formatMessage({
            id: 'OBD.pages.Obdeploy.CheckInfo.PortObproxySql',
            defaultMessage: 'OBProxy SQL端口',
          }),
          value: obproxy?.listen_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.PortObproxyExporter',
            defaultMessage: 'OBProxy Exporter 端口',
          }),
          value: obproxy?.prometheus_listen_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.Obdeploy.CheckInfo.PortObproxyRpc',
            defaultMessage: 'OBProxy RPC 端口',
          }),
          value: obproxy?.rpc_listen_port,
        },
      );
      obproxy?.parameters?.length &&
        more.push({
          label: componentsConfig[obproxyComponent].labelName,
          parameters: obproxy?.parameters,
        });
    }
    if (selectedConfig.includes(obagentComponent)) {
      content = content.concat(
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ObagentMonitoringServicePort',
            defaultMessage: 'OBAgent 监控服务端口',
          }),
          value: obagent?.monagent_http_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ObagentManageServicePorts',
            defaultMessage: 'OBAgent 管理服务端口',
          }),
          value: obagent?.mgragent_http_port,
        },
      );
      obagent?.parameters?.length &&
        more.push({
          label: componentsConfig[obagentComponent].labelName,
          parameters: obagent?.parameters,
        });
    }
    // more是否有数据跟前面是否打开更多配置有关
    if (!lowVersion && selectedConfig.includes('ocp-express')) {
      content.push({
        label: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.PortOcpExpress',
          defaultMessage: 'OCP Express 端口',
        }),
        value: ocpexpress?.port,
      });
      ocpexpress?.parameters?.length &&
        more.push({
          label: componentsConfig[ocpexpressComponentKey].labelName,
          parameters: ocpexpress?.parameters,
        });
    }

    if (selectedConfig.includes(configServerComponent)) {
      content = content.concat({
        label: intl.formatMessage({
          id: 'OBD.pages.Obdeploy.CheckInfo.ObconfigserverServicePort',
          defaultMessage: 'obconfigserver 服务端口',
        }),
        value: obconfigserver?.listen_port,
      });
      obconfigserver?.parameters?.length &&
        more.push({
          label: componentsConfig[configServerComponentKey].labelName,
          parameters: obconfigserver?.parameters,
        });
    }
    clusterConfigInfo.push({
      key: 'components',
      group: intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.ComponentConfiguration',
        defaultMessage: '组件配置',
      }),
      content,
      more,
    });
  }

  useEffect(() => {
    const newConfig = { ...componentConfig };
    if (Object.keys(ocpexpress).length !== 0) {
      newConfig.ocpexpress.admin_passwd = generateComplexPwd();
    }
    if (Object.keys(obproxy).length !== 0) {
      newConfig.obproxy.obproxy_sys_password = generatePwd();
    }
    setComponentConfig(newConfig);
  }, []);

  return (
    <Space
      className={`${styles.spaceWidth} ${styles.checkInfoSpace}`}
      direction="vertical"
      size="middle"
    >
      <Alert
        type="info"
        showIcon
        icon={<ExclamationCircleFilled className={styles.alertContent} />}
        message={intl.formatMessage({
          id: 'OBD.pages.ComponentDeploy.PreCheckInfo.TheComponentConfigurationHasBeen',
          defaultMessage:
            '组件配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
        })}
      />

      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <DeployedCompCheckInfo componentsList={componentsList} />
        </Row>
      </ProCard>

      {/* 组件节点配置 */}
      {selectedConfig.includes('obproxy-ce') ||
      selectedConfig.includes(ocpexpressComponent) ||
      selectedConfig.includes(configServerComponent) ? (
        <ProCard className={styles.pageCard} split="horizontal">
          <Row gutter={16}>
            {selectedConfig.length ? (
              <CompNodeCheckInfo
                componentsNodeConfigList={componentsNodeConfigList}
              />
            ) : null}
          </Row>
        </ProCard>
      ) : null}

      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <UserCheckInfo title={<DeployedUserTitle />} user={deployUser} />
        </Row>
      </ProCard>
      {/* 软件路径配置 */}
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <PathCheckInfo home_path={home_path} />
        </Row>
      </ProCard>
      {/* 组件配置 */}
      <CompDetailCheckInfo clusterConfigInfo={clusterConfigInfo} />
      <CustomFooter>
        <Button
          onClick={() => handleQuit(handleQuitProgress, setCurrent, false, 5)}
        >
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.PreCheckInfo.Exit',
            defaultMessage: '退出',
          })}
        </Button>
        <Button onClick={preStep}>
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.PreCheckInfo.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button loading={loading} onClick={handlePreCheck} type="primary">
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.PreCheckInfo.PreCheck',
            defaultMessage: '预检查',
          })}
        </Button>
      </CustomFooter>
    </Space>
  );
}
