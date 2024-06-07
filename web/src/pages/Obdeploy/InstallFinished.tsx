import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import {
  Space,
  Button,
  Table,
  Alert,
  Result,
  Tooltip,
  message,
  Tag,
  Modal,
  Typography,
  Spin,
} from 'antd';
import {
  CloseCircleFilled,
  CheckCircleFilled,
  CaretRightFilled,
  CaretDownFilled,
  CopyOutlined,
  ExclamationCircleOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import useRequest from '@/utils/useRequest';
import type { ColumnsType } from 'antd/es/table';
import copy from 'copy-to-clipboard';
import { handleCopy } from '@/utils/helper';
import {
  queryDeploymentReport,
  queryConnectionInfo,
  queryInstallLog,
} from '@/services/ob-deploy-web/Deployments';
import {
  componentsConfig,
  componentVersionTypeToComponent,
} from '../constants';
import { handleQuit, getErrorInfo } from '@/utils';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const { Paragraph } = Typography;

export default function InstallProcess() {
  const {
    configData,
    installStatus,
    setCurrentStep,
    handleQuitProgress,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const [logs, setLogs] = useState({});
  const [currentExpeandedName, setCurrentExpeandedName] = useState('');

  const name = configData?.components?.oceanbase?.appname;
  const { run: fetchReportInfo, data: reportInfo } = useRequest(
    queryDeploymentReport,
    {
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );
  const { run: fetchConnectInfo, data: connectInfo } = useRequest(
    queryConnectionInfo,
    {
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const { run: handleInstallLog, loading } = useRequest(queryInstallLog, {
    onSuccess: (
      { success, data }: API.OBResponseInstallLog_,
      [{ component_name }]: [API.queryInstallLogParams],
    ) => {
      if (success) {
        setLogs({ ...logs, [component_name]: data?.log });
        setTimeout(() => {
          const log = document.getElementById(`report-log-${component_name}`);
          if (log) {
            log.scrollTop = log.scrollHeight;
          }
        });
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  useEffect(() => {
    fetchReportInfo({ name });
    fetchConnectInfo({ name });
  }, []);

  const connectColumns: ColumnsType<API.ConnectionInfo> = [
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Component',
        defaultMessage: '组件',
      }),
      dataIndex: 'component',
      width: 200,
      render: (text) => {
        const component = componentVersionTypeToComponent[text]
          ? componentVersionTypeToComponent[text]
          : text;
        return componentsConfig[component]?.showComponentName || '-';
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.AccessAddress',
        defaultMessage: '访问地址',
      }),
      dataIndex: 'access_url',
      width: 160,
      render: (text) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Account',
        defaultMessage: '账号',
      }),
      dataIndex: 'user',
      render: (text) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Password',
        defaultMessage: '密码',
      }),
      dataIndex: 'password',
      width: 160,
      render: (text) =>
        text ? (
          <Tooltip title={text}>
            <div className="ellipsis">{text}</div>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.ConnectionString',
        defaultMessage: '连接串',
      }),
      dataIndex: 'connect_url',
      width: 300,
      render: (text, record) => {
        let content;
        if (/^http/g.test(text)) {
          content = (
            <a
              href={text}
              target="_blank"
              {...(record.component === 'ocp-express'
                ? {
                    spm: intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.DeploymentResultOcpExpressAccess',
                      defaultMessage: '部署结果-OCP Express 访问地址',
                    }),
                  }
                : {})}
            >
              {text}
            </a>
          );
        } else {
          content = (
            <div
              {...(record.component === 'oceanbase'
                ? { spm: 'c307514.d317296' /* spm: 部署结果-直连连接串 */ }
                : record.component === 'obproxy'
                ? {
                    spm: intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.DeploymentResultObproxyConnectionString',
                      defaultMessage: '部署结果-OBProxy 连接串',
                    }),
                  }
                : {})}
            >
              {text}
            </div>
          );
        }
        return (
          <div style={{ position: 'relative' }}>
            <Tooltip title={text}>
              <div className="ellipsis" style={{ width: 'calc(100% - 20px)' }}>
                {content}
              </div>
            </Tooltip>
            <a style={{ position: 'absolute', top: '0px', right: '0px' }}>
              <CopyOutlined onClick={() => handleCopy(text)} />
            </a>
          </div>
        );
      },
    },
  ];

  const reportColumns: ColumnsType<API.DeploymentReport> = [
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.ComponentName',
        defaultMessage: '组件名称',
      }),
      dataIndex: 'name',
      render: (text) => {
        const component = componentVersionTypeToComponent[text]
          ? componentVersionTypeToComponent[text]
          : text;
        return componentsConfig[component]?.showComponentName || '-';
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.ComponentType',
        defaultMessage: '组件类型',
      }),
      dataIndex: 'type',
      render: (_, record) => {
        const component = componentVersionTypeToComponent[record.name]
          ? componentVersionTypeToComponent[record.name]
          : record.name;
        return componentsConfig[component]?.type || '-';
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.Version',
        defaultMessage: '版本',
      }),
      dataIndex: 'version',
      render: (text) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.InstallFinished.InstallationResults',
        defaultMessage: '安装结果',
      }),
      dataIndex: 'status',
      width: locale === 'zh-CN' ? 200 : 260,
      render: (text, record) => {
        const statusIcon =
          text === 'SUCCESSFUL' ? (
            <CheckCircleFilled style={{ color: '#4dcca2', marginRight: 6 }} />
          ) : (
            <CloseCircleFilled style={{ color: '#ff4d67', marginRight: 6 }} />
          );

        const status =
          text === 'SUCCESSFUL'
            ? intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.Success',
                defaultMessage: '成功',
              })
            : intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.Failed',
                defaultMessage: '失败',
              });

        const getCommand = (component: string, ip: string) => {
          return `obd tool command ${name} log -c ${component} -s ${ip}`;
        };

        const serversInfo = record.servers?.map((server) => ({
          server,
          command: getCommand(record.name, server),
        }));

        return (
          <>
            {statusIcon}
            {status}
            <Tooltip
              title={
                <>
                  <div style={{ marginBottom: 12 }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.components.InstallFinished.GoToTheObdConsole',
                      defaultMessage: '请前往 OBD 中控机执行以下命令查看日志',
                    })}
                  </div>
                  {serversInfo.map((item) => (
                    <>
                      <div className="fw-500">
                        {statusIcon}
                        {item.server}
                      </div>
                      <div style={{ position: 'relative' }}>
                        <div
                          style={{
                            width: 'calc(100% - 20px)',
                            fontFamily: 'PingFangSC',
                          }}
                        >
                          {item.command}
                        </div>
                        <a
                          style={{
                            position: 'absolute',
                            top: '0px',
                            right: '0px',
                          }}
                        >
                          <CopyOutlined
                            onClick={() => handleCopy(item.command)}
                          />
                        </a>
                      </div>
                    </>
                  ))}
                </>
              }
              placement="topRight"
              overlayClassName={styles.reportTooltip}
            >
              <Tag className="default-tag ml-16">
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallFinished.ViewDetails',
                  defaultMessage: '查看详情',
                })}
              </Tag>
            </Tooltip>
          </>
        );
      },
    },
  ];

  const onExpand = (expeanded: boolean, record: API.DeploymentReport) => {
    if (expeanded && !logs?.[record.name]) {
      setCurrentExpeandedName(record.name);
      handleInstallLog({ name, component_name: record.name });
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
          {intl.formatMessage({
            id: 'OBD.pages.components.InstallFinished.BeforeExitingMakeSureThat',
            defaultMessage: '退出前，请确保已复制访问地址及账密信息',
          })}

          <br />
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
              onCopy: () =>{
                handleCopy(JSON.stringify(connectInfo.items, null, 4) || '')
              },
            }}
          />
        </div>
      ),

      icon: <ExclamationCircleOutlined style={{ color: '#ff4b4b' }} />,
      onOk: () => {
        handleQuit(handleQuitProgress, setCurrentStep, true);
      },
    });
  };

  return (
    <Space className={styles.spaceWidth} direction="vertical" size="middle">
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
              {intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.OceanbaseSuccessfullyDeployed',
                defaultMessage: 'OceanBase 部署成功',
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
              {intl.formatMessage({
                id: 'OBD.pages.components.InstallFinished.OceanbaseDeploymentFailed',
                defaultMessage: 'OceanBase 部署失败',
              })}
            </div>
          )
        }
      />

      {connectInfo?.items?.length ? (
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
            showIcon
            action={
              <Button
                type="primary"
                onClick={() =>
                  handleCopy(JSON.stringify(connectInfo?.items, null, 4) || '')
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
                  id: 'OBD.pages.components.InstallFinished.OneClickCopy',
                  defaultMessage: '一键复制',
                })}
              </Button>
            }
          />

          <Table
            className={`${styles.connectTable} ob-table`}
            columns={connectColumns}
            dataSource={connectInfo?.items || []}
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
          columns={reportColumns}
          dataSource={reportInfo?.items || []}
          rowKey="name"
          expandable={{ onExpand, expandedRowRender }}
          pagination={false}
        />
      </ProCard>
      <footer className={styles.pageFooterContainer}>
        <div className={styles.pageFooter}>
          <Space className={styles.foolterAction}>
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
          </Space>
        </div>
      </footer>
    </Space>
  );
}
