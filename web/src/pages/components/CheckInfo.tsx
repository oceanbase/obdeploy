import { useState } from 'react';
import { useModel } from 'umi';
import { Space, Button, Table, Row, Col, Alert, Tooltip } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import type { ColumnsType } from 'antd/es/table';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import useRequest from '@/utils/useRequest';
import { createDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { handleQuit } from '@/utils';
import {
  componentsNameConfig,
  allComponentsKeys,
  onlyComponentsKeys,
  modeConfig,
  obproxyComponent,
} from '../constants';
import styles from './index.less';
interface ComponentsNodeConfig {
  name: string;
  servers: string[];
  key: string;
  isTooltip: boolean;
}

export default function CheckInfo() {
  const {
    configData,
    currentType,
    setCheckOK,
    lowVersion,
    setCurrentStep,
    handleQuitProgress,
  } = useModel('global');
  const { components = {}, auth, home_path } = configData || {};
  const {
    oceanbase = {},
    obproxy = {},
    ocpexpress = {},
    obagent = {},
  } = components;
  const [showPwd, setShowPwd] = useState(false);

  const { run: handleCreateConfig, loading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          setCheckOK(true);
        }
      },
    },
  );

  const prevStep = () => {
    setCurrentStep(3);
  };

  const handlePreCheck = () => {
    handleCreateConfig({ name: oceanbase?.appname }, { ...configData });
  };

  const getComponentsList = () => {
    const componentsList: API.TableComponentInfo[] = [];
    allComponentsKeys.forEach((key) => {
      if (components?.[key]) {
        const componentConfig = componentsNameConfig?.[key] || {};
        componentsList.push({
          ...componentConfig,
          version: components?.[key].version,
          key,
        });
      }
    });
    return componentsList;
  };

  const getComponentsNodeConfigList = () => {
    const componentsNodeConfigList: ComponentsNodeConfig[] = [];
    let currentOnlyComponentsKeys = onlyComponentsKeys.filter(
      (key) => key !== 'obagent',
    );
    if (lowVersion) {
      currentOnlyComponentsKeys = currentOnlyComponentsKeys.filter(
        (key) => key !== 'ocpexpress',
      );
    }
    currentOnlyComponentsKeys.forEach((key) => {
      if (componentsNameConfig?.[key]) {
        componentsNodeConfigList.push({
          key,
          name: componentsNameConfig?.[key]?.name,
          servers: components?.[key]?.servers?.join('，'),
          isTooltip: key === obproxyComponent,
        });
      }
    });

    return componentsNodeConfigList;
  };

  const dbConfigColumns: ColumnsType<API.DBConfig> = [
    {
      title: 'Zone 名称',
      dataIndex: 'name',
      width: 200,
      render: (text) => text || '-',
    },
    {
      title: 'OB Server 节点',
      dataIndex: 'servers',
      render: (text) => {
        const serversIps = text.map((item: API.OceanbaseServers) => item.ip);
        const str = serversIps.join('，');
        return (
          <Tooltip title={str} placement="topLeft">
            <div className="ellipsis">{str}</div>
          </Tooltip>
        );
      },
    },
    {
      title: 'Root Server 节点',
      dataIndex: 'rootservice',
      width: 200,
      render: (text) => text || '-',
    },
  ];

  const getMoreColumns = (label: string) => {
    const columns: ColumnsType<API.MoreParameter> = [
      {
        title: `${label}参数名称`,
        dataIndex: 'key',
        render: (text) => text,
      },
      {
        title: '参数值',
        dataIndex: 'value',
        render: (text, record) => (record.adaptive ? '自适应' : text || '-'),
      },
      {
        title: '介绍',
        dataIndex: 'description',
        render: (text) => (
          <Tooltip title={text} placement="topLeft">
            <div className="ellipsis">{text}</div>
          </Tooltip>
        ),
      },
    ];
    return columns;
  };

  const componentsList = getComponentsList();
  const componentsNodeConfigList = getComponentsNodeConfigList();
  const initDir = `${home_path}/oceanbase/store`;
  const clusterConfigInfo = [
    {
      key: 'cluster',
      group: '集群配置',
      content: [
        { label: '配置模式', value: modeConfig[oceanbase?.mode] },
        {
          label: 'root@sys 密码',
          value: (
            <Tooltip title={oceanbase?.root_password} placement="topLeft">
              <div className="ellipsis">{oceanbase?.root_password}</div>
            </Tooltip>
          ),
        },
        {
          label: '数据目录',
          value: (
            <Tooltip title={oceanbase?.data_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.data_dir || initDir}</div>
            </Tooltip>
          ),
        },
        {
          label: '日志目录',
          value: (
            <Tooltip title={oceanbase?.redo_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.redo_dir || initDir}</div>
            </Tooltip>
          ),
        },
        { label: 'SQL 端口', value: oceanbase?.mysql_port },
        { label: 'RPC 端口', value: oceanbase?.rpc_port },
      ],
      more: oceanbase?.parameters?.length
        ? [
            {
              label: componentsNameConfig['oceanbase'].name,
              parameters: oceanbase?.parameters,
            },
          ]
        : [],
    },
  ];

  if (currentType === 'all') {
    const content = [
      { label: 'OBProxy 服务端口', value: obproxy?.listen_port },
      {
        label: 'OBProxy Exporter 端口',
        value: obproxy?.prometheus_listen_port,
      },
      { label: 'OBAgent 管理服务端口', value: obagent?.monagent_http_port },
      { label: 'OBAgent 监控服务端口', value: obagent?.mgragent_http_port },
    ];

    if (!lowVersion) {
      content.push({ label: 'OCPExpress 端口', value: ocpexpress?.port });
    }

    let more: any = [];
    if (obproxy?.parameters?.length) {
      more = [
        {
          label: componentsNameConfig['obproxy'].name,
          parameters: obproxy?.parameters,
        },
        {
          label: componentsNameConfig['obagent'].name,
          parameters: obagent?.parameters,
        },
      ];
      if (!lowVersion) {
        more.push({
          label: componentsNameConfig['ocpexpress'].name,
          parameters: ocpexpress?.parameters,
        });
      }
    }
    clusterConfigInfo.push({
      key: 'components',
      group: '组件配置',
      content,
      more,
    });
  }

  return (
    <Space
      className={`${styles.spaceWidth} ${styles.checkInfoSpace}`}
      direction="vertical"
      size="middle"
    >
      <Alert
        message="OceanBase 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。"
        type="info"
        showIcon
      />
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <ProCard title="部署配置" className="card-padding-bottom-24">
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard colSpan={10} title="部署集群名称">
                  {oceanbase?.appname}
                </ProCard>
                <ProCard colSpan={14} title="部署类型">
                  {currentType === 'all' ? '完全部署' : '精简部署'}
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
          <ProCard
            title="部署组件"
            className="card-header-padding-top-0 card-padding-bottom-24 "
          >
            <Row gutter={16}>
              {componentsList.map(
                (item: API.TableComponentInfo, index: number) => (
                  <Col
                    span={12}
                    style={index > 1 ? { marginTop: 16 } : {}}
                    key={item.key}
                  >
                    <ProCard
                      className={styles.infoSubCard}
                      split="vertical"
                      key={item.key}
                    >
                      <ProCard colSpan={10} title="组件">
                        {item?.showComponentName}
                      </ProCard>
                      <ProCard colSpan={7} title="类型">
                        {componentsNameConfig[item.key]?.type}
                      </ProCard>
                      <ProCard colSpan={7} title="版本">
                        {item?.version}
                      </ProCard>
                    </ProCard>
                  </Col>
                ),
              )}
            </Row>
          </ProCard>
        </Row>
      </ProCard>
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <ProCard title="数据库节点配置" className="card-padding-bottom-24">
            <ProCard
              className={styles.infoSubCard}
              style={{ border: '1px solid #e2e8f3' }}
              split="vertical"
            >
              <Table
                className={`${styles.infoCheckTable}  ob-table`}
                columns={dbConfigColumns}
                dataSource={oceanbase?.topology}
                rowKey="id"
                scroll={{ y: 300 }}
                pagination={false}
              />
            </ProCard>
          </ProCard>
          {currentType === 'all' ? (
            <ProCard
              title="组件节点配置"
              className="card-header-padding-top-0 card-padding-bottom-24"
            >
              <Col span={componentsNodeConfigList?.length === 1 ? 12 : 24}>
                <ProCard className={styles.infoSubCard} split="vertical">
                  {componentsNodeConfigList.map(
                    (item: ComponentsNodeConfig) => (
                      <ProCard title={item.name} key={item.key}>
                        {item.isTooltip ? (
                          <Tooltip title={item?.servers} placement="topLeft">
                            <div className="ellipsis">{item?.servers}</div>
                          </Tooltip>
                        ) : (
                          item?.servers
                        )}
                      </ProCard>
                    ),
                  )}
                </ProCard>
              </Col>
            </ProCard>
          ) : null}
          <ProCard
            title="部署用户配置"
            className="card-header-padding-top-0 card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard title="用户名">{auth?.user}</ProCard>
                <ProCard title="密码">
                  {auth?.password ? (
                    <div style={{ position: 'relative' }}>
                      {showPwd ? (
                        <div>
                          <Tooltip title={auth?.password} placement="topLeft">
                            <div
                              className="ellipsis"
                              style={{ width: 'calc(100% - 20px)' }}
                            >
                              {auth?.password}
                            </div>
                          </Tooltip>
                          <EyeOutlined
                            className={styles.pwdIcon}
                            onClick={() => setShowPwd(false)}
                          />
                        </div>
                      ) : (
                        <div>
                          ******
                          <EyeInvisibleOutlined
                            className={styles.pwdIcon}
                            onClick={() => setShowPwd(true)}
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    '-'
                  )}
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
          <ProCard
            title="软件路径配置"
            className="card-header-padding-top-0 card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard title="软件路径">
                  <Tooltip title={home_path} placement="topLeft">
                    {home_path}
                  </Tooltip>
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
        </Row>
      </ProCard>
      <ProCard split="horizontal">
        <Row gutter={16}>
          {clusterConfigInfo?.map((item, index) => (
            <ProCard
              title={item.group}
              key={item.key}
              className={`${
                index === clusterConfigInfo?.length - 1
                  ? 'card-header-padding-top-0 card-padding-bottom-24'
                  : 'card-padding-bottom-24'
              }`}
            >
              <Col span={24}>
                <ProCard className={styles.infoSubCard} split="vertical">
                  {item.content.map((subItem) => (
                    <ProCard title={subItem.label} key={subItem.label}>
                      {subItem.value}
                    </ProCard>
                  ))}
                </ProCard>
              </Col>
              <Space
                direction="vertical"
                size="middle"
                style={{ marginTop: 16 }}
              >
                {item?.more?.length
                  ? item?.more.map((moreItem) => (
                      <ProCard
                        className={styles.infoSubCard}
                        style={{ border: '1px solid #e2e8f3' }}
                        split="vertical"
                        key={moreItem.label}
                      >
                        <Table
                          className={`${styles.infoCheckTable}  ob-table`}
                          columns={getMoreColumns(moreItem.label)}
                          dataSource={moreItem?.parameters}
                          pagination={false}
                          scroll={{ y: 300 }}
                          rowKey="key"
                        />
                      </ProCard>
                    ))
                  : null}
              </Space>
            </ProCard>
          ))}
        </Row>
      </ProCard>
      <footer className={styles.pageFooterContainer}>
        <div className={styles.pageFooter}>
          <Space className={styles.foolterAction}>
            <Button
              onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
              data-aspm-click="c307504.d317275"
              data-aspm-desc="预检查-退出"
              data-aspm-param={``}
              data-aspm-expo
            >
              退出
            </Button>
            <Button
              onClick={prevStep}
              data-aspm-click="c307504.d317274"
              data-aspm-desc="预检查-上一步"
              data-aspm-param={``}
              data-aspm-expo
            >
              上一步
            </Button>
            <Button
              type="primary"
              onClick={handlePreCheck}
              loading={loading}
              data-aspm-click="c307504.d317273"
              data-aspm-desc="预检查-预检查"
              data-aspm-param={``}
              data-aspm-expo
            >
              预检查
            </Button>
          </Space>
        </div>
      </footer>
    </Space>
  );
}
