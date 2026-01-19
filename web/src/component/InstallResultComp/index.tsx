import {
  connectColumns,
  getReportColumns,
} from '@/pages/Obdeploy/InstallFinished';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { handleCopy } from '@/utils/helper';
import { intl } from '@/utils/intl';
import {
  CaretDownFilled,
  CaretRightFilled,
  CheckOutlined,
  CopyOutlined,
  ExclamationCircleFilled,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { getLocale, useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import {
  Alert,
  Button,
  Modal,
  Popconfirm,
  Result,
  Space,
  Spin,
  Table,
  Typography,
} from 'antd';
import { isEmpty } from 'lodash';
import { useState } from 'react';
import CreatTenant from '../CreateTenantDrawer';
import CustomFooter from '../CustomFooter';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
const { Paragraph, Text } = Typography;

export enum ResultType {
  OBInstall = 'obInstall',
  CompInstall = 'componentInstall',
  TenantInstall = 'tenantInstall',
  OmsInstall = 'omsInstall',
}

interface InstallResultCompProps {
  installStatus: string;
  connectInfo?: API.ConnectionInfo[];
  reportInfo?: API.DeploymentReport[];
  ConfigserverAlert?: React.ReactDOM;
  type: ResultType;
  logs: any;
  name: string;
  configPath?: string;
  handleInstallLog: ({
    name,
    components,
    component_name,
  }: {
    name: string;
    components?: string;
    component_name?: string;
  }) => void;
  loading: boolean;
  exitOnOk: () => void;
}

export default function InstallResultComp({
  installStatus,
  connectInfo,
  reportInfo,
  logs,
  type,
  handleInstallLog,
  name,
  loading,
  exitOnOk,
  configPath,
  ConfigserverAlert,
}: InstallResultCompProps) {
  const [currentExpeandedName, setCurrentExpeandedName] = useState('');
  const [obConnectInfo, setObConnectInfo] = useState('');
  const { deployUser = '', componentConfig = {} } = useModel('componentDeploy');
  const { home_path = '' } = componentConfig;
  const [open, setOpen] = useState<boolean>(false);

  const onExpand = (expeanded: boolean, record: API.DeploymentReport) => {
    if (expeanded && !logs?.[record.name]) {
      setCurrentExpeandedName(record.name);
      if (type === ResultType.CompInstall) {
        handleInstallLog({ name, components: record.name });
      } else if (type === ResultType.OBInstall) {
        handleInstallLog({ name, component_name: record.name });
      }
    }
  };
  const expandedRowRender = (record: API.DeploymentReport) => {
    return (
      <Spin spinning={loading && currentExpeandedName === record.name}>
        <pre className={styles.reportLog} id={`report-log-${record.name}`}>
          {logs?.[record.name]}
        </pre>
      </Spin>
    );
  };

  const handleFinished = () => {
    Modal.confirm({
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.DoYouWantToExit',
        defaultMessage: '是否要退出页面？',
      }),
      okText: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Exit',
        defaultMessage: '退出',
      }),
      cancelText: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Cancel',
        defaultMessage: '取消',
      }),
      okButtonProps: { type: 'primary', danger: true },
      content: (
        <div>
          <p style={{ margin: '0 0 4px 0', lineHeight: '22px' }}>
            {intl.formatMessage({
              id: 'OBD.pages.components.InstallFinished.BeforeExitingMakeSureThat',
              defaultMessage: '退出前，请确保已复制访问地址及账密信息',
            })}
          </p>
          <Paragraph
            copyable={{
              tooltips: false,
              icon: [
                <>
                  <CopyOutlined style={{ marginRight: 6 }} />
                  {intl.formatMessage({
                    id: 'OBD.pages.components.InstallFinished.CopyInformation',
                    defaultMessage: '复制信息',
                  })}
                </>,
                <>
                  <CheckOutlined style={{ marginRight: 6, color: '#4dcca2' }} />
                  {intl.formatMessage({
                    id: 'OBD.pages.components.InstallFinished.CopyInformation',
                    defaultMessage: '复制信息',
                  })}
                </>,
              ],

              onCopy: () => {
                handleCopy(JSON.stringify(connectInfo, null, 4) || '');
              },
            }}
          />
        </div>
      ),

      icon: <ExclamationCircleOutlined style={{ color: '#ff4b4b' }} />,
      onOk: exitOnOk,
    });
  };

  const { ocpConfigData } = useModel('global');
  const { components = {} } = ocpConfigData;
  const { oceanbase = {} } = components;

  // 上报遥测数据
  const { run: telemetryReport } = useRequest(OCP.telemetryReport, {
    manual: true,
    throwOnError: false,
    onError: () => {
      // 静默处理错误，不显示错误信息
    },
  });

  useRequest(OCP.getTelemetryData, {
    ready: !!name,
    throwOnError: false,
    defaultParams: [
      {
        name,
      },
    ],
    onSuccess: (res) => {
      // 即使 success 为 false 也不显示错误，静默处理
      if (res?.success && !isEmpty(res?.data)) {
        const data = res?.data;
        telemetryReport({ component: 'obd', content: data?.data });
      }
    },
    onError: () => {
      // 静默处理错误，不显示错误信息
    },
  });

  const obConnect = connectInfo?.find((item) =>
    item.component.includes('oceanbase'),
  );

  const obConnectUrl = obConnect?.connect_url;

  return (
    <Space className={styles.spaceWidth} direction="vertical" size="middle">
      {ConfigserverAlert}
      <Result
        style={{ paddingBottom: 8 }}
        icon={
          <img
            src={
              installStatus === 'SUCCESSFUL'
                ? '/assets/successful.png'
                : '/assets/failed.png'
            }
            alt="resultLogo"
            style={{ width: 160, position: 'relative', right: '-8px' }}
          />
        }
        title={
          installStatus === 'SUCCESSFUL' ? (
            <div
              data-aspm-click="c307514.d317295"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.DeploymentResultDeploymentSuccessful',
                defaultMessage: '部署结果-部署成功',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {type === ResultType.OBInstall
                ? intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.OceanbaseSuccessfullyDeployed',
                  defaultMessage: 'OceanBase 部署成功!',
                })
                : type === ResultType.OmsInstall
                  ? 'OMS 部署成功!'
                  : intl.formatMessage({
                    id: 'OBD.component.InstallResultComp.ComponentDeploymentSucceeded',
                    defaultMessage: '组件部署成功',
                  })}
            </div>
          ) : (
            <div
              data-aspm-click="c307514.d317298"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.DeploymentResultDeploymentFailed',
                defaultMessage: '部署结果-部署失败',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {type === ResultType.OBInstall
                ? intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.OceanbaseDeploymentFailed',
                  defaultMessage: 'OceanBase 部署失败',
                })
                : type === ResultType.OmsInstall
                  ? 'OMS 部署失败'
                  : intl.formatMessage({
                    id: 'OBD.component.InstallResultComp.ComponentDeploymentFailed',
                    defaultMessage: '组件部署失败',
                  })}
            </div>
          )
        }
      />
      {connectInfo?.length ? (
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.pages.components.InstallFinished.AccessAddressAndAccountSecret',
            defaultMessage: '访问地址及账密信息',
          })}
        >
          <Alert
            message={intl.formatMessage({
              id: 'OBD.pages.components.InstallFinished.PleaseKeepTheFollowingAccess',
              defaultMessage:
                '请妥善保存以下访问地址及账密信息，OceanBase 未保存账密信息，丢失后无法找回',
            })}
            type="info"
            icon={<ExclamationCircleFilled className={styles.alertContent} />}
            showIcon
            action={
              <Button
                type="primary"
                onClick={() =>
                  handleCopy(JSON.stringify(connectInfo, null, 4) || '')
                }
                data-aspm-click="c307514.d317299"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.DeploymentResultCopyInformation',
                  defaultMessage: '部署结果-复制信息',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.component.InsstallResult.CopyInformation',
                  defaultMessage: '复制信息',
                })}
              </Button>
            }
          />

          <Table
            className={`${styles.connectTable} ob-table`}
            columns={connectColumns}
            dataSource={connectInfo || []}
            rowKey="component"
            pagination={false}
          />
        </ProCard>
      ) : null}
      <ProCard
        title={intl.formatMessage({
          id: 'OBD.pages.components.InstallFinished.DeploymentReport',
          defaultMessage: '部署报告',
        })}
        className={styles.collapsibleCard}
        collapsible
        defaultCollapsed={installStatus !== 'FAILED'}
        collapsibleIconRender={({ collapsed }) =>
          collapsed ? <CaretRightFilled /> : <CaretDownFilled />
        }
        bodyStyle={{ paddingLeft: '0px', paddingRight: '0px' }}
      >
        <Table
          className="ob-table ob-table-expandable"
          columns={getReportColumns(
            name,
            type === ResultType.CompInstall,
            configPath,
          )}
          dataSource={reportInfo || []}
          rowKey="name"
          expandable={{ onExpand, expandedRowRender }}
          pagination={false}
        />
      </ProCard>
      <CustomFooter>
        {type === ResultType.OBInstall ? (
          <>
            <Popconfirm
              title={
                <>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.0116F3E1',
                      defaultMessage: '确定要退出页面吗？',
                    })}
                  </div>
                  <div style={{ color: '#5c6b8a', margin: '8px 0' }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.4C585A48',
                      defaultMessage: '退出前，请确保已复制访问地址及账密信息',
                    })}
                  </div>
                  <Text
                    copyable={{
                      text: `${obConnectUrl} ${obConnectInfo}`,
                    }}
                    style={{ color: '#006aff' }}
                  >
                    {intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.0B5951B4',
                      defaultMessage: '复制链接信息',
                    })}
                  </Text>
                </>
              }
              onConfirm={exitOnOk}
              okText={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.CE82EA51',
                defaultMessage: '退出',
              })}
              cancelText={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.F8BD249F',
                defaultMessage: '取消',
              })}
              okButtonProps={{
                danger: true,
              }}
              icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
            >
              <Button
                type="default"
                data-aspm-click="c307514.d317297"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.DeploymentResultDeploymentCompleted',
                  defaultMessage: '部署结果-部署完成',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.B444903C',
                  defaultMessage: '退出',
                })}
              </Button>
            </Popconfirm>
            {installStatus === 'SUCCESSFUL' && (
              <Button type="primary" onClick={() => setOpen(true)}>
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.15AD4E27',
                  defaultMessage: '创建业务租户',
                })}
              </Button>
            )}
          </>
        ) : type === ResultType.OmsInstall
          ? <Popconfirm
            title={
              <>
                <div style={{ fontSize: 16, fontWeight: 600 }}>
                  {intl.formatMessage({
                    id: 'OBD.component.InstallResult.DoYouWantToExit',
                    defaultMessage: '是否要退出页面？',
                  })}
                </div>
                <div style={{ color: '#5c6b8a', margin: '8px 0' }}>
                  {intl.formatMessage({
                    id: 'OBD.pages.components.InstallFinished.4C585A48',
                    defaultMessage: '退出前，请确保已复制访问地址及账密信息',
                  })}
                </div>
                <Text
                  copyable={{
                    text: `${obConnectUrl} ${obConnectInfo}`,
                  }}
                  style={{ color: '#006aff' }}
                >
                  {intl.formatMessage({
                    id: 'OBD.pages.components.InstallFinished.0B5951B4',
                    defaultMessage: '复制链接信息',
                  })}
                </Text>
              </>
            }
            onConfirm={exitOnOk}
            okText={intl.formatMessage({
              id: 'OBD.pages.components.InstallFinished.CE82EA51',
              defaultMessage: '退出',
            })}
            cancelText={intl.formatMessage({
              id: 'OBD.pages.components.InstallFinished.F8BD249F',
              defaultMessage: '取消',
            })}
            okButtonProps={{
              danger: true,
            }}
            icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
          >
            <Button
              type="default"
              data-aspm-click="c307514.d317297"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.DeploymentResultDeploymentCompleted',
                defaultMessage: '部署结果-部署完成',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              完成
            </Button>
          </Popconfirm> : (
            <Button
              type="primary"
              onClick={handleFinished}
              data-aspm-click="c307514.d317297"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.DeploymentResultDeploymentCompleted',
                defaultMessage: '部署结果-部署完成',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.Complete',
                defaultMessage: '退出',
              })}
            </Button>
          )}
      </CustomFooter>
      <CreatTenant
        open={open}
        setOpen={setOpen}
        obConnectInfo={obConnectInfo as string}
        setObConnectInfo={setObConnectInfo}
        obConnectUrl={obConnect?.access_url}
      />
    </Space>
  );
}
