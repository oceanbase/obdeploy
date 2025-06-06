import InputPort from '@/component/InputPort';
import {
  commonStyle,
  configServerComponent,
  grafanaComponent,
  obagentComponent,
  obproxyComponent,
  prometheusComponent,
} from '@/pages/constants';
import { intl } from '@/utils/intl';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { ProForm } from '@ant-design/pro-components';
import { Col, Row, Tooltip } from 'antd';
import type { FormInstance } from 'antd/lib/form';

interface ComponentsPortProps {
  lowVersion?: boolean;
  selectedConfig: string[];
  form: FormInstance;
}

export default function ComponentsPort({
  selectedConfig,
  lowVersion = false,
  form,
}: ComponentsPortProps) {
  const PortOcpExpressFormValue = ProForm.useWatch(
    ['ocpexpress', 'port'],
    form,
  );
  const PortListentFormValue = ProForm.useWatch(
    ['obconfigserver', 'listen_port'],
    form,
  );

  return (
    <Row>
      {(selectedConfig?.includes(obproxyComponent) ||
        selectedConfig?.includes('obproxy-ce')) && (
        <>
          <Col span={6}>
            <InputPort
              name={['obproxy', 'listen_port']}
              label={intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PortObproxySql',
                defaultMessage: 'OBProxy SQL 端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Col>
          <Col span={6}>
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
                    <QuestionCircleOutlined style={{ marginLeft: 4 }} />
                  </Tooltip>
                </>
              }
              fieldProps={{ style: commonStyle }}
            />
          </Col>
          <Col span={6}>
            <InputPort
              name={['obproxy', 'rpc_listen_port']}
              label={intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PortObproxyRpc',
                defaultMessage: 'OBProxy RPC 端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Col>
        </>
      )}

      {selectedConfig?.includes(obagentComponent) && (
        <>
          <Col span={6}>
            <InputPort
              name={['obagent', 'monagent_http_port']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ObagentMonitoringServicePort',
                defaultMessage: 'OBAgent 监控服务端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Col>
          <Col span={6}>
            <InputPort
              name={['obagent', 'mgragent_http_port']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ObagentManageServicePorts',
                defaultMessage: 'OBAgent 管理服务端口',
              })}
              fieldProps={{ style: commonStyle }}
            />
          </Col>
        </>
      )}
      {selectedConfig?.includes(configServerComponent) && !lowVersion && (
        <>
          {selectedConfig?.includes(configServerComponent) && (
            <Col span={6}>
              <InputPort
                name={['obconfigserver', 'listen_port']}
                label={intl.formatMessage({
                  id: 'OBD.Obdeploy.ClusterConfig.ObconfigserverServicePort',
                  defaultMessage: 'OBConfigserver 服务端口',
                })}
                fieldProps={{ style: commonStyle }}
                portError={
                  PortOcpExpressFormValue === PortListentFormValue &&
                  intl.formatMessage(
                    {
                      id: 'OBD.pages.components.InstallConfig.PortOccupied',
                      defaultMessage:
                        '端口${PortListentFormValue}已被占用，请修改',
                    },
                    { PortListentFormValue: PortListentFormValue },
                  )
                }
              />
            </Col>
          )}
        </>
      )}
      {selectedConfig?.includes(prometheusComponent) && (
        <Col span={6}>
          <InputPort
            name={['prometheus', 'port']}
            label={intl.formatMessage({
              id: 'OBD.Obdeploy.ClusterConfig.PrometheusServicePort',
              defaultMessage: 'Prometheus 服务端口',
            })}
            fieldProps={{ style: commonStyle }}
          />
        </Col>
      )}
      {selectedConfig.includes(grafanaComponent) && (
        <Col span={6}>
          <InputPort
            name={['grafana', 'port']}
            label={intl.formatMessage({
              id: 'OBD.Obdeploy.ClusterConfig.GrafanaServicePort',
              defaultMessage: 'Grafana 服务端口',
            })}
            fieldProps={{ style: commonStyle }}
          />
        </Col>
      )}
    </Row>
  );
}
