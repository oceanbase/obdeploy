import { intl } from '@/utils/intl';
import { Button, Space, Alert, Row, Col } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from 'umi';
import useRequest from '@/utils/useRequest';
import { getErrorInfo } from '@/utils';
import { createOcpDeploymentConfig } from '@/services/ocp_installer_backend/OCP';
import CustomFooter from '../../CustomFooter';
import BasicInfo from './BasicInfo';
import ConfigInfo from './ConfigInfo';
import ConnectInfo from './ConnectInfo';
import ResourceInfo from './ResourceInfo';
import ExitBtn from '@/component/ExitBtn';
import { formatPreCheckData } from '../helper';
import { encryptPwdForConfig } from '@/utils/encrypt';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import CustomAlert from '@/component/CustomAlert';
import styles from '../index.less';
import type {
  BasicInfoProp,
  ProductInfoType,
  ConnectInfoType,
  ConnectInfoPropType,
  ResourceInfoPropType,
} from './type';

interface CheckInfoProps {
  showNext: React.Dispatch<React.SetStateAction<boolean>>;
  isNewDB: boolean;
}

export const leftCardStyle = { width: 211 };

export default function CheckInfo({
  showNext,
  current,
  setCurrent,
  isNewDB,
}: CheckInfoProps & API.StepProp) {
  const { ocpConfigData, setErrorVisible, setErrorsList, errorsList } =
    useModel('global');
  const { setConnectId, obVersionInfo, ocpVersionInfo, obproxyVersionInfo } =
    useModel('ocpInstallData');
  const { components = {}, auth = {} } = ocpConfigData;
  const { oceanbase = {}, obproxy = {}, ocpserver = {} } = components;
  const basicInfoProp: BasicInfoProp = {
    appname: oceanbase.appname,
    type: intl.formatMessage({
      id: 'OBD.OCPPreCheck.CheckInfo.InstallAll',
      defaultMessage: '全部安装',
    }),
    productsInfo: [
      {
        productName: 'OCP',
        version: ocpserver.version,
        isCommunity: ocpVersionInfo?.versionType === 'ce',
      },
    ],
  };
  const configInfoProp: ConnectInfoPropType = {
    userConfig: { ...auth },
    ocpNodeConfig: ocpserver.servers,
    clusterConfig: {
      info: {
        root_password: oceanbase.root_password,
        home_path: oceanbase.home_path,
        data_dir: oceanbase.data_dir,
        redo_dir: oceanbase.redo_dir,
        mysql_port: oceanbase.mysql_port,
        rpc_port: oceanbase.rpc_port,
      },
    },
    dbNode: oceanbase.topology,
    obproxyConfig: {
      info: {
        servers: obproxy.servers,
        home_path: obproxy.home_path,
        listen_port: obproxy.listen_port,
        prometheus_listen_port: obproxy.prometheus_listen_port,
      },
    },
  };
  const connectInfoProp: ConnectInfoType[] = [
    [
      {
        label: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.HostIp',
          defaultMessage: '主机IP',
        }),
        value: ocpserver?.metadb?.host,
      },
      {
        label: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.AccessPort',
          defaultMessage: '访问端口',
        }),
        value: ocpserver?.metadb?.port,
      },
    ],

    [
      {
        label: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.AccessAccount',
          defaultMessage: '访问账号',
        }),
        value: ocpserver?.metadb?.user,
      },
      {
        label: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.Password',
          defaultMessage: '密码',
        }),
        value: ocpserver?.metadb?.password,
      },
    ],
  ];

  const resourceInfoProp: ResourceInfoPropType = {
    serviceConfig: {
      admin_password: ocpserver.admin_password,
      home_path: ocpserver.home_path,
      log_dir: ocpserver.log_dir,
      soft_dir: ocpserver.soft_dir,
      ocp_site_url: ocpserver.ocp_site_url,
    },
    resourcePlan: { ...ocpserver.manage_info },
    memory_size: ocpserver.memory_size,
    tenantConfig: {
      info: {
        tenant_name: ocpserver?.meta_tenant?.name?.tenant_name,
        password: ocpserver?.meta_tenant?.password,
      },
      resource: { ...ocpserver?.meta_tenant?.resource },
    },
    monitorConfig: {
      info: {
        tenant_name: ocpserver?.monitor_tenant?.name?.tenant_name,
        password: ocpserver?.monitor_tenant?.password,
      },
      resource: { ...ocpserver?.monitor_tenant?.resource },
    },
  };
  if (isNewDB) {
    let extraProducts: ProductInfoType[] = [
      {
        productName: 'OceanBase',
        version: oceanbase.version,
        isCommunity: obVersionInfo?.versionType === 'ce',
      },
      {
        productName: 'OBProxy',
        version: obproxy.version,
      },
    ];

    basicInfoProp.productsInfo.push(...extraProducts);
  }
  if (!isNewDB) {
    resourceInfoProp.userConfig = { ...auth };
    resourceInfoProp.ocpServer = ocpserver.servers;
  }
  const { run: handleCreateConfig, loading } = useRequest(
    createOcpDeploymentConfig,
    {
      onSuccess: ({ success, data }: API.OBResponse) => {
        if (success) {
          setConnectId(data);
          showNext(true);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const nextStep = async() => {
    const { data: publicKey } = await getPublicKey();
    handleCreateConfig(
      { name: oceanbase?.appname },
      formatPreCheckData(encryptPwdForConfig(ocpConfigData, publicKey)),
    );
  };
  const prevStep = () => {
    setCurrent(current - 1);
  };
  return (
    <Space className={styles.checkInfoSpace} direction="vertical" size="middle">
      <CustomAlert
        message={intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.TheOcpInstallationInformationConfiguration',
          defaultMessage:
            'OCP 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
        })}
        type="info"
        showIcon
        style={{ margin: '16px 0', height: '40px' }}
      />

      <ProCard className={styles.pageCard} split="horizontal">
        <BasicInfo basicInfoProp={basicInfoProp} />
      </ProCard>
      <ProCard className={styles.pageCard} split="vertical">
        <Row gutter={16}>
          {!isNewDB ? (
            <ConnectInfo connectInfoProp={connectInfoProp} />
          ) : (
            <ConfigInfo
              configInfoProp={configInfoProp}
              oceanbase={oceanbase}
              obproxy={obproxy}
              isNewDB={isNewDB}
            />
          )}
        </Row>
      </ProCard>
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <ResourceInfo resourceInfoProp={resourceInfoProp} isNewDB={isNewDB} />
        </Row>
      </ProCard>
      <CustomFooter>
        <ExitBtn />
        <Button
          data-aspm-click="ca54437.da43442"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.PreCheckPreviousStep',
            defaultMessage: '预检查-上一步',
          })}
          data-aspm-param={``}
          data-aspm-expo
          onClick={prevStep}
        >
          {intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button
          data-aspm-click="ca54437.da43443"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.PreCheck',
            defaultMessage: '预检查-预检查',
          })}
          data-aspm-param={``}
          data-aspm-expo
          loading={loading}
          type="primary"
          onClick={nextStep}
        >
          {intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.PreCheck.1',
            defaultMessage: '预检查',
          })}
        </Button>
      </CustomFooter>
    </Space>
  );
}
