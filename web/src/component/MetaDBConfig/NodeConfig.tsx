import { commonInputStyle, commonStyle } from '@/pages/constants';
import { dnsValidator, ocpServersValidator,  hybridAddressValidator } from '@/utils';
import { intl } from '@/utils/intl';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import {
  ProForm,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { Col, message, Row, Select, Space, Tooltip } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import styles from './index.less';

export default function NodeConfig({ form }: { form: FormInstance<any> }) {
  const { isSingleOcpNode, setIsSingleOcpNode } = useModel('ocpInstallData');
  const [show, setShow] = useState<boolean>(false);
  const selectChange = (value: string[]) => {
    if (isSingleOcpNode === true && value.length > 1) {
      setIsSingleOcpNode(false);
    } else if (value.length === 1) {
      setIsSingleOcpNode(true);
    } else if (value.length === 0) {
      setIsSingleOcpNode(undefined);
    }
    if (value.find((item) => item === '127.0.0.1')) {
      message.warning('依据 OceanBase 最佳实践，建议使用非 127.0.0.1 IP 地址');
    }
  };
  const {
    ocpConfigData: {
      components: { ocpserver },
    },
  } = useModel('global');
  const dns = ProForm.useWatch(['ocpserver', 'dnsType'], form);

  useEffect(() => {
    if (ocpserver?.dns !== undefined || ocpserver?.vip_address !== undefined) {
      setShow(true);
    }
  }, []);

  return (
    <div>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.NodeConfig.OcpNodeConfiguration',
          defaultMessage: 'OCP 节点配置',
        })}
      </p>

      <Row>
        <ProForm.Item
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.MetaDBConfig.NodeConfig.PleaseEnter',
                defaultMessage: '请输入正确的 OCP 节点',
              }),
            },
            {
              validator: ocpServersValidator,
            },
          ]}
          label={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.NodeConfig.SelectHost',
            defaultMessage: '选择主机',
          })}
          style={{ ...commonInputStyle, marginRight: 12 }}
          name={['ocpserver', 'servers']}
        >
          <Select
            mode="tags"
            onBlur={() => form.validateFields([['ocpserver', 'servers']])}
            onChange={selectChange}
          />
        </ProForm.Item>
      </Row>
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
              id: 'OBD.pages.components.NodeConfig.B4449035',
              defaultMessage:
                '主要用于用户访问 OCP，建议部署多节点 OCP 时提供 VIP/DNS 地址，避免后期更改 OCP 访问地址（ocp.site.url）。若不配置，系统默认选择第一个 IP 地址设置连接串。',
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
                name={['ocpserver', 'dnsType']}
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
                {dns === 'vip' ? (
                  <Col span={8}>
                    <ProFormText
                      name={['ocpserver', 'vip_address']}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.B4449039',
                        defaultMessage: 'IP 地址',
                      })}
                      formItemProps={{
                        rules: [
                          {
                            required: true,
                            message: '此项是必填项',
                          },
                          {
                            validator: (_: any, value: string[]) =>
                              hybridAddressValidator(_, [value], 'OBServer'),
                          },
                        ],
                      }}
                    />
                  </Col>
                ) : (
                  <Col span={8}>
                    <ProFormText
                      name={['ocpserver', 'dns']}
                      label={
                        <Tooltip
                          title={intl.formatMessage({
                            id: 'OBD.pages.components.NodeConfig.B4449034',
                            defaultMessage:
                              '用于指向 VIP 及端口的配置信息，平台未提供 VIP 与域名的映射关系，需自行准备域名解析服务。',
                          })}
                        >
                          {intl.formatMessage({
                            id: 'OBD.pages.components.NodeConfig.B4449033',
                            defaultMessage: '域名',
                          })}
                          <QuestionCircleOutlined style={{ marginLeft: 4 }} />
                        </Tooltip>
                      }
                      formItemProps={{
                        rules: [
                          {
                            required: true,
                            message: '此项是必填项',
                          },
                          {
                            validator: (_: any, value: string[]) =>
                              dnsValidator(_, [value]),
                          },
                        ],
                      }}
                    />
                  </Col>
                )}

                {dns === 'vip' && (
                  <Col span={8}>
                    <ProFormDigit
                      name={['ocpserver', 'vip_port']}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.B4449032',
                        defaultMessage: '访问端口',
                      })}
                      initialValue={2883}
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
    </div>
  );
}
