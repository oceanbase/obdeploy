import InputPort from '@/component/InputPort';
import {
  commonStyle,
  configServerComponent,
  obagentComponent,
  obproxyComponent,
  ocpexpressComponent,
} from '@/pages/constants';
import { intl } from '@/utils/intl';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { Row, Space, Tooltip } from 'antd';

interface ComponentsPortProps {
  lowVersion?: boolean;
  selectedConfig: string[];
}

export default function ComponentsPort({
  selectedConfig,
  lowVersion = false,
}: ComponentsPortProps) {
  return (
    <>
      {(selectedConfig.includes(obproxyComponent) ||
        selectedConfig.includes('obproxy-ce')) && (
        <Row>
          <Space size="large">
            <InputPort
              name={['obproxy', 'listen_port']}
              label={intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PortObproxySql',
                defaultMessage: 'OBProxy SQL 端口',
              })}
              fieldProps={{ style: commonStyle }}
            />

            <InputPort
              name={['obproxy', 'prometheus_listen_port']}
              label={
                <>
                  {intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PortObproxyExporter',
                    defaultMessage: 'OBProxy Exporter 端口',
                  })}

                  <Tooltip
                    title={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PortObproxyOfExporterIs',
                      defaultMessage:
                        'OBProxy 的 Exporter 端口，用于 Prometheus 拉取 OBProxy 监控数据。',
                    })}
                  >
                    <QuestionCircleOutlined className="ml-10" />
                  </Tooltip>
                </>
              }
              fieldProps={{ style: commonStyle }}
            />
            <InputPort
              name={['obproxy', 'rpc_listen_port']}
              label={intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PortObproxyRpc',
                defaultMessage: 'OBProxy RPC 端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Space>
        </Row>
      )}
      {selectedConfig.includes(obagentComponent) && (
        <Row>
          <Space size="large">
            <InputPort
              name={['obagent', 'monagent_http_port']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ObagentMonitoringServicePort',
                defaultMessage: 'OBAgent 监控服务端口',
              })}
              fieldProps={{ style: commonStyle }}
            />

            <InputPort
              name={['obagent', 'mgragent_http_port']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ObagentManageServicePorts',
                defaultMessage: 'OBAgent 管理服务端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Space>
        </Row>
      )}
      {(selectedConfig.includes(ocpexpressComponent) ||
        selectedConfig.includes(configServerComponent)) &&
        !lowVersion && (
          <Row>
            <Space size="large">
              {selectedConfig.includes(ocpexpressComponent) && (
                <InputPort
                  name={['ocpexpress', 'port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PortOcpExpress',
                    defaultMessage: 'OCP Express 端口',
                  })}
                  fieldProps={{ style: commonStyle }}
                />
              )}

              {selectedConfig.includes(configServerComponent) && (
                <InputPort
                  name={['obconfigserver', 'listen_port']}
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.ClusterConfig.ObconfigserverServicePort',
                    defaultMessage: 'OBConfigserver 服务端口',
                  })}
                  fieldProps={{ style: commonStyle }}
                />
              )}
            </Space>
          </Row>
        )}
    </>
  );
}
