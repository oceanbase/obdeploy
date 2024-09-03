import InstallResultComp, { ResultType } from '@/component/InstallResultComp';
import {
  queryConnectionInfo,
  queryDeploymentReport,
  queryInstallLog,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo, handleQuit } from '@/utils';
import { connectInfoForPwd, handleCopy } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  CopyOutlined,
} from '@ant-design/icons';
import { Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  componentsConfig,
  componentVersionTypeToComponent,
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export const connectColumns: ColumnsType<API.ConnectionInfo> = [
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
      id: 'OBD.pages.Obdeploy.InstallFinished.ConnectionString',
      defaultMessage: '连接字符串',
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
          {text ? (
            <>
              {' '}
              <Tooltip title={text}>
                <div
                  className="ellipsis"
                  style={{ width: 'calc(100% - 20px)' }}
                >
                  {content}
                </div>
              </Tooltip>
              <a style={{ position: 'absolute', top: '0px', right: '0px' }}>
                <CopyOutlined onClick={() => handleCopy(text)} />
              </a>
            </>
          ) : (
            '-'
          )}
        </div>
      );
    },
  },
];

export const getReportColumns = (
  clusterName: string,
  isCompChange: boolean = false,
  configPath?: string,
): ColumnsType<API.DeploymentReport> => {
  return [
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
          if (text !== 'SUCCESSFUL' && isCompChange) {
            return `obd tool command ${clusterName} log -c ${component} -s ${ip} --config=${configPath}`;
          }
          return `obd tool command ${clusterName} log -c ${component} -s ${ip}`;
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
};

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
  const name = configData?.components?.oceanbase?.appname;
  const [connectInfo, setConnectInfo] = useState<API.ConnectionInfo[]>([]);
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
  const { run: fetchConnectInfo } = useRequest(queryConnectionInfo, {
    onSuccess: ({ success, data }) => {
      if (success) {
        setConnectInfo(connectInfoForPwd(data?.items, configData?.components));
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

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

  const exitOnOk = () => {
    handleQuit(handleQuitProgress, setCurrentStep, true);
  };

  useEffect(() => {
    fetchReportInfo({ name });
    fetchConnectInfo({ name });
  }, []);

  return (
    <InstallResultComp
      installStatus={installStatus}
      connectInfo={connectInfo}
      reportInfo={reportInfo?.items}
      type={ResultType.OBInstall}
      logs={logs}
      handleInstallLog={handleInstallLog}
      name={name}
      loading={loading}
      exitOnOk={exitOnOk}
    />
  );
}
