import InputPort from '@/component/InputPort';
import MyInput from '@/component/MyInput';
import { FORM_ITEM_SMALL_LAYOUT } from '@/constant';
import type { ConnectInfoType } from '@/models/ocpInstallData';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import { intl } from '@/utils/intl';
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { Card, Form, Spin } from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { Alert, Button, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { FormInstance } from 'antd/lib/form';
import React from 'react';
import { useModel } from 'umi';
import styles from './index.less';
export interface ConnectionInfoProps {
  form: FormInstance<any>;
  loading?: boolean;
  onSuccess?: () => void;
  handleCheck: () => void;
  systemUserForm: any;
  checkConnectInfo?: 'unchecked' | 'fail' | 'success';
  checkStatus: 'unchecked' | 'fail' | 'success';
  setCheckStatus: React.Dispatch<
    React.SetStateAction<'unchecked' | 'fail' | 'success'>
  >;

  setCheckConnectInfo: React.Dispatch<
    React.SetStateAction<'unchecked' | 'fail' | 'success'>
  >;

  updateInfo: API.connectMetaDB | undefined;
  upgraadeHosts?: Array<string>;
  allowInputUser: boolean;
}

type DataType = {
  name: string;
  servers: string[];
};

const commonWidthStyle = { width: 328 };

const ConnectionInfo: React.FC<ConnectionInfoProps> = ({
  form,
  loading = false,
  handleCheck,
  checkConnectInfo,
  systemUserForm,
  checkStatus,
  setCheckStatus,
  setCheckConnectInfo,
  updateInfo,
  allowInputUser,
}) => {
  const { setFieldsValue, getFieldsValue } = form;
  const { ocpConfigData = {}, setOcpConfigData } = useModel('global');
  const { updateConnectInfo = {} } = ocpConfigData;
  const columns: ColumnsType<DataType> = [
    {
      title: intl.formatMessage({
        id: 'OBD.Component.ConnectionInfo.ComponentName',
        defaultMessage: '组件名称',
      }),
      dataIndex: 'name',
      key: 'componentName',
      width: 135,
    },
    {
      title: intl.formatMessage({
        id: 'OBD.Component.ConnectionInfo.NodeIp',
        defaultMessage: '节点 IP',
      }),
      dataIndex: 'ip',
      key: 'ip',
      render: (_, record) => (
        <>
          {_.length &&
            _.map((server: string, idx: number) => (
              <Tag key={idx} style={{ marginRight: 4 }}>
                {server}
              </Tag>
            ))}
        </>
      ),
    },
  ];

  const { run: checkOperatingUser, loading: checkUserLoading } = useRequest(
    Metadb.checkOperatingUser,
    {
      manual: true,
      onError: (e) => {
        setCheckStatus('fail');
      },
    },
  );

  const handleCheckSystemUser = () => {
    systemUserForm.validateFields().then(async (values: any) => {
      const { user, password, systemPort: port } = values;
      const res = await checkOperatingUser({
        user,
        password,
        port,
        servers:
          updateInfo?.component.find(
            (item: any) =>
              item.name === 'ocp-server' || item.name === 'ocp-server-ce',
          ).ip || [],
      });
      if (res.success) {
        setCheckStatus('success');
        setOcpConfigData({
          ...ocpConfigData,
          updateConnectInfo: {
            ...ocpConfigData.updateConnectInfo,
            ...values,
          },
        });
      } else {
        setCheckStatus('fail');
      }
    });
  };
  const initialValues: ConnectInfoType = {
    ...updateConnectInfo,
    accessUser: updateConnectInfo.accessUser || 'root@sys',
  };

  const systemUserInitialValues = {
    user: updateConnectInfo.user || undefined,
    systemPort: updateConnectInfo.systemPort || 22,
    password: updateConnectInfo.password || undefined,
  };

  return (
    <Spin spinning={loading}>
      <Alert
        type="info"
        showIcon={true}
        message={intl.formatMessage({
          id: 'OBD.Component.ConnectionInfo.TheInstallerAutomaticallyObtainsMetadb',
          defaultMessage:
            '安装程序根据当前主机 OCP 环境自动获取 MetaDB 配置信息，请检查 MetaDB 配置信息是否正确，OCP 将根据以下信息执行升级程序',
        })}
        style={{
          margin: '16px 0',
          height: 54,
        }}
      />

      <Card
        bordered={false}
        style={{ marginBottom: '70px' }}
        divided={false}
        title={intl.formatMessage({
          id: 'OBD.Component.ConnectionInfo.ConnectionInformation',
          defaultMessage: '连接信息',
        })}
      >
        <Form
          form={form}
          initialValues={initialValues}
          layout="vertical"
          requiredMark={false}
          scrollToFirstError
          {...FORM_ITEM_SMALL_LAYOUT}
        >
          <Form.Item
            name="host"
            label={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.AccessAddress',
              defaultMessage: '访问地址',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.Component.ConnectionInfo.EnterAnAccessAddress',
                  defaultMessage: '请输入访问地址',
                }),
              },
            ]}
          >
            <MyInput
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterADatabaseAccessIp',
                defaultMessage: '请输入数据库访问 IP 地址',
              })}
              onChange={() => setCheckConnectInfo('unchecked')}
            />
          </Form.Item>
          <InputPort
            name="port"
            label={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.AccessPort',
              defaultMessage: '访问端口',
            })}
            message={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.EnterAnAccessPort',
              defaultMessage: '请输入访问端口',
            })}
            fieldProps={{ style: commonWidthStyle }}
          />

          <Form.Item
            name="database"
            label={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.DatabaseName',
              defaultMessage: '数据库名',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.Component.ConnectionInfo.EnterADatabaseName',
                  defaultMessage: '请输入数据库名',
                }),
              },
              // {
              //   pattern: nameReg,
              //   message: '库名仅支持英文、数字，长度不超过20个字符',
              // },
            ]}
          >
            <MyInput
              onChange={() => {
                setCheckConnectInfo('unchecked');
              }}
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterADatabaseName',
                defaultMessage: '请输入数据库名',
              })}
            />
          </Form.Item>

          <Form.Item
            name="accessUser"
            label={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.AccessAccount',
              defaultMessage: '访问账号',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.Component.ConnectionInfo.EnterAnAccessAccount',
                  defaultMessage: '请输入访问账号',
                }),
              },
            ]}
          >
            <MyInput
              onChange={() => setCheckConnectInfo('unchecked')}
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterAnAccount',
                defaultMessage: '请输入账号',
              })}
            />
          </Form.Item>
          <Form.Item
            name="accessCode"
            label={intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.AccessPassword',
              defaultMessage: '访问密码',
            })}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.Component.ConnectionInfo.EnterAnAccessPassword',
                  defaultMessage: '请输入访问密码',
                }),
              },
            ]}
          >
            <MyInput.Password
              onChange={() => {
                setCheckConnectInfo('unchecked');
              }}
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.PleaseEnter',
                defaultMessage: '请输入密码',
              })}
            />
          </Form.Item>
          <Button onClick={() => handleCheck()}>
            {intl.formatMessage({
              id: 'OBD.Component.ConnectionInfo.Verification',
              defaultMessage: '验 证',
            })}
          </Button>
          {checkConnectInfo === 'fail' && (
            <div style={{ color: 'rgba(255,75,75,1)', marginTop: 4 }}>
              <CloseCircleFilled />
              {intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.TheCurrentVerificationFailedPlease',
                defaultMessage: '当前验证失败，请重新填写错误参数',
              })}
            </div>
          )}

          {checkConnectInfo === 'success' && (
            <div style={{ color: 'rgba(77,204,162,1)', marginTop: 4 }}>
              <CheckCircleFilled />
              {intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.TheVerificationIsSuccessfulPlease',
                defaultMessage: '当前验证成功，请填写下方参数',
              })}
            </div>
          )}
        </Form>
        {checkConnectInfo === 'success' && updateInfo && (
          <div style={{ marginTop: 16 }}>
            <ProCard
              type="inner"
              className={`${styles.componentCard}`}
              style={{ border: '1px solid #e2e8f3' }}
              //   key={oceanBaseInfo.group}
            >
              <Table
                className={`${styles.componentTable} ob-table`}
                columns={columns}
                pagination={false}
                dataSource={updateInfo.component}
                rowKey="name"
              />
            </ProCard>
            <Form
              form={systemUserForm}
              initialValues={systemUserInitialValues}
              layout="vertical"
            >
              <ProCard
                className={styles.cardContainer}
                title={intl.formatMessage({
                  id: 'OBD.Component.ConnectionInfo.OperatingSystemUsers',
                  defaultMessage: '操作系统用户',
                })}
              >
                <Form.Item
                  name="user"
                  label={intl.formatMessage({
                    id: 'OBD.Component.ConnectionInfo.Username',
                    defaultMessage: '用户名',
                  })}
                  style={{ marginTop: 16 }}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.Component.ConnectionInfo.EnterAUsername',
                        defaultMessage: '请输入用户名',
                      }),
                    },
                  ]}
                >
                  <MyInput
                    onChange={() => setCheckStatus('unchecked')}
                    disabled={!allowInputUser}
                    style={commonWidthStyle}
                  />
                </Form.Item>
                <p style={{ color: '#8592AD', marginTop: -20 }}>
                  {intl.formatMessage({
                    id: 'OBD.Component.ConnectionInfo.PleaseProvideTheUserName',
                    defaultMessage:
                      '请提供用户名用以自动化配置平台专用操作系统用户',
                  })}
                </p>
                <InputPort
                  name="systemPort"
                  label={intl.formatMessage({
                    id: 'OBD.Component.ConnectionInfo.SshPort',
                    defaultMessage: 'SSH端口',
                  })}
                  fieldProps={{ style: commonWidthStyle }}
                  limit={false}
                />

                <div style={{ display: 'flex', alignItems: 'end' }}>
                  <Form.Item
                    label={intl.formatMessage({
                      id: 'OBD.Component.ConnectionInfo.PasswordOptional',
                      defaultMessage: '密码（可选）',
                    })}
                    name="password"
                  >
                    <MyInput.Password
                      onChange={() => setCheckStatus('unchecked')}
                      placeholder={intl.formatMessage({
                        id: 'OBD.Component.ConnectionInfo.IfYouHaveConfiguredPassword',
                        defaultMessage: '如已配置免密登录，则无需再次输入密码',
                      })}
                      style={commonWidthStyle}
                    />
                  </Form.Item>
                  <Button
                    loading={checkUserLoading}
                    style={{ marginLeft: 12, marginBottom: 24 }}
                    onClick={() => handleCheckSystemUser()}
                  >
                    {intl.formatMessage({
                      id: 'OBD.Component.ConnectionInfo.Verification',
                      defaultMessage: '验 证',
                    })}
                  </Button>
                </div>
                <div style={{ marginTop: -24 }}>
                  {checkStatus === 'success' && (
                    <div style={{ color: 'rgba(77,204,162,1)', marginTop: 4 }}>
                      <CheckCircleFilled />
                      <span style={{ marginLeft: 5 }}>
                        {intl.formatMessage({
                          id: 'OBD.Component.ConnectionInfo.TheVerificationIsSuccessfulProceed',
                          defaultMessage: '当前验证成功，请进行下一步',
                        })}
                      </span>
                    </div>
                  )}

                  {checkStatus === 'fail' && (
                    <div style={{ color: 'rgba(255,75,75,1)', marginTop: 4 }}>
                      <CloseCircleFilled />
                      <span style={{ marginLeft: 5 }}>
                        {intl.formatMessage({
                          id: 'OBD.Component.ConnectionInfo.TheCurrentVerificationFailedPlease.1',
                          defaultMessage: '当前验证失败，请重新输入',
                        })}
                      </span>
                    </div>
                  )}
                </div>
              </ProCard>
            </Form>
          </div>
        )}
      </Card>
    </Spin>
  );
};

export default ConnectionInfo;
