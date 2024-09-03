import InputPort from '@/component/InputPort';
import { FORM_ITEM_SMALL_LAYOUT } from '@/constant';
import type { ConnectInfoType } from '@/models/ocpInstallData';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import { encrypt } from '@/utils/encrypt';
import { intl } from '@/utils/intl';
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons';
import { ProCard, ProForm } from '@ant-design/pro-components';
import { Card, Spin } from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { Alert, Button, Input, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { FormInstance } from 'antd/lib/form';
import React from 'react';
import { useModel } from 'umi';
import styles from './index.less';
export interface ConnectionInfoProps {
  form: FormInstance<any>;
  loading?: boolean;
  checkLoading: boolean;
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
  checkLoading,
  handleCheck,
  checkConnectInfo,
  systemUserForm,
  checkStatus,
  setCheckStatus,
  setCheckConnectInfo,
  updateInfo,
  allowInputUser,
}) => {
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
      const { data: publicKey } = await getPublicKey();
      const res = await checkOperatingUser({
        user,
        password: encrypt(password, publicKey) || password,
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
    accessUser: updateConnectInfo.accessUser || 'meta_user@ocp_meta',
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
        <ProForm
          form={form}
          submitter={false}
          className={styles.formContainer}
          initialValues={initialValues}
          layout="vertical"
          requiredMark={false}
          scrollToFirstError
          {...FORM_ITEM_SMALL_LAYOUT}
        >
          <ProForm.Item
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
            <Input
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterADatabaseAccessIp',
                defaultMessage: '请输入数据库访问 IP 地址',
              })}
              onChange={() => setCheckConnectInfo('unchecked')}
            />
          </ProForm.Item>
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

          <ProForm.Item
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
            <Input
              onChange={() => {
                setCheckConnectInfo('unchecked');
              }}
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterADatabaseName',
                defaultMessage: '请输入数据库名',
              })}
            />
          </ProForm.Item>
          <ProForm.Item
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
            <Input
              onChange={() => setCheckConnectInfo('unchecked')}
              style={commonWidthStyle}
              placeholder={intl.formatMessage({
                id: 'OBD.Component.ConnectionInfo.EnterAnAccount',
                defaultMessage: '请输入账号',
              })}
            />
          </ProForm.Item>
          <ProForm.Item noStyle dependencies={['accessUser']}>
            {({ getFieldValue, getFieldError }) => {
              const accessUser = getFieldValue('accessUser');
              if (
                (/^root@/.test(accessUser) || accessUser === 'root') &&
                getFieldError('accessCode').length
              ) {
                form.setFields([{ name: 'accessCode', errors: [] }]);
              }
              return (
                <ProForm.Item
                  name="accessCode"
                  label={intl.formatMessage({
                    id: 'OBD.Component.ConnectionInfo.AccessPassword',
                    defaultMessage: '访问密码',
                  })}
                  rules={[
                    {
                      required:
                        !/^root@/.test(accessUser) && accessUser !== 'root',
                      message: intl.formatMessage({
                        id: 'OBD.Component.ConnectionInfo.EnterAnAccessPassword',
                        defaultMessage: '请输入访问密码',
                      }),
                    },
                  ]}
                >
                  <Input.Password
                    onChange={() => {
                      setCheckConnectInfo('unchecked');
                    }}
                    style={commonWidthStyle}
                    placeholder={intl.formatMessage({
                      id: 'OBD.Component.ConnectionInfo.PleaseEnter',
                      defaultMessage: '请输入密码',
                    })}
                  />
                </ProForm.Item>
              );
            }}
          </ProForm.Item>

          <Button loading={checkLoading} onClick={() => handleCheck()}>
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
        </ProForm>
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
            <ProForm
              submitter={false}
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
                <ProForm.Item
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
                  <Input
                    onChange={() => setCheckStatus('unchecked')}
                    disabled={!allowInputUser}
                    style={commonWidthStyle}
                  />
                </ProForm.Item>
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
                  <ProForm.Item
                    label={intl.formatMessage({
                      id: 'OBD.Component.ConnectionInfo.PasswordOptional',
                      defaultMessage: '密码（可选）',
                    })}
                    name="password"
                  >
                    <Input.Password
                      onChange={() => setCheckStatus('unchecked')}
                      placeholder={intl.formatMessage({
                        id: 'OBD.Component.ConnectionInfo.IfYouHaveConfiguredPassword',
                        defaultMessage: '如已配置免密登录，则无需再次输入密码',
                      })}
                      style={commonWidthStyle}
                    />
                  </ProForm.Item>
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
            </ProForm>
          </div>
        )}
      </Card>
    </Spin>
  );
};

export default ConnectionInfo;
