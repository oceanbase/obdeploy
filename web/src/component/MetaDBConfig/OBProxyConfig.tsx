import {
  commonInputStyle,
  commonPortStyle,
  commonStyle,
} from '@/pages/constants';
import { intl } from '@/utils/intl';
import {
  ProCard,
  ProForm,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { useUpdateEffect } from 'ahooks';
import { Col, Input, message, Row, Space, Tooltip } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';

import { obproxyAddonAfter, PARAMETER_TYPE } from '@/constant/configuration';
import ConfigTable from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import {
  dnsValidator,
  getErrorInfo,
  ocpServersValidator,
  serversValidator,
} from '@/utils';
import { formatMoreConfig } from '@/utils/helper';
import useRequest from '@/utils/useRequest';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import InputPort from '../InputPort';
import styles from './index.less';
export default function OBProxyConfig({
  form,
  parameterRules,
}: {
  form: FormInstance<any>;
  parameterRules: any;
}) {
  const {
    ocpConfigData,
    proxyMoreConfig,
    setProxyMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { isShowMoreConfig, setIsShowMoreConfig, deployUser, useRunningUser } =
    useModel('ocpInstallData');
  const { components = {} } = ocpConfigData || {};
  const { obproxy = {} } = components;
  const [proxyMoreLoading, setProxyMoreLoading] = useState(false);
  const { run: getMoreParamsters } = useRequest(queryComponentParameters);
  const getInitialParameters = (
    currentComponent: string,
    dataSource: API.MoreParameter[],
    data: API.NewParameterMeta[],
  ) => {
    const currentComponentNameConfig = data?.filter(
      (item) => item.component === currentComponent,
    )?.[0];
    if (currentComponentNameConfig) {
      const parameters: any = {};
      currentComponentNameConfig.configParameter.forEach((item) => {
        let parameter = {
          ...item,
          key: item.name,
          params: {
            value: item.default,
            adaptive: item.auto,
            auto: item.auto,
            require: item.require,
            type: item.type,
          },
        };
        dataSource?.some((dataItem) => {
          if (item.name === dataItem.key) {
            parameter = {
              key: dataItem.key,
              description: parameter.description,
              params: {
                ...parameter.params,
                ...dataItem,
              },
            };
            return true;
          }
          return false;
        });
        if (
          (parameter.params.type === PARAMETER_TYPE.capacity ||
            parameter.params.type === PARAMETER_TYPE.capacityMB) &&
          parameter.params.value == '0'
        ) {
          parameter.params.value += 'GB';
        }
        parameters[item.name] = parameter;
      });
      return parameters;
    } else {
      return undefined;
    }
  };

  const getProxyMoreParamsters = async () => {
    setProxyMoreLoading(true);
    try {
      const { success, data } = await getMoreParamsters(
        {},
        {
          filters: [
            {
              component: obproxy?.component,
              version: obproxy?.version,
              is_essential_only: true,
            },
          ],
        },
      );
      if (success) {
        const newClusterMoreConfig = formatMoreConfig(data?.items);
        setProxyMoreConfig(newClusterMoreConfig);
        form.setFieldsValue({
          obproxy: {
            parameters: getInitialParameters(
              obproxy?.component,
              obproxy?.parameters,
              newClusterMoreConfig,
            ),
          },
        });
      }
    } catch (e: any) {
      setIsShowMoreConfig(false);
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    }
    setProxyMoreLoading(false);
  };

  const handleCluserMoreChange = (checked) => {
    setIsShowMoreConfig(checked);
    if (!proxyMoreConfig?.length) {
      getProxyMoreParamsters();
    }
  };

  useUpdateEffect(() => {
    const homePath =
      !useRunningUser && deployUser === 'root'
        ? `/${deployUser}`
        : `/home/${deployUser}`;
    form.setFieldValue(['obproxy', 'home_path'], homePath);
  }, [deployUser]);
  const [show, setShow] = useState<boolean>(false);
  const [cluserMoreChange, setCluserMoreChange] = useState<boolean>(false);
  const dns = ProForm.useWatch(['obproxy', 'dnsType'], form);

  useEffect(() => {
    if (obproxy?.dns !== undefined || obproxy?.vip_address !== undefined) {
      setShow(true);
    }
  }, []);

  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.OBProxyConfig.ObproxyConfiguration',
        defaultMessage: 'OBProxy 配置',
      })}
      bodyStyle={{ paddingBottom: 24 }}
      className={styles.proxyContainer}
    >
      <ProFormSelect
        mode="tags"
        name={['obproxy', 'servers']}
        fieldProps={{ style: commonInputStyle }}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
          {
            validator: ocpServersValidator,
            validateTrigger: 'onBlur',
          },
        ]}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.OBProxyConfig.ObproxyNodes',
          defaultMessage: 'OBProxy 节点',
        })}
        onChange={(value) => {
          if (value.find((item) => item === '127.0.0.1')) {
            message.warning(
              intl.formatMessage({
                id: 'OBD.component.MetaDBConfig.DataBaseNodeConfig.B663133E',
                defaultMessage:
                  '依据 OceanBase 最佳实践，建议使用非 127.0.0.1 IP 地址',
              }),
            );
          }
        }}
      />
      <div
        style={{
          background: '#f8fafe',
          marginBottom: 16,
          padding: 16,
        }}
      >
        <Space size={8} onClick={() => setShow(!show)}>
          {show ? <CaretDownOutlined /> : <CaretRightOutlined />}

          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.pages.components.obproxyConfig.D42DEEB0',
              defaultMessage:
                '主要用于 OCP 访问 MetaDB 集群，建议部署多节点 OBProxy 时提供 VIP/DNS 地址，避免后期更改 OBProxy 访问地址。若不配置，系统默认选择第一个 IP 地址设置连接串。',
            })}
          >
            <span>
              {intl.formatMessage({
                id: 'OBD.pages.components.obproxyConfig.D42DEEB1',
                defaultMessage: '负载均衡管理',
              })}
            </span>
            <QuestionCircleOutlined style={{ marginLeft: 4 }} />
          </Tooltip>
        </Space>
        {show && (
          <Row gutter={[8, 0]} style={{ marginTop: 24 }}>
            <Col span={8}>
              <ProFormSelect
                mode="single"
                name={['obproxy', 'dnsType']}
                label={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.B4449036',
                  defaultMessage: '访问方式',
                })}
                placeholder={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.PleaseSelect',
                  defaultMessage: '请选择',
                })}
                options={[
                  {
                    label: intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.B4449037',
                      defaultMessage: 'VIP',
                    }),
                    value: 'vip',
                  },
                  {
                    label: intl.formatMessage({
                      id: 'OBD.pages.components.NodeConfig.B4449038',
                      defaultMessage: 'DNS（域名）',
                    }),
                    value: 'dns',
                  },
                ]}
              />
            </Col>
            {dns !== undefined && (
              <>
                <Col span={8}>
                  <ProFormText
                    name={
                      dns === 'vip'
                        ? ['obproxy', 'vip_address']
                        : ['obproxy', 'dns']
                    }
                    label={
                      dns === 'vip' ? (
                        intl.formatMessage({
                          id: 'OBD.pages.components.NodeConfig.B4449039',
                          defaultMessage: 'IP 地址',
                        })
                      ) : (
                        <Tooltip
                          title={intl.formatMessage({
                            id: 'OBD.pages.components.obproxyConfig.D42DEEB0',
                            defaultMessage:
                              '主要用于 OCP 访问 MetaDB 集群，建议部署多节点 OBProxy 时提供 VIP/DNS 地址，避免后期更改 OBProxy 访问地址。若不配置，系统默认选择第一个 IP 地址设置连接串。',
                          })}
                        >
                          {intl.formatMessage({
                            id: 'OBD.pages.components.NodeConfig.B4449033',
                            defaultMessage: '域名',
                          })}
                          <QuestionCircleOutlined style={{ marginLeft: 4 }} />
                        </Tooltip>
                      )
                    }
                    formItemProps={{
                      rules: [
                        {
                          required: true,
                          message: '此项是必填项',
                        },
                        ...[
                          dns === 'vip'
                            ? {
                                validator: (_: any, value: string[]) =>
                                  serversValidator(_, [value], 'OBServer'),
                              }
                            : {
                                validator: (_: any, value: string[]) =>
                                  dnsValidator(_, [value]),
                              },
                        ],
                      ],
                    }}
                  />
                </Col>
                {dns === 'vip' && (
                  <Col span={8}>
                    <ProFormDigit
                      name={['obproxy', 'vip_port']}
                      initialValue={2883}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.B4449032',
                        defaultMessage: '访问端口',
                      })}
                      fieldProps={{ style: commonStyle }}
                      placeholder={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.PleaseEnter',
                        defaultMessage: '请输入',
                      })}
                    />
                  </Col>
                )}
              </>
            )}
          </Row>
        )}
      </div>
      <Row>
        <Space size="large">
          <InputPort
            fieldProps={{ style: commonPortStyle }}
            name={['obproxy', 'listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.SqlPort',
              defaultMessage: 'SQL 端口',
            })}
          />
          <InputPort
            fieldProps={{ style: commonPortStyle }}
            name={['obproxy', 'prometheus_listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PortExporter',
              defaultMessage: 'Exporter 端口',
            })}
          />
        </Space>
      </Row>
      <ProForm.Item
        name={['obproxy', 'home_path']}
        style={commonInputStyle}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.OBProxyConfig.SoftwarePath',
          defaultMessage: '软件路径',
        })}
      >
        <Input addonAfter={<span>{obproxyAddonAfter}</span>} />
      </ProForm.Item>
      <div className={styles.moreSwitch}>
        <Space
          size={8}
          onClick={() => {
            setCluserMoreChange(!cluserMoreChange);
            handleCluserMoreChange(!cluserMoreChange);
          }}
          style={{
            fontSize: 16,
          }}
        >
          {cluserMoreChange ? <CaretDownOutlined /> : <CaretRightOutlined />}
          <span style={{ width: 150 }}>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.MoreConfigurations',
              defaultMessage: '更多配置',
            })}
          </span>
        </Space>
      </div>
      <ConfigTable
        parameterRules={parameterRules}
        dataSource={proxyMoreConfig}
        showVisible={isShowMoreConfig}
        loading={proxyMoreLoading}
      />
    </ProCard>
  );
}
