import { intl } from '@/utils/intl';
import { Row, Col, Tooltip, Space, Table,Typography } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import type { ConnectInfoPropType } from './type';
import { componentsConfig } from '@/pages/constants';
import type { ColumnsType } from 'antd/es/table';
import styles from './index.less';
import type { DBNodeType } from './type';
import PasswordCard from '@/component/PasswordCard';
import { leftCardStyle } from '.';
import {
  oceanbaseAddonAfter,
  obproxyAddonAfter,
} from '@/constant/configuration';
interface BasicInfo {
  isNewDB: boolean;
  configInfoProp: ConnectInfoPropType;
  oceanbase: any;
  obproxy: any;
}
const { Text } = Typography;

export default function ConfigInfo({
  isNewDB,
  configInfoProp,
  oceanbase,
  obproxy,
}: BasicInfo) {
  const { userConfig, ocpNodeConfig, clusterConfig, obproxyConfig, dbNode } =
    configInfoProp;
  const obConfigInfo = clusterConfig.info;
  const obproxyConfigInfo = obproxyConfig.info;
  const ObproxyServer = () => (
    <>
      {obproxyConfigInfo.servers &&
        obproxyConfigInfo.servers.map((text: string, idx: number) => (
          <span key={idx}>
            {text}
            {idx !== obproxyConfigInfo.servers.length - 1 && <>，</>}{' '}
          </span>
        ))}
    </>
  );

  const configInfo = [
    {
      key: 'cluster',
      group: intl.formatMessage({
        id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ClusterConfiguration',
        defaultMessage: '集群配置',
      }),
      content: [
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.RootSysPassword',
            defaultMessage: 'root@sys 密码',
          }),
          colSpan: 5,
          value: (
            <Tooltip title={obConfigInfo?.root_password} placement="topLeft">
              <div className="ellipsis">{obConfigInfo?.root_password}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.SoftwarePath',
            defaultMessage: '软件路径',
          }),
          value: (
            <Tooltip
              title={obConfigInfo?.home_path + oceanbaseAddonAfter}
              placement="topLeft"
            >
              <div className="ellipsis">
                {obConfigInfo?.home_path}
                {oceanbaseAddonAfter}
              </div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.DataPath',
            defaultMessage: '数据路径',
          }),
          value: (
            <Tooltip title={obConfigInfo?.data_dir} placement="topLeft">
              <div className="ellipsis">{obConfigInfo?.data_dir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.LogPath',
            defaultMessage: '日志路径',
          }),
          value: (
            <Tooltip title={obConfigInfo?.redo_dir} placement="topLeft">
              <div className="ellipsis">{obConfigInfo?.redo_dir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.MysqlPort',
            defaultMessage: 'mysql 端口',
          }),
          colSpan: 3,
          value: obConfigInfo?.mysql_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.RpcPort',
            defaultMessage: 'rpc 端口',
          }),
          colSpan: 3,
          value: obConfigInfo?.rpc_port,
        },
      ],

      more: oceanbase?.parameters?.length
        ? [
            {
              label: componentsConfig['oceanbase'].labelName,
              parameters: oceanbase?.parameters,
            },
          ]
        : [],
    },
    {
      key: 'obproxy',
      group: intl.formatMessage({
        id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ObproxyConfiguration',
        defaultMessage: 'OBProxy 配置',
      }),
      content: [
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ObproxyNodes',
            defaultMessage: 'OBProxy 节点',
          }),
          colSpan: 6,
          value: (
            <Tooltip title={<ObproxyServer />} placement="topLeft">
              <div className="ellipsis">
                <ObproxyServer />
              </div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.SoftwarePath',
            defaultMessage: '软件路径',
          }),
          colSpan: 6,
          value: (
            <Tooltip
              title={obproxyConfigInfo?.home_path + obproxyAddonAfter}
              placement="topLeft"
            >
              <div className="ellipsis">
                {obproxyConfigInfo?.home_path}
                {obproxyAddonAfter}
              </div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.SqlPort',
            defaultMessage: 'SQL 端口',
          }),
          colSpan: 6,
          value: (
            <Tooltip title={obproxyConfigInfo?.listen_port} placement="topLeft">
              <div className="ellipsis">{obproxyConfigInfo?.listen_port}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.PortExporter',
            defaultMessage: 'Exporter 端口',
          }),
          colSpan: 6,
          value: (
            <Tooltip
              title={obproxyConfigInfo?.prometheus_listen_port}
              placement="topLeft"
            >
              <div className="ellipsis">
                {obproxyConfigInfo?.prometheus_listen_port}
              </div>
            </Tooltip>
          ),
        },
      ],

      more: obproxy?.parameters?.length
        ? [
            {
              label: componentsConfig['obproxy'].labelName,
              parameters: obproxy?.parameters,
            },
          ]
        : [],
    },
  ];

  const getMoreColumns = (label: string) => {
    const columns: ColumnsType<API.MoreParameter> = [
      {
        title: label,
        dataIndex: 'key',
        render: (text) => text,
      },
      {
        title: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ParameterValue',
          defaultMessage: '参数值',
        }),
        dataIndex: 'value',
        render: (text, record) =>
          record.adaptive
            ? intl.formatMessage({
                id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.AutomaticAllocation',
                defaultMessage: '自动分配',
              })
            : text || '-',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.Introduction',
          defaultMessage: '介绍',
        }),
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

  const dbNodeColums: ColumnsType<DBNodeType> = [
    {
      title: intl.formatMessage({
        id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ZoneName',
        defaultMessage: 'Zone 名称',
      }),
      dataIndex: 'name',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ObServerNodes',
        defaultMessage: 'OB Server 节点',
      }),
      dataIndex: 'servers',
      render: (_, record) => (
        <>
          {_.map((item: { ip: string }, idx: number) => (
            <span key={idx}>
              {item.ip}
              {idx !== _.length - 1 && <span> ，</span>}
            </span>
          ))}
        </>
      ),
    },
    {
      title: intl.formatMessage({
        id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.RootServerNodes',
        defaultMessage: 'Root Server 节点',
      }),
      dataIndex: 'rootservice',
    },
  ];

  return (
    <ProCard className={styles.pageCard} split="horizontal">
      <Row gutter={16}>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.DeployUserConfiguration',
            defaultMessage: '部署用户配置',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={18}>
            <ProCard className={styles.infoSubCard} split="vertical">
              <ProCard
                style={leftCardStyle}
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.Username',
                  defaultMessage: '用户名',
                })}
              >
                 <Text
                    style={{ width: 200 }}
                    ellipsis={{ tooltip: userConfig.user }}
                  >
                    {userConfig.user}
                  </Text>
              </ProCard>
              <PasswordCard password={userConfig.password} />
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.SshPort',
                  defaultMessage: 'SSH端口',
                })}
              >
                {userConfig.port || '-'}
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.OcpNodeConfiguration',
            defaultMessage: 'OCP 节点配置',
          })}
          className="card-padding-bottom-24"
        >
          <Row gutter={16}>
            <Col span={ocpNodeConfig.length * 6 || 0}>
              <ProCard className={styles.infoSubCard} split="vertical">
                {ocpNodeConfig &&
                  ocpNodeConfig.map((server, idx) => (
                    <ProCard
                      style={idx === 0 ? leftCardStyle : {}}
                      key={idx}
                      title={`节点${idx + 1}`}
                    >
                      {server}
                    </ProCard>
                  ))}
              </ProCard>
            </Col>
          </Row>
        </ProCard>
        <ProCard
          title={intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.DatabaseNodeConfiguration',
            defaultMessage: '数据库节点配置',
          })}
        >
          <Table
            rowKey="id"
            className={styles.dbTable}
            pagination={false}
            columns={dbNodeColums}
            dataSource={dbNode}
          />
        </ProCard>
        <ProCard split="horizontal">
          <Row gutter={16}>
            {configInfo?.map((item, index) => {
              return (
                <ProCard
                  title={item.group}
                  key={item.key}
                  className={`${
                    index === configInfo?.length - 1
                      ? 'card-header-padding-top-0 card-padding-bottom-24'
                      : 'card-padding-bottom-24'
                  }`}
                >
                  <Col span={24}>
                    <ProCard className={styles.infoSubCard} split="vertical">
                      {item.content.map((subItem) => (
                        <ProCard
                          title={subItem.label}
                          key={subItem.label}
                          colSpan={subItem.colSpan}
                        >
                          {subItem.value}
                        </ProCard>
                      ))}
                    </ProCard>
                  </Col>
                  {item?.more?.length ? (
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{ marginTop: 16 }}
                    >
                      {item?.more.map((moreItem) => (
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
                      ))}
                    </Space>
                  ) : null}
                </ProCard>
              );
            })}
          </Row>
        </ProCard>
      </Row>
    </ProCard>
  );
}
