
import { intl } from '@/utils/intl';
import { ProCard, } from '@ant-design/pro-components';
import { Spin } from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { Alert, Button, Col, Input, Table, Tag, Typography } from 'antd';
import type { FormInstance } from 'antd/lib/form';
import React, { useEffect } from 'react';
import { useModel } from 'umi';
import { getLocale } from 'umi';
import EnStyles from '../../../indexEn.less';
import ZhStyles from '../../../indexZh.less';
import CustomFooter from '@/component/CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import { creatOmsDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import { encrypt } from '@/utils/encrypt';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
const { Text } = Typography;

const locale = getLocale();
const mainStyles = locale === 'zh-CN' ? ZhStyles : EnStyles;

// 辅助函数：在数组中根据 value 查找对应的项
const findByValue = (array: Array<{ value: string; label: string }>, value: string) => {
  return array.find((item) => item.value === value);
};
export interface ConnectionInfoProps {
  type: 'install' | 'update';
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

const ConnectionInfo: React.FC<ConnectionInfoProps> = ({
  type
}) => {

  const {
    configData = {},
    setCurrentStep,
    setErrorVisible,
    setErrorsList,
    selectedOmsType,
    errorsList,
    ocpConfigData,
    omsTakeoverData
  } = useModel('global');

  const { setConnectId } = useModel('ocpInstallData');

  // 组件挂载时清空之前的错误，避免显示遗留的错误信息
  useEffect(() => {
    setErrorVisible(false);
    setErrorsList([]);
  }, []);


  // 当前为 OBD ，适用于 oms 升级
  const OBDUpdate = ocpConfigData?.install_type === 'obd_install'

  const { run: handleCreateConfig, loading: createConfigLoading } = useRequest(
    creatOmsDeploymentConfig,
    {
      manual: true,
      onSuccess: ({ success, data }: API.OBResponse) => {
        if (success) {
          setConnectId(data);
          setCurrentStep(4);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );



  const handlePreCheck = async () => {
    const { data: publicKey } = await getPublicKey();
    // 移除 regions 中的 id 字段和 configData 中的 appname 字段
    const { appname, mode, oms_meta_password, tsdb_password, tsdb_url, tsdb_port, tsdb_username, auth, ...configDataWithoutAppname } = configData || {};

    // 判断监控配置是否展开（基于 tsdb_url 是否存在）
    const isMonitoringConfigExpanded = !!configData?.tsdb_url;

    const configDataWithoutId: any = {
      ...configDataWithoutAppname,
      auth: {
        ...auth,
        user: auth.username,
        password: auth.password ? encrypt(auth.password, publicKey) : encrypt('', publicKey),
      },
      oms_meta_password: oms_meta_password ? encrypt(oms_meta_password, publicKey) : encrypt('', publicKey),
      regions: configData?.regions?.map(({ id, ...rest }: any) => {
        const result = { ...rest };
        // 如果 regions 的长度为 1，添加 cm_is_default: true
        if (configData?.regions?.length === 1) {
          result.cm_is_default = true;
        }
        return result;
      }) || [],
    };

    // 只有当监控配置展开时，才传递 tsdb 相关的配置参数
    if (isMonitoringConfigExpanded) {
      configDataWithoutId.tsdb_url = `${tsdb_url}:${tsdb_port}`;
      configDataWithoutId.tsdb_username = tsdb_username;
      configDataWithoutId.tsdb_service = "INFLUXDB"
      configDataWithoutId.tsdb_password = tsdb_password ? encrypt(tsdb_password, publicKey) : '';
    }

    handleCreateConfig(
      { name: appname },
      configDataWithoutId,
    );
  };

  const handleUpdate = () => {
    setCurrentStep(1);
  }

  const prevStep = () => {
    if (type === 'install') {
      setCurrentStep(2);
    } else if (type === 'update') {
      setCurrentStep(-1);
    }
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const deployMode = [
    {
      label: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.SingleNode',
        defaultMessage: '单节点',
      }),
      value: 'standard',
    },
    {
      label: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.SingleRegionMultiNode',
        defaultMessage: '单地域多节点',
      }),
      value: 'compact',
    },
    {
      label: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.MultiRegionMultiNode',
        defaultMessage: '多地域多节点',
      }),
      value: 'multi',
    },
  ]

  const userInfo = (title: string) => {
    return <ProCard
      title={title}
      className="card-padding-bottom-24"

    >
      <Col span={24}>
        <ProCard
          className={mainStyles.infoSubCard}
          split="vertical"
        >
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Username',
              defaultMessage: '用户名',
            })}
          >
            {type === 'install' ? configData?.auth?.username : ocpConfigData?.user}
          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Password',
              defaultMessage: '密码',
            })}
          >
            {
              (configData?.auth?.password || ocpConfigData?.password) ?
                <Input.Password
                  value={configData?.auth?.password || ocpConfigData?.password}
                  visibilityToggle={true}
                  readOnly
                  bordered={false}
                  style={{ padding: 0 }}
                /> : <div>-</div>
            }

          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.SshPort',
              defaultMessage: 'SSH 端口',
            })}
          >
            {type === 'install' ? configData?.auth?.ssh_port : ocpConfigData?.port}
          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.UseRuntimeUser',
              defaultMessage: '使用运行用户',
            })}
          >
            {intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Yes',
              defaultMessage: '是',
            })}
          </ProCard>
        </ProCard>
      </Col>
    </ProCard>
  }

  const mirrorInfo = () => {
    return <ProCard
      title={intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.MonitoringConfiguration',
        defaultMessage: '监控配置',
      })}
      className="card-padding-bottom-24"
    >
      <Col span={24}>
        <ProCard
          className={mainStyles.infoSubCard}
          split="vertical"
        >
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.InfluxDbAddress',
              defaultMessage: 'InfluxDB 地址',
            })}
          >
            {configData?.tsdb_url}
          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Port',
              defaultMessage: '端口',
            })}
          >
            {configData?.tsdb_port}
          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Username',
              defaultMessage: '用户名',
            })}
          >
            {configData?.tsdb_username}
          </ProCard>
          <ProCard
            colSpan={6}
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.Password',
              defaultMessage: '密码',
            })}
          >
            <Input.Password
              value={configData?.tsdb_password}
              visibilityToggle={true}
              readOnly
              bordered={false}
              style={{ padding: 0 }}
            />
          </ProCard>
        </ProCard>
      </Col>
    </ProCard>
  }

  const visibleMirrorInfo = (title: string) => {
    return (
      <ProCard
        title={title}
        className="card-padding-bottom-24"
      >
        <Col span={24}>
          <ProCard
            className={mainStyles.infoSubCard}
            split="vertical"
          >
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.AccessAddress',
                defaultMessage: '访问地址',
              })}
            >
              {configData?.oms_meta_host}
            </ProCard>
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.Port',
                defaultMessage: '端口',
              })}
            >
              {configData?.oms_meta_port}
            </ProCard>
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.AccessAccount',
                defaultMessage: '访问账号',
              })}
            >
              {configData?.oms_meta_user}
            </ProCard>
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.Password',
                defaultMessage: '密码',
              })}
            >
              <Input.Password
                value={configData?.oms_meta_password}
                visibilityToggle={true}
                readOnly
                bordered={false}
                style={{ padding: 0 }}
              />
            </ProCard>
          </ProCard>
        </Col>
      </ProCard>
    )
  }
  const visibleConnectInfo = (title: string) => {
    return (
      <ProCard
        title={title}
        className="card-padding-bottom-24"
      >
        <Col span={24}>
          <ProCard
            className={mainStyles.infoSubCard}
            split="vertical"
          >
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.OmsAccessAddress',
                defaultMessage: 'OMS 访问地址',
              })}
            >
              {ocpConfigData?.host}
            </ProCard>
            <ProCard
              colSpan={18}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.OmsContainerName',
                defaultMessage: 'OMS 容器名称',
              })}
            >
              {ocpConfigData?.container_name}
            </ProCard>

          </ProCard>
        </Col>
        <Col span={24}>
          <ProCard
            className={mainStyles.infoSubCard}
            split="vertical"
          >
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.AccessAccount',
                defaultMessage: '访问账号',
              })}
            >
              {ocpConfigData?.user}
            </ProCard>
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.Password',
                defaultMessage: '密码',
              })}
            >
              <Input.Password
                value={ocpConfigData?.password}
                visibilityToggle={true}
                readOnly
                bordered={false}
                style={{ padding: 0 }}
              />
            </ProCard>
            <ProCard
              colSpan={6}
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.Port',
                defaultMessage: '端口',
              })}
            >
              {ocpConfigData?.port}
            </ProCard>
          </ProCard>
        </Col>
      </ProCard>
    )
  }
  const moreConfigColumns = [
    {
      title: 'drc_cm_heartbeat_db',
      dataIndex: 'drc_cm_heartbeat_db',
      render: (text: any) => text || '-',
      width: '50%',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.ConnectionInfo.RegionName',
        defaultMessage: '地域名称',
      }),
      dataIndex: 'cm_region',
      render: (text: any) => text || '-',
    },
  ]

  // 检查 configData.regions 中是否存在 drc_cm_heartbeat_db
  const hasDrcCmHeartbeatDb = configData?.regions?.some((item: any) =>
    item?.drc_cm_heartbeat_db && item.drc_cm_heartbeat_db.trim() !== ''
  );

  return (
    <Spin
      spinning={false}
    >
      <Alert
        type="info"
        showIcon={true}
        message={
          type === 'install' ?
            intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.OmsInstallationInfoConfigurationCompleted',
              defaultMessage: 'OMS 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
            })
            : intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.OmsUpgradeInfoMessage',
              defaultMessage: '系统会根据 MetaDB 配置信息获取 OMS 相关配置信息，为保证管理功能一致性，升级程序将升级平台管理服务 OMS Server。请检查并确认以下配置信息，确定后开始预检查。',
            })}
        style={{
          margin: '16px 0',
          height: 54,
        }}
      />
      <ProCard className={mainStyles.pageCard} split="horizontal">
        <ProCard
          title={type === 'install' ? intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.BasicConfiguration',
            defaultMessage: '基本配置',
          }) : intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.DeploymentSource',
            defaultMessage: '部署来源',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={type === 'install' ? 12 : 24}>
            <ProCard
              className={mainStyles.infoSubCard}
              split="vertical"
            >
              {
                type === 'update' &&
                <ProCard
                  colSpan={OBDUpdate ? 6 : 10}
                  title={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.OriginalDeploymentMethod',
                    defaultMessage: '原部署方式',
                  })}
                >
                  {OBDUpdate ? intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.ObdDeployment',
                    defaultMessage: 'OBD 部署',
                  }) : intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.NonObdDeployment',
                    defaultMessage: '非OBD 部署',
                  })}
                </ProCard>
              }

              <ProCard
                colSpan={OBDUpdate ? 6 : 10}
                title={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.DeploymentName',
                  defaultMessage: '部署名称',
                })}
              >
                {type === 'install' ? configData?.appname : ocpConfigData?.cluster_name}
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        {
          type === 'install' && <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.DeploymentMode',
              defaultMessage: '部署模式',
            })}
            className="card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard
                split="vertical"
                style={{ backgroundColor: '#f8fafe' }}
              >
                <ProCard
                  colSpan={24}
                  style={{ backgroundColor: '#f8fafe' }}
                >
                  {findByValue(deployMode, configData?.mode)?.label}
                </ProCard>

              </ProCard>
            </Col>
          </ProCard>
        }
        {
          !OBDUpdate && (
            <>
              {
                type === 'update' &&
                visibleConnectInfo(intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.ConnectionInformation',
                  defaultMessage: '连接信息',
                }))
              }
            </>
          )
        }

        {
          type === 'install' && <>
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.PortConfiguration',
                defaultMessage: '端口配置',
              })}
              className="card-padding-bottom-24"

            >
              <Col span={24}>
                <ProCard
                  className={mainStyles.infoSubCard}
                  split="vertical"
                >
                  <ProCard
                    colSpan={5}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.HttpServicePort',
                      defaultMessage: 'HTTP 服务端口',
                    })}
                  >
                    {configData?.nginx_server_port}
                  </ProCard>
                  <ProCard
                    colSpan={5}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.CmsServicePort',
                      defaultMessage: 'CM 服务端口',
                    })}
                  >
                    {configData?.cm_server_port}
                  </ProCard>
                  <ProCard
                    colSpan={5}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.SupervisorServicePort',
                      defaultMessage: 'Supervisor 服务端口',
                    })}
                  >
                    {configData?.supervisor_server_port}
                  </ProCard>

                  <ProCard
                    colSpan={5}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.GhanaServicePort',
                      defaultMessage: 'Ghana 服务端口',
                    })}
                  >
                    {configData?.ghana_server_port}
                  </ProCard>
                  <ProCard
                    colSpan={4}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.SshdServicePort',
                      defaultMessage: 'SSHD 服务端口',
                    })}
                  >
                    {configData?.sshd_server_port}
                  </ProCard>
                </ProCard>
              </Col>
            </ProCard>
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.DataDirectory',
                defaultMessage: '数据目录',
              })}
              className="card-padding-bottom-24"
            >
              <Col span={type === 'install' ? 12 : 24}>
                <ProCard
                  className={mainStyles.infoSubCard}
                  split="vertical"
                >
                  <ProCard
                    colSpan={6}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.Path',
                      defaultMessage: '路径',
                    })}
                  >
                    {configData?.mount_path}
                  </ProCard>
                </ProCard>
              </Col>
            </ProCard>
            {userInfo(intl.formatMessage({
              id: 'OBD.pages.Oms.ConnectionInfo.DeploymentUserConfiguration',
              defaultMessage: '部署用户配置',
            }))}
          </>
        }
        <ProCard
          title={type === 'update' ? intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.UpgradeConfiguration',
            defaultMessage: '升级配置',
          }) : intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.ProductVersion',
            defaultMessage: '产品版本',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={type === 'install' ? 12 : 24}>
            <ProCard
              className={mainStyles.infoSubCard}
              split="vertical"
            >
              <ProCard
                colSpan={type === 'install' ? 12 : 6}
                title={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.Product',
                  defaultMessage: '产品',
                })}
              >
                OMS
                <Tag style={{ marginLeft: 6 }}>{(type == 'install' ? selectedOmsType?.includes('ce') : ocpConfigData?.version?.includes('ce')) ? intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.CommunityEdition',
                  defaultMessage: '社区版',
                }) : intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.CommercialEdition',
                  defaultMessage: '商业版',
                })}</Tag>
              </ProCard>
              <ProCard
                colSpan={6}
                title={type == 'install' ? intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.Version',
                  defaultMessage: '版本',
                }) : intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.OriginalVersion',
                  defaultMessage: '原版本',
                })}
              >
                <span style={{ whiteSpace: 'nowrap' }}>
                  {
                    type == 'install' ? selectedOmsType?.toUpperCase()
                      : ocpConfigData?.current_version ?
                        `V ${ocpConfigData?.current_version?.split('feature_')[1]?.toUpperCase()}` :
                        `V ${omsTakeoverData?.version?.split('feature_')[1]?.toUpperCase()}`}
                </span>
              </ProCard>
              {
                type === 'update' && <ProCard
                  colSpan={6}
                  title={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.TargetVersion',
                    defaultMessage: '目标版本',
                  })}
                >
                  V {ocpConfigData?.version?.split('feature_')[1]?.toUpperCase()}
                </ProCard>
              }
              {
                type === 'update' && ocpConfigData?.path &&
                ocpConfigData?.upgrade_mode === 'online' &&
                <ProCard
                  colSpan={6}
                  title={intl.formatMessage({
                    id: 'OBD.pages.Oms.ConnectionInfo.UpgradeFilePath',
                    defaultMessage: '存放升级文件路径',
                  })}
                  style={{ backgroundColor: '#f8fafe' }}
                >
                  <Text
                    ellipsis={{
                      tooltip: ocpConfigData?.path,
                    }}
                  >
                    {ocpConfigData?.path}
                  </Text>
                </ProCard>
              }

            </ProCard>
          </Col>
        </ProCard>
        {type === 'update' && <ProCard
          title={intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.UpgradeMethod',
            defaultMessage: '升级方式',
          })}
          className="card-padding-bottom-24"
        >
          <Col span={12}>
            <ProCard
              split="vertical"
              style={{ backgroundColor: '#f8fafe' }}
            >
              <ProCard
                colSpan={6}
                style={{ backgroundColor: '#f8fafe' }}
              >
                {
                  ocpConfigData?.upgrade_mode === 'online' ?
                    intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.OnlineUpgrade',
                      defaultMessage: '在线升级',
                    }) : intl.formatMessage({
                      id: 'OBD.pages.Oms.ConnectionInfo.OfflineUpgrade',
                      defaultMessage: '停服升级',
                    })}
              </ProCard>
            </ProCard>
          </Col>
        </ProCard>
        }
      </ProCard>
      {
        type === 'install' &&
        <ProCard
          className={mainStyles.pageCard}
          split="horizontal"
          style={{ marginTop: 56 }}
        >
          {visibleMirrorInfo(intl.formatMessage({
            id: 'OBD.pages.Oms.ConnectionInfo.AccessConfiguration',
            defaultMessage: '访问配置',
          }))}
          {/* 监控配置：当存在 tsdb_url 时默认展示 */}
          {configData?.tsdb_url && mirrorInfo()}
          {
            (configData?.drc_rm_db && configData?.drc_cm_db) || hasDrcCmHeartbeatDb ?
              <ProCard
                title={intl.formatMessage({
                  id: 'OBD.pages.Oms.ConnectionInfo.MoreConfiguration',
                  defaultMessage: '更多配置',
                })}
                className="card-padding-bottom-24"
              >
                <Col span={12}>
                  <ProCard
                    className={mainStyles.infoSubCard}
                    split="vertical"
                  >
                    <ProCard
                      colSpan={12}
                      title='drc_rm_db'
                    >
                      {configData?.drc_rm_db || '-'}
                    </ProCard>
                    <ProCard
                      colSpan={12}
                      title='drc_cm_db'
                    >
                      {configData?.drc_cm_db || '-'}
                    </ProCard>
                  </ProCard>
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Table
                    columns={moreConfigColumns}
                    dataSource={configData?.regions?.filter((item: any) => item?.drc_cm_heartbeat_db) || []}
                    rowKey="id"
                    pagination={false}
                    className={mainStyles.nodemoreCard}
                  />
                </Col>
              </ProCard>
              : null
          }
        </ProCard>
      }
      <CustomFooter>
        <ExitBtn />
        <Button
          onClick={prevStep}
        >
          {intl.formatMessage({
            id: 'OBD.component.PreCheck.preCheck.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button
          type="primary"
          loading={createConfigLoading}
          onClick={() => {
            if (type === 'install') {
              handlePreCheck()
            } else if (type === 'update') {
              handleUpdate()
            }
          }}>
          {intl.formatMessage({
            id: 'OBD.component.PreCheck.preCheck.NextStep',
            defaultMessage: '下一步',
          })}
        </Button>
      </CustomFooter>
    </Spin>
  );
};

export default ConnectionInfo;
