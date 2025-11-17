import {
  handleQuit,
  serverReg,
} from '@/utils';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type {
  EditableFormInstance,
} from '@ant-design/pro-components';
import {
  EditableProTable,
  ProCard,
  ProForm,
  ProFormDigit,
  ProFormText,
} from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Col,
  Input,
  Row,
  Space,
  Tooltip,
} from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  commonSelectStyle,
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
import { omsConnectInfluxdb } from '@/services/component-change/componentChange';

import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import { Modal } from '@oceanbase/design';
import { encrypt } from '@/utils/encrypt';
import { getPublicKey } from '@/services/ob-deploy-web/Common';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function NodeConfig() {
  const {
    setCurrentStep,
    configData,
    setConfigData,
    handleQuitProgress,
    setErrorVisible,
    setErrorsList,
  } = useModel('global');

  const [form] = ProForm.useForm();

  const [editableForm] = ProForm.useForm();
  const tableFormRef = useRef<EditableFormInstance<API.DBConfig>>();
  // 检查初始化数据中是否有 tsdb_url，如果有则默认展开监控配置
  const hasTsdbUrl = configData?.tsdb_url && configData.tsdb_url.trim() !== '';
  const [monitorShow, setMonitorShow] = useState<boolean>(!!hasTsdbUrl);
  // 检查初始化数据中是否有 drc_cm_heartbeat_db，如果有则默认展开
  const hasDrcCmHeartbeatDb = configData?.regions?.some((item: any) =>
    item?.drc_cm_heartbeat_db || configData?.drc_rm_db
  );
  const [show, setShow] = useState<boolean>(!!hasDrcCmHeartbeatDb);


  const initDBConfigData = configData?.regions?.length
    ? configData?.regions?.map((item: any, index: number) => ({
      id: (Date.now() + index).toString(),
      ...item,
      // 设置 drc_cm_heartbeat_db 的默认值
      drc_cm_heartbeat_db: item?.drc_cm_heartbeat_db || '',
    }))
    : [];

  // 使用状态管理表格数据，确保编辑后能正确更新
  const [tableData, setTableData] = useState<API.DBConfig[]>(initDBConfigData);

  // 当 configData.tsdb_url 变化时，检查是否需要展开监控配置
  useEffect(() => {
    if (configData?.tsdb_url && configData.tsdb_url.trim() !== '') {
      setMonitorShow(true);
    }
  }, [configData?.tsdb_url]);

  // 当 configData.regions 变化时，同步更新表格数据
  useEffect(() => {
    if (configData?.regions?.length) {
      const newTableData = configData.regions.map((item: any, index: number) => ({
        id: item.id || (Date.now() + index).toString(),
        ...item,
        // 设置 drc_cm_heartbeat_db 的默认值，优先使用已有的值，否则使用 drc_rm_db 或 configData.drc_rm_db
        drc_cm_heartbeat_db: item?.drc_cm_heartbeat_db || item?.drc_rm_db || configData?.drc_rm_db || '',
      }));

      // 检查 newTableData 中是否有 drc_cm_heartbeat_db，如果有则展开"更多配置"
      const hasDrcCmHeartbeatDb = newTableData.some((item: any) =>
        item?.drc_cm_heartbeat_db && item.drc_cm_heartbeat_db.trim() !== ''
      );
      if (hasDrcCmHeartbeatDb) {
        setShow(true);
      }

      setTableData(newTableData as API.DBConfig[]);
      setEditableRowKeys(newTableData.map((item: any) => item.id));
    }
  }, [configData?.regions?.length, configData?.drc_rm_db]);

  const [editableKeys, setEditableRowKeys] = useState<React.Key[]>(() =>
    initDBConfigData.map((item: any) => item.id),
  );

  const [metadbConnectionCheckStatus, setMetadbConnectionCheckStatus] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');

  const [checkMirrorStatus, setCheckMirrorStatus] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');

  // 保存上次校验成功的 MetaDB 访问配置参数
  const lastMetadbParams = useRef<{
    host?: string;
    port?: number;
    user?: string;
    password?: string;
  } | null>(null);

  // 保存上次校验成功的监控配置参数
  const lastMirrorParams = useRef<{
    host?: string;
    port?: number;
    user?: string;
    password?: string;
  } | null>(null);

  // 组件初始化时，如果 configData 中有访问配置的值，恢复校验状态
  useEffect(() => {
    // 初始化 MetaDB 访问配置的校验状态
    if (configData?.oms_meta_host && configData?.oms_meta_port && configData?.oms_meta_user) {
      // 如果 lastMetadbParams 为空，说明是首次加载，从 configData 初始化
      if (!lastMetadbParams.current) {
        lastMetadbParams.current = {
          host: configData.oms_meta_host.trim(),
          port: configData.oms_meta_port,
          user: configData.oms_meta_user.trim(),
          password: configData.oms_meta_password ? configData.oms_meta_password.trim() : '',
        };
        // 如果 configData 中有值，假设之前校验成功过，恢复状态为 success
        setMetadbConnectionCheckStatus('success');
      }
    }

    // 初始化监控配置的校验状态
    if (configData?.tsdb_url && configData?.tsdb_port && configData?.tsdb_username) {
      // 如果 lastMirrorParams 为空，说明是首次加载，从 configData 初始化
      if (!lastMirrorParams.current) {
        lastMirrorParams.current = {
          host: configData.tsdb_url.trim(),
          port: configData.tsdb_port,
          user: configData.tsdb_username.trim(),
          password: configData.tsdb_password ? configData.tsdb_password.trim() : '',
        };
        // 如果 configData 中有值，假设之前校验成功过，恢复状态为 success
        setCheckMirrorStatus('success');
      }
    }
  }, []); // 只在组件挂载时执行一次

  const prevStep = () => {
    const formValues = form.getFieldsValue(true);
    setConfigData({
      ...configData,
      ...formValues,

    });
    setCurrentStep(1);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const nextStep = () => {
    form.validateFields().then((values) => {
      setConfigData({
        ...configData,
        ...values,
        regions: tableData,
      });
      setCurrentStep(3);
      window.scrollTo(0, 0);
    })
  };

  const columns = [
    {
      title: 'drc_cm_heartbeat_db',
      dataIndex: 'drc_cm_heartbeat_db',
      formItemProps: {
        allowClear: false,
      },
      width: 328,
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.NodeConfig.Region',
        defaultMessage: '所属地域',
      }),
      dataIndex: 'cm_region',
      width: 140,
      formItemProps: {
        rules: [
          {
            whitespace: false,
          },
        ],
      },
      renderFormItem: () => {
        return <Input disabled style={{ backgroundColor: '#f0f2f5', color: '#000000d9' }} />;
      },
    },
  ];


  const { run: createMetadbConnection, loading: createMetadbConnectionLoading } = useRequest(
    Metadb.createMetadbConnection,
    {
      manual: true,
      onSuccess: () => {
        setMetadbConnectionCheckStatus('success');
        // 保存当前校验成功的参数（使用表单中的值）
        const formValues = form.getFieldsValue();
        lastMetadbParams.current = {
          host: formValues?.oms_meta_host,
          port: formValues?.oms_meta_port,
          user: formValues?.oms_meta_user,
          password: formValues?.oms_meta_password,
        };
      },
      onError: ({ data }: any) => {
        setMetadbConnectionCheckStatus('fail');
        const errorInfo =
          data?.detail?.msg || (data?.detail[0] && data?.detail[0]?.msg);
        Modal.error({
          title: intl.formatMessage({
            id: 'OBD.component.ConnectConfig.MetadbConnectionFailedPleaseCheck',
            defaultMessage: 'MetaDB 连接失败，请检查连接配置',
          }),
          icon: <CloseCircleOutlined />,
          content: errorInfo,
          okText: intl.formatMessage({
            id: 'OBD.component.ConnectConfig.IKnow',
            defaultMessage: '我知道了',
          }),
        });
      },
    },
  );

  const {
    run: connectInfluxdb,
    loading: connectInfluxdbLoading,
  } = useRequest(omsConnectInfluxdb, {
    onSuccess: ({ data }) => {
      if (data?.check_result) {
        setCheckMirrorStatus('success');
      } else {
        setCheckMirrorStatus('fail');
      }
      // 保存当前校验成功的参数（使用表单中的值）
      const formValues = form.getFieldsValue();
      lastMirrorParams.current = {
        host: formValues?.tsdb_url,
        port: formValues?.tsdb_port,
        user: formValues?.tsdb_username,
        password: formValues?.tsdb_password,
      };
    },
    onError: () => {
      setCheckMirrorStatus('fail');
    },
  });

  // console.log('connectInfluxdbData', connectInfluxdbData)
  const handleMetadbConnectionCheck = async () => {
    // 在函数内部获取最新的表单值
    const formValues = form.getFieldsValue();
    const { data: publicKey } = await getPublicKey();
    const body = {
      host: formValues?.oms_meta_host,
      password: encrypt(formValues?.oms_meta_password, publicKey),
      user: formValues?.oms_meta_user,
      port: formValues?.oms_meta_port,
    }
    createMetadbConnection({}, body);
  };

  const handleCheckMirror = async () => {
    // 在函数内部获取最新的表单值
    const formValues = form.getFieldsValue();
    const { data: publicKey } = await getPublicKey();
    const body = {
      host: formValues?.tsdb_url,
      user: formValues?.tsdb_username,
      password: encrypt(formValues?.tsdb_password, publicKey),
      port: formValues?.tsdb_port,
    }
    connectInfluxdb({}, body);
  };

  // 监听 MetaDB 访问配置的变化，如果有变化则重置校验状态
  useEffect(() => {
    const lastParams = lastMetadbParams.current;

    // 只有当之前已经校验成功过（lastParams 不为 null）时，才比较参数变化
    if (lastParams && configData?.oms_meta_host && configData?.oms_meta_port && configData?.oms_meta_user) {
      const currentParams = {
        host: configData.oms_meta_host.trim(),
        port: configData.oms_meta_port,
        user: configData.oms_meta_user.trim(),
        password: configData.oms_meta_password ? configData.oms_meta_password.trim() : '',
      };

      // 比较当前参数和上一次校验的参数，如果有变化则重置校验状态
      if (
        lastParams.host !== currentParams.host ||
        lastParams.port !== currentParams.port ||
        lastParams.user !== currentParams.user ||
        lastParams.password !== currentParams.password
      ) {
        // 参数有变化，重置校验状态
        setMetadbConnectionCheckStatus('unchecked');
      } else {
        // 参数没有变化，如果当前状态是 unchecked（可能是初始化），恢复为 success
        setMetadbConnectionCheckStatus((prevStatus) => {
          if (prevStatus === 'unchecked') {
            return 'success';
          }
          return prevStatus; // 保持其他状态不变
        });
      }
    }
  }, [configData?.oms_meta_host, configData?.oms_meta_port, configData?.oms_meta_user, configData?.oms_meta_password]);

  // 监听监控配置的变化，如果有变化则重置校验状态
  useEffect(() => {
    const lastParams = lastMirrorParams.current;

    // 只有当之前已经校验成功过（lastParams 不为 null）时，才比较参数变化
    if (lastParams && configData?.tsdb_url && configData?.tsdb_port && configData?.tsdb_username) {
      const currentParams = {
        host: configData.tsdb_url.trim(),
        port: configData.tsdb_port,
        user: configData.tsdb_username.trim(),
        password: configData.tsdb_password ? configData.tsdb_password.trim() : '',
      };

      // 比较当前参数和上一次校验的参数，如果有变化则重置校验状态
      if (
        lastParams.host !== currentParams.host ||
        lastParams.port !== currentParams.port ||
        lastParams.user !== currentParams.user ||
        lastParams.password !== currentParams.password
      ) {
        // 参数有变化，重置校验状态
        setCheckMirrorStatus('unchecked');
      } else {
        // 参数没有变化，如果当前状态是 unchecked（可能是初始化），恢复为 success
        setCheckMirrorStatus((prevStatus) => {
          if (prevStatus === 'unchecked') {
            return 'success';
          }
          return prevStatus; // 保持其他状态不变
        });
      }
    }
  }, [configData?.tsdb_url, configData?.tsdb_port, configData?.tsdb_username, configData?.tsdb_password]);

  return (
    <ProForm
      form={form}
      submitter={false}
      grid={true}
      validateTrigger={['onBlur', 'onChange']}
      initialValues={{
        oms_meta_port: configData?.oms_meta_port || 2881,
        tsdb_port: configData?.tsdb_port || 8086,
        oms_meta_user: configData?.oms_meta_user,
        oms_meta_password: configData?.oms_meta_password,
        oms_meta_host: configData?.oms_meta_host,
        tsdb_url: configData?.tsdb_url,
        tsdb_username: configData?.tsdb_username,
        tsdb_password: configData?.tsdb_password,
        drc_rm_db: configData?.drc_rm_db,
        drc_cm_db: configData?.drc_cm_db,
      }}
      onValuesChange={(changedValues, allValues) => {
        // 同步更新 configData，确保表单值变化时能及时同步
        setConfigData((prevConfigData: any) => ({
          ...prevConfigData,
          ...allValues,
        }));
      }}
    >
      <Space direction="vertical" size="middle">
        <Alert
          showIcon={true}
          type="info"
          message={intl.formatMessage({
            id: 'OBD.pages.Oms.NodeConfig.MetadbHighAvailabilityRecommendation',
            defaultMessage: '为了提升系统可靠性，建议 MetaDB 实施高可用数据库方案能有效保障 OMS 核心服务的 7x24 小时稳定运行，降低业务中断风险。',
          })}
        />
        <ProCard
          className={styles.pageCard}
          title={intl.formatMessage({
            id: 'OBD.pages.Oms.NodeConfig.AccessConfiguration',
            defaultMessage: '访问配置',
          })}
        >
          <Row gutter={[16, 0]}  >
            <Col span={24} >
              <Space size="large" >
                <ProFormText
                  name={'oms_meta_host'}
                  label={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.AccessAddress',
                    defaultMessage: '访问地址',
                  })}
                  fieldProps={{ style: commonSelectStyle }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.src.component.MySelect.PleaseSelect',
                    defaultMessage: '请选择',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.AccessAddress',
                        defaultMessage: '访问地址',
                      }),
                    }, {
                      pattern: serverReg,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.AccessAddress',
                        defaultMessage: '访问地址',
                      }),
                    }
                  ]}
                />
                <ProFormDigit
                  name={'oms_meta_port'}
                  label={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.Port',
                    defaultMessage: '端口',
                  })}
                  fieldProps={{ style: { width: 120 } }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.Port',
                    defaultMessage: '端口',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Port',
                        defaultMessage: '端口',
                      }),
                    },
                  ]}
                />
              </Space>
            </Col>
            <Col span={24}>
              <Space size="large"  >
                <ProFormText
                  name={'oms_meta_user'}
                  label={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.AccessAccount',
                    defaultMessage: '访问账号',
                  })}
                  fieldProps={{ style: commonSelectStyle }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.src.component.MySelect.PleaseSelect',
                    defaultMessage: '请选择',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.AccessAccount',
                        defaultMessage: '访问账号',
                      }),
                    },
                    {
                      validator: (_: any, value: string) => {
                        if (value && value.includes('@sys')) {
                          return Promise.reject(
                            intl.formatMessage({
                              id: 'OBD.pages.Oms.NodeConfig.AccessAccountCannotContainSys',
                              defaultMessage: '访问账号不可以输入@sys',
                            })
                          );
                        }
                        return Promise.resolve();
                      },
                    },
                  ]}
                />
                <ProFormText
                  name={'oms_meta_password'}
                  label={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.Password',
                    defaultMessage: '密码',
                  })}
                  placeholder={intl.formatMessage({
                    id: 'OBD.src.component.MySelect.PleaseSelect',
                    defaultMessage: '请选择',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Password',
                        defaultMessage: '密码',
                      }),
                    },
                  ]}
                >
                  <Input.Password
                    autoComplete="new-password"
                    placeholder={intl.formatMessage({
                      id: 'OBD.src.component.MySelect.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    style={commonSelectStyle}
                  />
                </ProFormText>
              </Space>
            </Col>
            <Col span={24}>
              <Button
                onClick={() => handleMetadbConnectionCheck()}
                loading={createMetadbConnectionLoading}
                style={{ marginTop: 12 }}
                disabled={form.getFieldValue('oms_meta_user')?.includes('@sys')}
              >
                {intl.formatMessage({
                  id: 'OBD.pages.Oms.NodeConfig.Validation',
                  defaultMessage: '校验',
                })}
              </Button>
              {metadbConnectionCheckStatus === 'success' && (
                <span style={{ color: 'rgba(77,204,162,1)', marginLeft: 12 }}>
                  <CheckCircleFilled />
                  <span style={{ marginLeft: 5 }}>
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.NodeConfig.CurrentValidationSuccessful',
                      defaultMessage: '当前校验成功',
                    })}
                  </span>
                </span>
              )}
              {metadbConnectionCheckStatus === 'fail' && (
                <span style={{ color: 'rgba(255,75,75,1)', marginLeft: 12 }}>
                  <CloseCircleFilled />
                  <span style={{ marginLeft: 5 }}>
                    {intl.formatMessage({
                      id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
                      defaultMessage: '当前校验失败，请重新输入',
                    })}
                  </span>
                </span>
              )}
            </Col>
          </Row>
          <div style={{ marginTop: 24 }} onClick={() => setMonitorShow(!monitorShow)}>
            <Space>
              {monitorShow ? <CaretDownOutlined /> : <CaretRightOutlined />}
              <span style={{ fontSize: 16, fontWeight: 500 }}>
                {intl.formatMessage({
                  id: 'OBD.pages.Oms.NodeConfig.MonitoringConfiguration',
                  defaultMessage: '监控配置',
                })}
              </span>
            </Space>
            <span style={{ color: '#8592ad', fontSize: 14, fontWeight: 400 }}>
              {intl.formatMessage({
                id: 'OBD.pages.Oms.NodeConfig.MonitoringConfigurationOptional',
                defaultMessage: '（可选）',
              })}
            </span>
          </div>
          <div style={{ marginTop: 24 }}>
            {
              monitorShow && <Row gutter={[16, 0]}  >
                <Col span={24} >
                  <Space size="large" >
                    <ProFormText
                      name={'tsdb_url'}
                      label={intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.InfluxDbAddress',
                        defaultMessage: 'InfluxDB 地址',
                      })}
                      fieldProps={{ style: commonSelectStyle }}
                      placeholder={intl.formatMessage({
                        id: 'OBD.src.component.MySelect.PleaseSelect',
                        defaultMessage: '请选择',
                      })}
                      rules={[
                        {
                          required: true,
                          message: intl.formatMessage({
                            id: 'OBD.pages.Oms.ConnectionInfo.InfluxDbAddress',
                            defaultMessage: 'InfluxDB 地址',
                          }),
                        }, {
                          pattern: serverReg,
                          message: intl.formatMessage({
                            id: 'OBD.pages.Oms.ConnectionInfo.InfluxDbAddress',
                            defaultMessage: 'InfluxDB 地址',
                          }),
                        }
                      ]}
                    />
                    <ProFormDigit
                      name={'tsdb_port'}
                      label={intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Port',
                        defaultMessage: '端口',
                      })}
                      fieldProps={{ style: { width: 120 } }}
                      placeholder={intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Port',
                        defaultMessage: '端口',
                      })}
                      rules={[
                        {
                          required: true,
                          message: intl.formatMessage({
                            id: 'OBD.pages.Oms.ConnectionInfo.Port',
                            defaultMessage: '端口',
                          }),
                        },
                      ]}
                    />
                  </Space>
                </Col>
                <Col span={24}>
                  <Space size="large"  >
                    <ProFormText
                      name={'tsdb_username'}
                      label={intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Username',
                        defaultMessage: '用户名',
                      })}
                      fieldProps={{ style: commonSelectStyle }}
                      placeholder={intl.formatMessage({
                        id: 'OBD.src.component.MySelect.PleaseSelect',
                        defaultMessage: '请选择',
                      })}
                      rules={[
                        {
                          required: true,
                          message: intl.formatMessage({
                            id: 'OBD.pages.Oms.ConnectionInfo.Username',
                            defaultMessage: '用户名',
                          }),
                        }
                      ]}
                    />
                    <ProFormText
                      name={'tsdb_password'}
                      label={intl.formatMessage({
                        id: 'OBD.pages.Oms.ConnectionInfo.Password',
                        defaultMessage: '密码',
                      })}
                      placeholder={intl.formatMessage({
                        id: 'OBD.src.component.MySelect.PleaseSelect',
                        defaultMessage: '请选择',
                      })}
                      rules={[
                        {
                          required: true,
                          message: intl.formatMessage({
                            id: 'OBD.pages.Oms.ConnectionInfo.Password',
                            defaultMessage: '密码',
                          }),
                        },
                      ]}
                    >
                      <Input.Password
                        autoComplete="new-password"
                        placeholder={intl.formatMessage({
                          id: 'OBD.src.component.MySelect.PleaseSelect',
                          defaultMessage: '请选择',
                        })}
                        style={commonSelectStyle}
                      />
                    </ProFormText>
                  </Space>
                </Col>
                <Col span={24}>
                  <Button
                    loading={connectInfluxdbLoading}
                    onClick={() => handleCheckMirror()}>
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.NodeConfig.Validation',
                      defaultMessage: '校验',
                    })}
                  </Button>
                  {checkMirrorStatus === 'success' && (
                    <span style={{ color: 'rgba(77,204,162,1)', marginLeft: 12 }}>
                      <CheckCircleFilled />
                      <span style={{ marginLeft: 5 }}>
                        {intl.formatMessage({
                          id: 'OBD.pages.Oms.NodeConfig.CurrentValidationSuccessful',
                          defaultMessage: '当前校验成功',
                        })}
                      </span>
                    </span>
                  )}
                  {checkMirrorStatus === 'fail' && (
                    <span style={{ color: 'rgba(255,75,75,1)', marginLeft: 12 }}>
                      <CloseCircleFilled />
                      <span style={{ marginLeft: 5 }}>
                        {intl.formatMessage({
                          id: 'OBD.component.OCPConfigNew.ServiceConfig.TheCurrentVerificationFailedPlease',
                          defaultMessage: '当前校验失败，请重新输入',
                        })}
                      </span>
                    </span>
                  )}
                </Col>
              </Row>

            }
          </div>

          <div style={{ marginTop: 24 }} onClick={() => setShow(!show)}>
            <Space>
              {show ? <CaretDownOutlined /> : <CaretRightOutlined />}
              <span style={{ fontSize: 16, fontWeight: 500 }}>
                {intl.formatMessage({
                  id: 'OBD.pages.Oms.NodeConfig.MoreConfiguration',
                  defaultMessage: '更多配置',
                })}
              </span>
            </Space>
          </div>
          <div style={{ marginTop: 24 }}>
            {
              show && <Row gutter={[16, 0]}  >
                <Col span={24} >
                  <ProFormText
                    name={'drc_rm_db'}
                    label="drc_rm_db"
                    fieldProps={{ style: commonSelectStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.src.component.MySelect.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    rules={[
                      {
                        required: true,
                        message: '请输入 drc_rm_db',
                      }
                    ]}
                  />
                </Col>
                <Col span={24} >
                  <ProFormText
                    name={'drc_cm_db'}
                    label="drc_cm_db"
                    fieldProps={{ style: commonSelectStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.src.component.MySelect.PleaseSelect',
                      defaultMessage: '请选择',
                    })}
                    rules={[
                      {
                        required: true,
                        message: '请输入 drc_cm_db',
                      },
                    ]}
                  />
                </Col>
                <Col span={12}>
                  <EditableProTable
                    className={styles.nodeEditabletable}
                    style={{ marginLeft: 8, marginRight: 16 }}
                    columns={columns}
                    rowKey="id"
                    value={tableData}
                    editableFormRef={tableFormRef}
                    onChange={(value) => {
                      // 更新表格数据状态
                      setTableData([...value] as API.DBConfig[]);
                      // 同时更新 configData.regions，确保数据同步
                      setConfigData({
                        ...configData,
                        regions: value.map((item: any) => ({
                          ...item,
                          // 保持 servers 格式一致
                          servers: item.servers?.map((server: any) =>
                            typeof server === 'string' ? { ip: server } : server
                          ) || [],
                        })),
                      });
                    }}
                    recordCreatorProps={false}
                    editable={{
                      type: 'multiple',
                      form: editableForm,
                      editableKeys,
                      actionRender: () => {
                        return [];
                      },
                      onValuesChange: (editableItem, recordList) => {
                        // 实时更新表格数据，确保编辑的值能立即保存
                        const newRecordList = recordList.map((item: any) => {
                          if (item.id === editableItem.id) {
                            return {
                              ...editableItem,
                            };
                          }
                          return item;
                        });
                        setTableData(newRecordList as API.DBConfig[]);
                        // 同时更新 configData.regions
                        setConfigData({
                          ...configData,
                          regions: newRecordList.map((item: any) => ({
                            ...item,
                            servers: item.servers?.map((server: any) =>
                              typeof server === 'string' ? { ip: server } : server
                            ) || [],
                          })),
                        });
                      },
                      onChange: setEditableRowKeys,
                    }}
                  />
                </Col>
              </Row>

            }
          </div>
        </ProCard>


        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.TheCurrentPageConfigurationHas',
                  defaultMessage: '当前页面配置已保存',
                })}
              >
                <Button
                  onClick={prevStep}
                  data-aspm-click="c307506.d317277"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.NodeConfigurationPreviousStep',
                    defaultMessage: '节点配置-上一步',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.pages.components.NodeConfig.PreviousStep',
                    defaultMessage: '上一步',
                  })}
                </Button>
              </Tooltip>
              <Button
                type="primary"
                onClick={nextStep}
                disabled={
                  metadbConnectionCheckStatus !== 'success' ||
                  (monitorShow && checkMirrorStatus !== 'success')
                }
                data-aspm-click="c307506.d317279"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NodeConfigurationNext',
                  defaultMessage: '节点配置-下一步',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NextStep',
                  defaultMessage: '下一步',
                })}
              </Button>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307506.d317278"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.NodeConfigurationExit',
                  defaultMessage: '节点配置-退出',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.NodeConfig.Exit',
                  defaultMessage: '退出',
                })}
              </Button>
            </Space>
          </div>
        </footer>
      </Space>
    </ProForm>
  );
}
