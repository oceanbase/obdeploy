import { useEffect } from 'react';
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
import {
  queryDeploymentReport,
  queryConnectionInfo,
} from '@/services/ob-deploy-web/Deployments';
import {
  componentsConfig,
  componentVersionTypeToComponent,
} from '../constants';
import { handleQuit } from '@/utils';
import styles from './index.less';

const { Paragraph } = Typography;

export default function InstallProcess() {
  const { configData, installStatus, setCurrentStep, handleQuitProgress } =
    useModel('global');

  const name = configData?.components?.oceanbase?.appname;
  const { run: fetchReportInfo, data: reportInfo } = useRequest(
    queryDeploymentReport,
  );
  const { run: fetchConnectInfo, data: connectInfo } =
    useRequest(queryConnectionInfo);

  const handleCopy = (content: string) => {
    copy(content);
    message.success('复制成功');
  };

  const handleCopyCommand = (command: string) => {
    copy(command);
    message.success('复制成功');
  };

  useEffect(() => {
    fetchReportInfo({ name });
    fetchConnectInfo({ name });
  }, []);

  const connectColumns: ColumnsType<API.ConnectionInfo> = [
    {
      title: '组件',
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
      title: '访问地址',
      dataIndex: 'access_url',
      width: 160,
      render: (text) => text || '-',
    },
    {
      title: '账号',
      dataIndex: 'user',
      render: (text) => text || '-',
    },
    {
      title: '密码',
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
      title: '连接串',
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
                ? { spm: '部署结果-OCP Express 访问地址' }
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
                ? { spm: '部署结果-OBProxy 连接串' }
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
      title: '组件名称',
      dataIndex: 'name',
      render: (text) => {
        const component = componentVersionTypeToComponent[text]
          ? componentVersionTypeToComponent[text]
          : text;
        return componentsConfig[component]?.showComponentName || '-';
      },
    },
    {
      title: '组件类型',
      dataIndex: 'type',
      render: (_, record) => {
        const component = componentVersionTypeToComponent[record.name]
          ? componentVersionTypeToComponent[record.name]
          : record.name;
        return componentsConfig[component]?.type || '-';
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      render: (text) => text || '-',
    },
    {
      title: '安装结果',
      dataIndex: 'status',
      width: 150,
      render: (text) =>
        text === 'SUCCESSFUL' ? (
          <>
            <CheckCircleFilled style={{ color: '#4dcca2', marginRight: 6 }} />
            成功
          </>
        ) : (
          <>
            <CloseCircleFilled style={{ color: '#ff4d67', marginRight: 6 }} />
            失败
          </>
        ),
    },
  ];

  const getEpendedColumns = (component: string) => {
    const expendedColumns: ColumnsType<{ ip: string }> = [
      {
        title: '节点',
        dataIndex: 'ip',
        render: (text) => text || '-',
      },
      {
        title: '日志',
        dataIndex: 'log',
        width: 200,
        render: (_, record) => {
          const command = `obd tool command ${name} log -c ${component} -s ${record.ip}`;
          return (
            <Tooltip
              title={
                <>
                  请前往 OBD 中控机执行以下命令查看日志：
                  <br />
                  {command} <br />
                  <a onClick={() => handleCopyCommand(command)}>复制信息</a>
                </>
              }
              overlayStyle={{ width: 300 }}
            >
              <Tag className="default-tag">查看日志</Tag>
            </Tooltip>
          );
        },
      },
    ];
    return expendedColumns;
  };

  const expandedRowRender = (record: API.DeploymentReport) => {
    const serversData = record?.servers?.map((server) => ({ ip: server }));
    return (
      <Table
        className="ob-table"
        columns={getEpendedColumns(record.name)}
        dataSource={serversData || []}
        rowKey="ip"
        pagination={false}
      />
    );
  };

  const handleFinished = () => {
    Modal.confirm({
      title: '是否要退出页面？',
      okText: '退出',
      cancelText: '取消',
      okButtonProps: { type: 'primary', danger: true },
      content: (
        <div>
          退出前，请确保已复制访问地址及账密信息
          <br />
          <Paragraph
            copyable={{
              tooltips: false,
              icon: [
                <>
                  <CopyOutlined style={{ marginRight: 6 }} />
                  复制信息
                </>,
                <>
                  <CheckOutlined style={{ marginRight: 6, color: '#4dcca2' }} />
                  复制信息
                </>,
              ],
              onCopy: () => handleCopy(JSON.stringify(connectInfo?.items)),
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
              data-aspm-desc="部署结果-部署成功"
              data-aspm-param={``}
              data-aspm-expo
            >
              OceanBase 部署成功
            </div>
          ) : (
            <div
              data-aspm-click="c307514.d317298"
              data-aspm-desc="部署结果-部署失败"
              data-aspm-param={``}
              data-aspm-expo
            >
              OceanBase 部署失败
            </div>
          )
        }
      />
      {connectInfo?.items?.length ? (
        <ProCard title="访问地址及账密信息">
          <Alert
            message="请妥善保存以下访问地址及账密信息，OceanBase 未保存账密信息，丢失后无法找回"
            type="info"
            showIcon
            action={
              <Button
                type="primary"
                onClick={() => handleCopy(JSON.stringify(connectInfo?.items))}
                data-aspm-click="c307514.d317299"
                data-aspm-desc="部署结果-复制信息"
                data-aspm-param={``}
                data-aspm-expo
              >
                复制信息
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
        title="部署报告"
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
          expandable={{ expandedRowRender }}
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
              data-aspm-desc="部署结果-部署完成"
              data-aspm-param={``}
              data-aspm-expo
            >
              完成
            </Button>
          </Space>
        </div>
      </footer>
    </Space>
  );
}
