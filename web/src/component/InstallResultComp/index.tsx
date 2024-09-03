import {
  connectColumns,
  getReportColumns,
} from '@/pages/Obdeploy/InstallFinished';
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
import {
  Alert,
  Button,
  Modal,
  Result,
  Space,
  Spin,
  Table,
  Typography,
} from 'antd';
import { useState } from 'react';
import CustomFooter from '../CustomFooter';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
const { Paragraph } = Typography;

export enum ResultType {
  OBInstall = 'obInstall',
  CompInstall = 'componentInstall',
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
  const { deployUser = '', componentConfig = {} } = useModel('componentDeploy');
  const { home_path = '' } = componentConfig;
  const onExpand = (expeanded: boolean, record: API.DeploymentReport) => {
    if (expeanded && !logs?.[record.name]) {
      setCurrentExpeandedName(record.name);
      if (type === ResultType.CompInstall) {
        handleInstallLog({ name, components: record.name });
      } else {
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
                    defaultMessage: 'OceanBase 部署成功',
                  })
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
            configPath
          )}
          dataSource={reportInfo || []}
          rowKey="name"
          expandable={{ onExpand, expandedRowRender }}
          pagination={false}
        />
      </ProCard>
      <CustomFooter>
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
            defaultMessage: '完成',
          })}
        </Button>
      </CustomFooter>
    </Space>
  );
}
