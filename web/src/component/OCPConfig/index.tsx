import { intl } from '@/utils/intl';
import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Row, Col, Descriptions } from '@oceanbase/design';
import { some } from 'lodash';
import { FORM_ITEM_SMALL_LAYOUT, SELECT_TOKEN_SPEARATORS } from '@/constant';
import MyInput from '@/component/MyInput';
import Password from '@/component/Password';
import MySelect from '@/component/MySelect';
import ContentWithQuestion from '@/component/ContentWithQuestion';
// import { validatePassword } from '@/utils';
// import tracert from '@/util/tracert';
import validator from 'validator';

export interface OCPConfigProps {
  form: any;
  hosts?: string[];
  userInfo?: any;
  createOcp?: any;
  metadbType?: string;
  clusterName?: string;
  currentOcpDeploymentConfig: any;
}

const OCPConfig: React.FC<OCPConfigProps> = ({
  form,
  hosts,
  userInfo,
  clusterName,
  createOcp,
  metadbType = 'new',
  currentOcpDeploymentConfig,
}) => {
  const { getFieldsValue, setFieldsValue } = form;
  const [adminPasswordPassed, setAdminPasswordPassed] = useState(true);
  const [tenantPasswordPassed, setTenantPasswordPassed] = useState(true);
  const [passed, setPassed] = useState(true);

  const { user } = getFieldsValue();

  useEffect(() => {
    if (userInfo?.username) {
      const { home_path } = getFieldsValue();

      setFieldsValue({
        user: userInfo?.username,
        home_path:
          !home_path || home_path === `/home/${userInfo?.username || 'root'}`
            ? `/home/${userInfo?.username || 'root'}`
            : home_path.split('/ocp')[0],
      });
    }

    if (currentOcpDeploymentConfig && !createOcp && !user && !clusterName) {
      const {
        auth,
        appname,
        // admin_password,
        meta_tenant,
        monitor_tenant,
        servers,
        home_path,
        server_port,
      } = currentOcpDeploymentConfig;

      setFieldsValue({
        hosts: servers || hosts,
        user: auth?.user,
        // password: auth?.password,
        appname: clusterName ? `${clusterName}-OCP` : appname || 'OCP',
        // admin_password,
        meta_tenant_name: meta_tenant?.name?.tenant_name,
        // tenantPassword: meta_tenant?.password,
        // monitorPassword: monitor_tenant?.password,
        monitor_tenant_name: monitor_tenant?.name?.tenant_name,
        home_path:
          !home_path || home_path === `/home/${userInfo?.username || 'root'}`
            ? `/home/${userInfo?.username || 'root'}`
            : home_path.split('/ocp')[0],
        server_port: server_port || 8080,
        confirmTenantPassword: meta_tenant?.password,
        confirmMonitorPassword: monitor_tenant?.password,
      });
    } else if (hosts) {
      setFieldsValue({
        hosts,
      });
    }
  }, [
    currentOcpDeploymentConfig,
    createOcp,
    hosts,
    clusterName,
    userInfo?.username,
  ]);

  const validateConfirmTenantPassword = (rule, value, callback) => {
    const { tenantPassword } = getFieldsValue();
    if (value && value !== tenantPassword) {
      callback(
        intl.formatMessage({
          id: 'OBD.component.OCPConfig.ThePasswordsEnteredTwiceAre',
          defaultMessage: '两次输入的密码不一致，请重新输入',
        }),
      );
    } else {
      callback();
    }
  };

  const validateConfirmMonitorPassword = (rule, value, callback) => {
    const { monitorPassword } = getFieldsValue();
    if (value && value !== monitorPassword) {
      callback(
        intl.formatMessage({
          id: 'OBD.component.OCPConfig.ThePasswordsEnteredTwiceAre',
          defaultMessage: '两次输入的密码不一致，请重新输入',
        }),
      );
    } else {
      callback();
    }
  };

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
          id: 'OBD.component.OCPConfig.InvalidIpAddress',
          defaultMessage: 'IP 地址不合法',
        }),
      );

      return;
    }
    callback();
  };

  const onFinish = (values) => {
  };

  return (
    <Form
      form={form}
      onFinish={onFinish}
      name="ocpConfig"
      preserve={true}
      layout="vertical"
      scrollToFirstError={true}
      requiredMark="optional"
    >
      <Row gutter={[24, 16]}>
        {metadbType === 'old' && (
          <Col span={24}>
            <Card
              title={intl.formatMessage({
                id: 'OBD.component.OCPConfig.SystemConfiguration',
                defaultMessage: '系统配置',
              })}
              divided={false}
              bordered={false}
            >
              <Form.Item
                {...FORM_ITEM_SMALL_LAYOUT}
                name="hosts"
                label={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.SelectHost',
                  defaultMessage: '选择主机',
                })}
                // initialValue={servers || hosts}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.component.OCPConfig.EnterAnIpAddress',
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
                    id: 'OBD.component.OCPConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  })}
                />
              </Form.Item>
              <Form.Item
                name="user"
                label={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.HostUser',
                  defaultMessage: '主机用户',
                })}
                {...FORM_ITEM_SMALL_LAYOUT}
                // initialValue={auth?.user}
                extra={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.PleaseProvideUsersOnThe',
                  defaultMessage:
                    '请提供操作系统上用户以便安装程序进行自动化配置',
                })}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.component.OCPConfig.EnterAnAdministratorAccount',
                      defaultMessage: '请输入管理员账号',
                    }),
                  },
                ]}
              >
                <MyInput />
              </Form.Item>
              <Form.Item
                name="password"
                label={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.UserPassword',
                  defaultMessage: '用户密码',
                })}
                // initialValue={auth?.password}
                {...FORM_ITEM_SMALL_LAYOUT}
                extra={
                  <div style={{ marginTop: 8 }}>
                    {intl.formatMessage({
                      id: 'OBD.component.OCPConfig.IfYouHaveSetPassword',
                      defaultMessage: '如果您已设置免密，请忽略本选项',
                    })}
                  </div>
                }
              >
                <MyInput.Password
                  placeholder={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  })}
                />
              </Form.Item>
            </Card>
          </Col>
        )}

        <Col span={24}>
          <Card
            divided={false}
            bordered={false}
            title={
              metadbType === 'new' ? (
                <div>
                  {intl.formatMessage({
                    id: 'OBD.component.OCPConfig.OcpServiceConfiguration',
                    defaultMessage: 'OCP 服务配置',
                  })}
                </div>
              ) : (
                <div>
                  {intl.formatMessage({
                    id: 'OBD.component.OCPConfig.ServiceConfiguration',
                    defaultMessage: '服务配置',
                  })}
                </div>
              )
            }
          >
            {metadbType === 'new' && (
              <Form.Item
                {...FORM_ITEM_SMALL_LAYOUT}
                name="hosts"
                label={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.SelectHost',
                  defaultMessage: '选择主机',
                })}
                // initialValue={servers || hosts}
                rules={[
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.component.OCPConfig.EnterAnIpAddress',
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
                  disabled={true}
                  tokenSeparators={SELECT_TOKEN_SPEARATORS}
                  placeholder={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  })}
                />
              </Form.Item>
            )}

            <Form.Item
              name="appname"
              label={intl.formatMessage({
                id: 'OBD.component.OCPConfig.ClusterName',
                defaultMessage: '集群名称',
              })}
              initialValue={clusterName ? `${clusterName}-OCP` : 'OCP'}
              {...FORM_ITEM_SMALL_LAYOUT}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.component.OCPConfig.EnterAClusterName',
                    defaultMessage: '请输入集群名称',
                  }),
                },
              ]}
            >
              <Input
                placeholder={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>
            <Form.Item
              name="admin_password"
              // initialValue={admin_password}
              label={
                <ContentWithQuestion
                  content={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.AdminPassword',
                    defaultMessage: 'Admin 密码',
                  })}
                  tooltip={{
                    title: intl.formatMessage({
                      id: 'OBD.component.OCPConfig.OcpPlatformAdministratorAccountPassword',
                      defaultMessage: 'OCP 平台管理员账号密码',
                    }),
                  }}
                />
              }
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.component.OCPConfig.EnterAPassword',
                    defaultMessage: '请输入密码',
                  }),
                },
                // {
                //   // 只对新密码进行密码校验，旧密码不做校验，避免老数据密码格式校验不通过时无法修改密码
                //   // validator: validatePassword(adminPasswordPassed),
                // },
              ]}
              {...FORM_ITEM_SMALL_LAYOUT}
            >
              <Password onValidate={setAdminPasswordPassed} />
            </Form.Item>
            <Form.Item
              name="home_path"
              label={intl.formatMessage({
                id: 'OBD.component.OCPConfig.SoftwarePath',
                defaultMessage: '软件路径',
              })}
              initialValue={`/home/${userInfo?.username || 'root'}`}
              // initialValue={!home_path ? `/home/${userInfo?.username || 'root'}` : (home_path !== `/home/${userInfo?.username || 'root'}`
              //   ? home_path
              // : home_path.split('/ocp')[0])}
              {...FORM_ITEM_SMALL_LAYOUT}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.component.OCPConfig.EnterTheSoftwarePath',
                    defaultMessage: '请输入软件路径',
                  }),
                },
              ]}
            >
              <Input
                addonAfter="/ocp"
                placeholder={intl.formatMessage({
                  id: 'OBD.component.OCPConfig.PleaseEnter',
                  defaultMessage: '请输入',
                })}
              />
            </Form.Item>
            <Row gutter={8}>
              <Col>
                <Form.Item
                  name="server_port"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.ServicePort',
                    defaultMessage: '服务端口',
                  })}
                  initialValue={8080}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterAServicePort',
                        defaultMessage: '请输入服务端口',
                      }),
                    },
                  ]}
                >
                  <Input
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                  />
                </Form.Item>
              </Col>

              <Col>
                <Form.Item
                  name="ocpagentPort"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.PortOcpagent',
                    defaultMessage: 'ocpagent 端口',
                  })}
                  initialValue={62888}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterPortOcpagent',
                        defaultMessage: '请输入 ocpagent 端口',
                      }),
                    },
                  ]}
                >
                  <Input
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                  />
                </Form.Item>
              </Col>
              <Col>
                <Form.Item
                  name="monitorPort"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.OcpagentMonitoringPort',
                    defaultMessage: 'ocpagent 监控端口',
                  })}
                  initialValue={62889}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterOcpagentMonitoringPort',
                        defaultMessage: '请输入 ocpagent 监控端口',
                      }),
                    },
                  ]}
                >
                  <Input
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                  />
                </Form.Item>
              </Col>
            </Row>
            {/* </Form> */}
          </Card>
        </Col>
        <Col span={24}>
          <Card
            divided={false}
            bordered={false}
            title={intl.formatMessage({
              id: 'OBD.component.OCPConfig.MetadataTenantConfiguration',
              defaultMessage: '元信息租户配置',
            })}
          >
            <Row gutter={8}>
              <Col span={8}>
                <Form.Item
                  name="meta_tenant_name"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.TenantName',
                    defaultMessage: '租户名称',
                  })}
                  // initialValue={meta_tenant?.name?.tenant_name}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterATenantName',
                        defaultMessage: '请输入租户名称',
                      }),
                    },
                  ]}
                >
                  <Input
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                  />
                </Form.Item>
              </Col>

              <Col span={8}>
                <Form.Item
                  name="tenantPassword"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.Password',
                    defaultMessage: '密码',
                  })}
                  // initialValue={meta_tenant?.name?.password}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterAPassword',
                        defaultMessage: '请输入密码',
                      }),
                    },

                    // {
                    //   // 只对新密码进行密码校验，旧密码不做校验，避免老数据密码格式校验不通过时无法修改密码
                    //   validator: validatePassword(tenantPasswordPassed),
                    // },
                  ]}
                >
                  <Password onValidate={setTenantPasswordPassed} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.ConfirmPassword',
                    defaultMessage: '确认密码',
                  })}
                  name="confirmTenantPassword"
                  // initialValue={meta_tenant?.name?.password}
                  dependencies={['tenantPassword']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.PleaseEnterANewPassword',
                        defaultMessage: '请再次输入新密码',
                      }),
                    },

                    {
                      validator: validateConfirmTenantPassword,
                    },
                  ]}
                >
                  <MyInput.Password
                    autoComplete="new-password"
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnterANewPassword',
                      defaultMessage: '请再次输入新密码',
                    })}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Descriptions
              title={intl.formatMessage({
                id: 'OBD.component.OCPConfig.MonitorDataTenantConfiguration',
                defaultMessage: '监控数据租户配置',
              })}
            />
            <Row gutter={8}>
              <Col span={8}>
                <Form.Item
                  name="monitor_tenant_name"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.TenantName',
                    defaultMessage: '租户名称',
                  })}
                  // initialValue={monitor_tenant?.name?.tenant_name}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterATenantName',
                        defaultMessage: '请输入租户名称',
                      }),
                    },
                  ]}
                >
                  <Input
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                  />
                </Form.Item>
              </Col>

              <Col span={8}>
                <Form.Item
                  name="monitorPassword"
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.Password',
                    defaultMessage: '密码',
                  })}
                  // initialValue={monitor_tenant?.name?.password}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.EnterAPassword',
                        defaultMessage: '请输入密码',
                      }),
                    },

                    // {
                    //   // 只对新密码进行密码校验，旧密码不做校验，避免老数据密码格式校验不通过时无法修改密码
                    //   validator: validatePassword(passed),
                    // },
                  ]}
                >
                  <Password onValidate={setPassed} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.component.OCPConfig.ConfirmPassword',
                    defaultMessage: '确认密码',
                  })}
                  name="confirmMonitorPassword"
                  // initialValue={monitor_tenant?.name?.password}
                  dependencies={['monitorPassword']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.component.OCPConfig.PleaseEnterANewPassword',
                        defaultMessage: '请再次输入新密码',
                      }),
                    },

                    {
                      validator: validateConfirmMonitorPassword,
                    },
                  ]}
                >
                  <MyInput.Password
                    autoComplete="new-password"
                    placeholder={intl.formatMessage({
                      id: 'OBD.component.OCPConfig.PleaseEnterANewPassword',
                      defaultMessage: '请再次输入新密码',
                    })}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </Form>
  );
};

export default OCPConfig;
