import { intl } from '@/utils/intl';
import React, { useEffect, useState } from 'react';
import {
  Card,
  Form,
  Input,
  Row,
  Col,
  Space,
  Radio,
  InputNumber,
} from '@oceanbase/design';
import { InfoCircleOutlined } from '@ant-design/icons';
import { some } from 'lodash';
import Password from '@/component/Password';
import MySelect from '@/component/MySelect';
import {
  SMLL_FORM_ITEM_LAYOUT,
  PASSWORD_REGEX,
  SELECT_TOKEN_SPEARATORS,
} from '@/constant';
import { validatePassword } from '@/utils';
import { PORT_MAX,PORT_MIN } from '@/constant';
// import tracert from '@/util/tracert';
import validator from 'validator';

export interface SystemConfigProps {
  form: any;
  step?: number;
  userInfo?: any;
  currentMetadbDeploymentConfig?: any;
  checkHomePathcheckStatus?: boolean;
  checkDataDircheckStatus?: boolean;
  checkLogDircheckStatus?: boolean;
  checkMachineResult?: API.ResourceCheckResult[];
  onChangeHomePath: () => void;
  onChangeDataDir: () => void;
  onChangeLogDir: () => void;
}

const SystemConfig: React.FC<SystemConfigProps> = ({
  form,
  step,
  userInfo,
  onChangeHomePath,
  onChangeDataDir,
  onChangeLogDir,
  checkMachineResult,
  checkHomePathcheckStatus,
  checkDataDircheckStatus,
  checkLogDircheckStatus,
  currentMetadbDeploymentConfig,
}) => {
  const { getFieldValue, setFieldsValue } = form;

  // 密码校验是否通过
  const [passed, setPassed] = useState<boolean>(true);
  const [devnameType, setDevnameType] = useState('AUTO');

  const [homePathcheckResult, setHomePathcheckResult] = useState<boolean>(true);
  const [dataDircheckResult, setDataDircheckResult] = useState<boolean>(true);
  const [logDircheckResult, setLogDircheckResult] = useState<boolean>(true);

  useEffect(() => {
    if (checkMachineResult && checkMachineResult?.length > 0) {
      setHomePathcheckResult(checkMachineResult[0] || true);
      setDataDircheckResult(checkMachineResult[1]);
      setLogDircheckResult(checkMachineResult[2]);
    }
  }, [checkMachineResult, checkMachineResult?.length]);

  useEffect(() => {
    if (userInfo?.username) {
      setFieldsValue({
        user: userInfo?.username,
        home_path: `/home/${userInfo?.username || 'root'}`,
      });
    }
    if (currentMetadbDeploymentConfig?.id) {
      const {
        auth,
        cluster_name,
        servers,
        // root_password,
        home_path,
        data_dir,
        log_dir,
        sql_port,
        rpc_port,
        devname,
      } = currentMetadbDeploymentConfig?.config;
      setFieldsValue({
        servers,
        user: auth?.user,
        private_key: auth?.private_key,
        username: auth?.username,
        // password: auth?.password,
        cluster_name,
        // root_password,
        home_path: home_path
          ? home_path.split('/oceanbase')[0]
          : `/home/${userInfo?.username || 'root'}`,
        data_dir: data_dir ? data_dir : '/data/1',
        log_dir: log_dir ? log_dir : '/data/log',
        sql_port,
        rpc_port,
        devname,
      });
      setDevnameType(devname || devname !== '' ? 'MANUAL' : 'AUTO');
    }
  }, [currentMetadbDeploymentConfig?.id, step, userInfo?.username]);

  const validate = (rule, values: any[], callback) => {
    if (
      values &&
      some(
        values,
        (item) =>
          // ipv4 地址
          !validator.isIP(item, '4'),
      )
    ) {
      callback(
        intl.formatMessage({
          id: 'OBD.Install.Component.SystemConfig.InvalidIpAddress',
          defaultMessage: 'IP 地址不合法',
        }),
      );

      return;
    }
    callback();
  };

  return (
    <Form
      form={form}
      scrollToFirstError={true}
      layout="vertical"
      requiredMark="optional"
      preserve={false}
      {...SMLL_FORM_ITEM_LAYOUT}
      data-aspm="c323704"
      data-aspm-desc={intl.formatMessage({
        id: 'OBD.Install.Component.SystemConfig.InstallAndDeployMetadbConfiguration',
        defaultMessage: '安装部署MetaDB配置页',
      })}
      // 扩展参数
      // data-aspm-param={tracert.stringify({
      //   // 网卡名称选择方式
      //   metadbSystemAevnameType: devnameType,
      // })}
      data-aspm-expo
    >
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            bordered={false}
            divided={false}
            title={
              <Space>
                {intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.SystemConfiguration',
                  defaultMessage: '系统配置',
                })}

                <Space
                  style={{ color: '#8592AD', fontWeight: 400, fontSize: 14 }}
                >
                  <InfoCircleOutlined />
                  {intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.ToAvoidOperatingSystemUser',
                    defaultMessage:
                      '为了避免操作系统用户冲突，请为 MetaDB 及 OCP 配置独立的操作系统用户',
                  })}
                </Space>
              </Space>
            }
          >
            <Form.Item
              name="servers"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.SelectHost',
                defaultMessage: '选择主机',
              })}
              // initialValue={servers}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterAnIpAddress',
                    defaultMessage: '请输入 IP 地址',
                  }),
                },

                {
                  validator: validate,
                },
              ]}
            >
              <MySelect
                mode="tags"
                open={false}
                tokenSeparators={SELECT_TOKEN_SPEARATORS}
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>

            <Form.Item
              name="user"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.HostUser',
                defaultMessage: '主机用户',
              })}
              initialValue={userInfo?.username || 'root'}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterAHostUser',
                    defaultMessage: '请输入主机用户',
                  }),
                },
              ]}
            >
              <Input
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>

            <Form.Item
              name="password"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.UserPassword',
                defaultMessage: '用户密码',
              })}
              extra={
                <div style={{ marginTop: 8 }}>
                  {intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.IfYouHaveSetPassword',
                    defaultMessage: '如果您已设置免密，请忽略本选项',
                  })}
                </div>
              }
            >
              <Input.Password
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>
          </Card>
        </Col>
        <Col span={24}>
          <Card
            divided={false}
            bordered={false}
            title={intl.formatMessage({
              id: 'OBD.Install.Component.SystemConfig.MetadbConfiguration',
              defaultMessage: 'MetaDB 配置',
            })}
          >
            <Form.Item
              name="cluster_name"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.ClusterName',
                defaultMessage: '集群名称',
              })}
              initialValue={'ocpmetadb'}
              // initialValue={cluster_name || "ocpmetadb"}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterAClusterName',
                    defaultMessage: '请输入集群名称',
                  }),
                },
              ]}
            >
              <Input
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>
            <Form.Item
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.RootSysPassword',
                defaultMessage: 'root@sys 密码',
              })}
              name="root_password"
              // initialValue={root_password}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterOrRandomlyGenerateThe',
                    defaultMessage: '请输入或随机生成 root@sys 密码',
                  }),
                },

                {
                  validator: validatePassword(passed),
                },
              ]}
            >
              <Password
                generatePasswordRegex={PASSWORD_REGEX}
                onValidate={(value) => {
                  setPassed(value);
                }}
              />
            </Form.Item>
            <Form.Item
              preserve={true}
              name="home_path"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.SoftwarePath',
                defaultMessage: '软件路径',
              })}
              initialValue={`/home/${userInfo?.username || 'root'}`}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterTheSoftwarePath',
                    defaultMessage: '请输入软件路径',
                  }),
                },
              ]}
              validateStatus={
                !checkHomePathcheckStatus &&
                homePathcheckResult?.check_result === false
                  ? 'error'
                  : ''
              }
              help={
                !checkHomePathcheckStatus &&
                homePathcheckResult?.check_result === false ? (
                  <div>{homePathcheckResult?.error_message?.join(',')}</div>
                ) : null
              }
            >
              <Input
                addonAfter="/oceanbase"
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
                onChange={() => {
                  onChangeHomePath();
                }}
              />
            </Form.Item>
            <Form.Item
              preserve={true}
              name="data_dir"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.DataPath',
                defaultMessage: '数据路径',
              })}
              initialValue={'/data/1'}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterADataPath',
                    defaultMessage: '请输入数据路径',
                  }),
                },
              ]}
              validateStatus={
                !checkDataDircheckStatus &&
                dataDircheckResult?.check_result === false
                  ? 'error'
                  : ''
              }
              help={
                !checkDataDircheckStatus &&
                dataDircheckResult?.check_result === false ? (
                  <div>{dataDircheckResult?.error_message?.join(',')}</div>
                ) : null
              }
            >
              <Input
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
                onChange={() => {
                  onChangeDataDir();
                }}
              />
            </Form.Item>
            <Form.Item
              preserve={true}
              name="log_dir"
              label={intl.formatMessage({
                id: 'OBD.Install.Component.SystemConfig.LogPath',
                defaultMessage: '日志路径',
              })}
              initialValue={'/data/log'}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.EnterALogPath',
                    defaultMessage: '请输入日志路径',
                  }),
                },
              ]}
              validateStatus={
                !checkLogDircheckStatus &&
                logDircheckResult?.check_result === false
                  ? 'error'
                  : ''
              }
              help={
                !checkLogDircheckStatus &&
                logDircheckResult?.check_result === false ? (
                  <div>{logDircheckResult?.error_message?.join(',')}</div>
                ) : null
              }
            >
              <Input
                placeholder={intl.formatMessage({
                  id: 'OBD.Install.Component.SystemConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
                onChange={() => {
                  onChangeLogDir();
                }}
              />
            </Form.Item>
            <Row gutter={8}>
              <Col span={6}>
                <Form.Item
                  preserve={true}
                  name="sql_port"
                  label={intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.SqlPort',
                    defaultMessage: 'sql 端口',
                  })}
                  initialValue={2881}
                  dependencies={['rpc_port']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Install.Component.SystemConfig.EnterALogPath',
                        defaultMessage: '请输入日志路径',
                      }),
                    },
                    {
                      validator: (rule, value, callback) => {
                        if (value == getFieldValue('rpc_port')) {
                          callback(
                            intl.formatMessage({
                              id: 'OBD.Install.Component.SystemConfig.TheSqlPortCannotBe',
                              defaultMessage: 'SQL 端口不可与 RPC 端口相同',
                            }),
                          );
                        } else {
                          callback();
                        }
                      },
                    },
                  ]}
                  {...{
                    labelCol: {
                      span: 24,
                    },

                    wrapperCol: {
                      span: 24,
                    },
                  }}
                >
                  <InputNumber
                    min={PORT_MIN}
                    max={PORT_MAX}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>

              <Col span={6}>
                <Form.Item
                  preserve={true}
                  name="rpc_port"
                  label={intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.RpcPort',
                    defaultMessage: 'rpc 端口',
                  })}
                  initialValue={2882}
                  dependencies={['sql_port']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Install.Component.SystemConfig.EnterALogPath',
                        defaultMessage: '请输入日志路径',
                      }),
                    },
                    {
                      validator: (rule, value, callback) => {
                        if (value == getFieldValue('sql_port')) {
                          callback(
                            intl.formatMessage({
                              id: 'OBD.Install.Component.SystemConfig.TheRpcPortCannotBe',
                              defaultMessage: 'RPC 端口不可与 SQL 端口相同',
                            }),
                          );
                        } else {
                          callback();
                        }
                      },
                    },
                  ]}
                  {...{
                    labelCol: {
                      span: 24,
                    },

                    wrapperCol: {
                      span: 24,
                    },
                  }}
                >
                  <InputNumber
                    min={PORT_MIN}
                    max={PORT_MAX}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={8}>
              <Col>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.Install.Component.SystemConfig.NicName',
                    defaultMessage: '网卡名称',
                  })}
                  name="devnameType"
                  initialValue={devnameType}
                  rules={[
                    {
                      required: true,
                    },
                  ]}
                >
                  <Radio.Group
                    style={{ width: 175 }}
                    onChange={(e) => {
                      setDevnameType(e.target.value);
                    }}
                  >
                    <Radio.Button value="AUTO">
                      {intl.formatMessage({
                        id: 'OBD.Install.Component.SystemConfig.AutomaticConfiguration',
                        defaultMessage: '自动配置',
                      })}
                    </Radio.Button>
                    <Radio.Button value="MANUAL">
                      {intl.formatMessage({
                        id: 'OBD.Install.Component.SystemConfig.ManualConfiguration',
                        defaultMessage: '手动配置',
                      })}
                    </Radio.Button>
                  </Radio.Group>
                </Form.Item>
              </Col>
              {devnameType === 'MANUAL' && (
                <Col span={6}>
                  <Form.Item
                    preserve={true}
                    name="devname"
                    label=" "
                    // initialValue={devname}
                    rules={[
                      {
                        required: devnameType === 'MANUAL',
                        message: intl.formatMessage({
                          id: 'OBD.Install.Component.SystemConfig.EnterANicName',
                          defaultMessage: '请输入网卡名称',
                        }),
                      },
                      {
                        max: 13,
                        message: intl.formatMessage({
                          id: 'OBD.Install.Component.SystemConfig.AMaximumOfCharactersCan',
                          defaultMessage: '最长可输入13个字符',
                        }),
                      },
                    ]}
                  >
                    <Input
                      style={{ width: 268 }}
                      placeholder={intl.formatMessage({
                        id: 'OBD.Install.Component.SystemConfig.EnterTheNameOfThe',
                        defaultMessage: '请输入OBServer 绑定的网卡设备名',
                      })}
                    />
                  </Form.Item>
                </Col>
              )}
            </Row>
          </Card>
        </Col>
      </Row>
    </Form>
  );
};

export default SystemConfig;
