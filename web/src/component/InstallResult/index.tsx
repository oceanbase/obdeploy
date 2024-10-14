import ArrowIcon from '@/component/Icon/ArrowIcon';
import NewIcon from '@/component/Icon/NewIcon';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import * as Process from '@/services/ocp_installer_backend/Process';
import { errorHandler } from '@/utils';
import { getTailPath, handleCopy } from '@/utils/helper';
import { intl } from '@/utils/intl';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  CopyOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Result,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { Alert, Modal, Spin } from 'antd';
import type { ResultProps } from 'antd/es/result';
import React, { useEffect, useState } from 'react';
import { history, useModel } from 'umi';
import CustomFooter from '../CustomFooter';
import ExitBtn from '../ExitBtn';
import styles from './index.less';

const { Text } = Typography;

export interface InstallResultProps extends ResultProps {
  upgradeOcpInfo?: any;
  ocpInfo?: any;
  installStatus?: string; // RUNNING, FINISHED
  installResult?: string; // SUCCESSFUL, FAILED
  taskId?: number;
  type?: string; // install  update
  current: number;
  setCurrent: React.Dispatch<React.SetStateAction<number>>;
}

const InstallResult: React.FC<InstallResultProps> = ({
  ocpInfo = {},
  upgradeOcpInfo,
  installStatus,
  installResult,
  type,
  setCurrent,
  current,
  ...restProps
}) => {
  let isHaveMetadb = 'install';
  const isUpdate = getTailPath() === 'update';
  const { RELEASE_RECORD, OCP_DOCS, ocpConfigData } = useModel('global');
  const ocpAdminPwd = ocpConfigData?.components?.ocpserver?.admin_password;

  if (ocpAdminPwd) ocpInfo.password = ocpAdminPwd;
  // 获取 升级主机列表
  const { data: upgraadeAgentHosts, run: getOcpNotUpgradingHost } = useRequest(
    OCP.getOcpNotUpgradingHost,
    {
      manual: true,
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );
  const { logData, setInstallStatus, setInstallResult } =
    useModel('ocpInstallData');
  const [openLog, setOpenLog] = useState(
    installResult === 'FAILED' ? true : false,
  );
  const { setIsReinstall, connectId, setInstallTaskId } =
    useModel('ocpInstallData');
  const upgraadeHosts = upgraadeAgentHosts?.data || {};

  // 重装ocp
  const {
    // data: reInstallOcpData,
    run: reInstallOcp,
    loading: reInstallOcpLoading,
  } = useRequest(OCP.reinstallOcp, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        res.data?.id && setInstallTaskId(res.data?.id);
        setIsReinstall(true);
        setInstallStatus('RUNNING');
        setCurrent(current - 1);
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 退出
  const { run: suicide, loading: suicideLoading } = useRequest(
    Process.suicide,
    {
      manual: true,
      onSuccess: (res) => {
        if (res?.success) {
          setInstallStatus('');
          setInstallResult('');
          history.push(`/quit?type=${isUpdate ? 'update' : 'install'}`);
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  // 销毁 OCP 安装残留
  const { run: destroyOcp, loading: destroyOCPLoading } = useRequest(
    OCP.destroyOcp,
    {
      manual: true,
      onSuccess: (data) => {
        if (data?.success) {
          setCurrent(3);
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  useEffect(() => {
    if (
      type === 'update' &&
      installStatus === 'FINISHED' &&
      installResult === 'SUCCESSFUL'
    ) {
      getOcpNotUpgradingHost();
    }
  }, [type, installStatus, installResult]);

  const columns = [
    {
      title: intl.formatMessage({
        id: 'OBD.component.InstallResult.ComponentName',
        defaultMessage: '组件名称',
      }),
      dataIndex: 'name',
      width: '20%',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.component.InstallResult.NodeIp',
        defaultMessage: '节点 IP',
      }),
      dataIndex: 'ip',
      render: (text, record) => {
        if (!text || text === '') {
          return '-';
        }
        const addressList = text.split(',');
        return addressList.map((item: string) => <Tag>{item}</Tag>);
      },
    },
  ];

  return (
    <div
      style={{
        backgroundColor: '#F5F8FE',
        paddingBottom: 0,
      }}
    >
      <Result
        style={{
          backgroundColor: '#F5F8FE',
        }}
        icon={
          <img
            src={
              installResult === 'SUCCESSFUL'
                ? '/assets/install/successful.png'
                : '/assets/install/failed.png'
            }
            alt="resultLogo"
            style={{
              width: 160,
              position: 'relative',
              right: '-8px',
              padding: 0,
            }}
          />
        }
        title={
          installResult === 'SUCCESSFUL' ? (
            <div>
              {type === 'update' ? (
                <span
                  data-aspm="c323709"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.component.InstallResult.UpgradeSuccessful',
                    defaultMessage: '升级成功',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.component.InstallResult.OcpUpgradedSuccessfully',
                    defaultMessage: 'OCP 升级成功',
                  })}
                </span>
              ) : (
                <span>
                  <>
                    {isHaveMetadb === 'install' ? (
                      <span
                        data-aspm="c323710"
                        data-aspm-desc={intl.formatMessage({
                          id: 'OBD.component.InstallResult.InstallationAndDeploymentNoMetadb',
                          defaultMessage: '安装部署无MetaDB部署成功',
                        })}
                        data-aspm-param={``}
                        data-aspm-expo
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.OcpDeployedSuccessfully',
                          defaultMessage: 'OCP 部署成功',
                        })}
                      </span>
                    ) : (
                      <span
                        data-aspm="c323708"
                        data-aspm-desc={intl.formatMessage({
                          id: 'OBD.component.InstallResult.MetadbIsDeployedSuccessfully',
                          defaultMessage: '安装部署有MetaDB部署成功',
                        })}
                        data-aspm-param={``}
                        data-aspm-expo
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.OcpDeployedSuccessfully',
                          defaultMessage: 'OCP 部署成功',
                        })}
                      </span>
                    )}
                  </>
                </span>
              )}
            </div>
          ) : (
            <>
              {type === 'update' ? (
                <div
                  data-aspm="c323713"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.component.InstallResult.UpgradeFailed',
                    defaultMessage: '升级失败',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.component.InstallResult.OcpUpgradeFailed',
                    defaultMessage: 'OCP 升级失败',
                  })}
                </div>
              ) : (
                <div>
                  <>
                    {isHaveMetadb === 'install' ? (
                      <span
                        data-aspm="c323714"
                        data-aspm-desc={intl.formatMessage({
                          id: 'OBD.component.InstallResult.InstallationAndDeploymentNoMetadb.1',
                          defaultMessage: '安装部署无MetaDB部署失败',
                        })}
                        data-aspm-param={``}
                        data-aspm-expo
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.OcpDeploymentFailed',
                          defaultMessage: 'OCP 部署失败',
                        })}
                      </span>
                    ) : (
                      <span
                        data-aspm="c323715"
                        data-aspm-desc={intl.formatMessage({
                          id: 'OBD.component.InstallResult.FailedToInstallAndDeploy',
                          defaultMessage: '安装部署有MetaDB部署失败',
                        })}
                        data-aspm-param={``}
                        data-aspm-expo
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.OcpDeploymentFailed',
                          defaultMessage: 'OCP 部署失败',
                        })}
                      </span>
                    )}
                  </>
                </div>
              )}
            </>
          )
        }
        subTitle={
          installResult === 'FAILED' &&
          installStatus === 'FINISHED' &&
          intl.formatMessage({
            id: 'OBD.component.InstallResult.PleaseCheckTheLogInformation',
            defaultMessage: '请查看日志信息获取失败原因，联系技术支持同学处理',
          })
        }
        {...restProps}
      />

      <div style={{ marginBottom: 16 }}>
        {installStatus === 'FINISHED' && installResult === 'SUCCESSFUL' ? (
          <>
            {type === 'update' ? (
              <Card
                divided={false}
                className={styles.upgradeReport}
                bordered={false}
                title={intl.formatMessage({
                  id: 'OBD.component.InstallResult.UpgradeReport',
                  defaultMessage: '升级报告',
                })}
                style={{
                  backgroundColor: '#fff',
                }}
                bodyStyle={{
                  padding: 24,
                  paddingTop: 0,
                }}
              >
                {upgraadeHosts?.address?.length > 0 && (
                  <Alert
                    type="info"
                    style={{
                      minHeight: 54,
                      marginBottom: 24,
                    }}
                    showIcon={true}
                    description={
                      <ul>
                        {/* 备份文件保存地址：/abc/def/hijk，可根据需要对备份文件进行维护管理 */}
                        <li>
                          {intl.formatMessage({
                            id: 'OBD.component.InstallResult.WeRecommendThatYouInstall',
                            defaultMessage:
                              '存在未升级 OCP Agent 的主机，建议您在 OCP 平台「主机管理」模块安装新版本 OCP Agent。',
                          })}
                          <br />
                          {upgraadeHosts?.address?.join()}
                        </li>
                        {/* <li>
                  ·备份文件保存地址：/abc/def/hijk, 可根据需要对备份文件进行维护管理
                  </li> */}
                      </ul>
                    }
                  />
                )}

                <Row gutter={[24, 16]}>
                  <Col span={24}>
                    <div className={styles.ocpVersion}>
                      {intl.formatMessage({
                        id: 'OBD.component.InstallResult.PreUpgradeVersion',
                        defaultMessage: '升级前版本：',
                      })}
                      <span>V {upgradeOcpInfo?.ocp_version}</span>
                    </div>
                    <div
                      style={{
                        float: 'left',
                        margin: '0 45px',
                        textAlign: 'center',
                        lineHeight: '69px',
                      }}
                    >
                      <ArrowIcon height={30} width={42} />
                    </div>
                    <div className={styles.ocpVersion}>
                      {intl.formatMessage({
                        id: 'OBD.component.InstallResult.UpgradedVersion',
                        defaultMessage: '升级后版本：',
                      })}

                      <span>V {upgradeOcpInfo?.upgrade_version}</span>
                      <NewIcon
                        size={36}
                        style={{
                          position: 'relative',
                          top: -12,
                        }}
                      />
                    </div>
                  </Col>
                </Row>
                <Table
                  bordered={true}
                  style={{
                    marginTop: 24,
                    borderRadius: 8,
                  }}
                  // loading={loading}
                  columns={columns}
                  pagination={false}
                  dataSource={
                    upgradeOcpInfo?.component ? upgradeOcpInfo?.component : []
                  }
                />

                <Space
                  style={{
                    marginTop: 16,
                  }}
                >
                  {intl.formatMessage({
                    id: 'OBD.component.InstallResult.Click',
                    defaultMessage: '点击',
                  })}

                  <a target="_blank" href={RELEASE_RECORD}>
                    {' '}
                    {intl.formatMessage({
                      id: 'OBD.component.InstallResult.OcpReleaseRecords',
                      defaultMessage: 'OCP 发布记录',
                    })}{' '}
                  </a>
                  {intl.formatMessage({
                    id: 'OBD.component.InstallResult.LearnMoreAboutTheNew',
                    defaultMessage: '了解新版本更多信息',
                  })}
                </Space>
              </Card>
            ) : (
              <Card
                className={styles.upgradeReport}
                bordered={false}
                title={intl.formatMessage({
                  id: 'OBD.component.InstallResult.AccessAddressAndAccountSecret',
                  defaultMessage: '访问地址及账密信息',
                })}
                style={{
                  backgroundColor: '#fff',
                }}
                bodyStyle={{
                  padding: 24,
                  paddingTop: 0,
                }}
              >
                <Alert
                  type="info"
                  showIcon={true}
                  style={{
                    marginBottom: 24,
                  }}
                  message={
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0 4px',
                        lineHeight: '32px',
                      }}
                    >
                      <div>
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.PleaseKeepTheFollowingAccess',
                          defaultMessage:
                            '请妥善保存以下访问地址及账密信息，及时更新 OCP\n                        初始密码，如需了解更多，请访问',
                        })}{' '}
                        <a target="_blank" href={OCP_DOCS}>
                          {intl.formatMessage({
                            id: 'OBD.component.InstallResult.OceanbaseDocumentCenter',
                            defaultMessage: 'OceanBase 文档中心',
                          })}
                        </a>
                      </div>
                      <Button
                        type="primary"
                        onClick={() => {
                          handleCopy(
                            ocpInfo ? JSON.stringify(ocpInfo, null, 4) : '',
                          );
                        }}
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.InstallResult.CopyInformation',
                          defaultMessage: '复制信息',
                        })}
                      </Button>
                    </div>
                  }
                />

                <Descriptions
                  layout="vertical"
                  column={3}
                  style={{
                    padding: 16,
                    backgroundColor: '#F5F8FE',
                  }}
                >
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: 'OBD.component.InstallResult.AccessAddress',
                      defaultMessage: '访问地址',
                    })}
                    style={{
                      borderRight: '1px solid #E8EAF3',
                    }}
                  >
                    {ocpInfo?.url?.join(',') || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: 'OBD.component.InstallResult.AdministratorAccount',
                      defaultMessage: '管理员账号',
                    })}
                    style={{
                      borderRight: '1px solid #E8EAF3',
                      paddingLeft: 16,
                    }}
                  >
                    {ocpInfo?.account || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item
                    label={intl.formatMessage({
                      id: 'OBD.component.InstallResult.InitialPassword',
                      defaultMessage: '初始密码',
                    })}
                    style={{
                      paddingLeft: 16,
                    }}
                  >
                    {ocpInfo?.password}
                    <a>
                      {ocpInfo?.password ? (
                        <CopyOutlined
                          onClick={() => handleCopy(ocpInfo?.password)}
                        />
                      ) : (
                        '-'
                      )}
                    </a>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}
          </>
        ) : null}
      </div>
      <Col span={24}>
        <Card
          bordered={false}
          divided={false}
          title={
            <Space>
              {type === 'update'
                ? intl.formatMessage({
                  id: 'OBD.component.InstallResult.UpgradeLogs',
                  defaultMessage: '升级日志',
                })
                : intl.formatMessage({
                  id: 'OBD.component.InstallResult.DeploymentLogs',
                  defaultMessage: '部署日志',
                })}
              <span
                style={{
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setOpenLog(!openLog);
                }}
              >
                {openLog ? <CaretDownOutlined /> : <CaretRightOutlined />}
              </span>
            </Space>
          }
          bodyStyle={{
            padding: 0,
          }}
          className={`${styles.installSubCard} resource-card card-background-color`}
          style={{
            background: installStatus === 'RUNNING' ? '#F8FAFE' : '#fff',
          }}
        >
          <pre
            className={styles.installLog}
            id="installLog"
            style={{ height: openLog ? 360 : 0 }}
          >
            {openLog && (
              <>
                {logData?.log}
                {installStatus === 'RUNNING' ? (
                  <div className={styles.shapeContainer}>
                    <div className={styles.shape} />
                    <div className={styles.shape} />
                    <div className={styles.shape} />
                    <div className={styles.shape} />
                  </div>
                ) : null}

                <div style={{ height: 60 }}>
                  <Spin spinning={installStatus === 'RUNNING'} />
                </div>
              </>
            )}
          </pre>
        </Card>
      </Col>
      <CustomFooter>
        {installResult === 'SUCCESSFUL' ? (
          <Button
            data-aspm="c323702"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.component.InstallResult.ExitTheInstaller',
              defaultMessage: '退出安装程序',
            })}
            data-aspm-param={``}
            data-aspm-expo
            type="primary"
            // loading={suicideLoading}
            onClick={() => {
              Modal.confirm({
                title: intl.formatMessage({
                  id: 'OBD.component.InstallResult.DoYouWantToExit',
                  defaultMessage: '是否要退出页面？',
                }),
                icon: (
                  <ExclamationCircleOutlined style={{ color: '#FF4B4B' }} />
                ),

                content: (
                  <div>
                    <div>
                      {intl.formatMessage({
                        id: 'OBD.component.InstallResult.BeforeExitingMakeSureThat',
                        defaultMessage:
                          '退出前，请确保已复制访问地址及账密信息',
                      })}
                    </div>
                    <a>
                      {intl.formatMessage({
                        id: 'OBD.component.InstallResult.CopyInformation',
                        defaultMessage: '复制信息',
                      })}
                      <CopyOutlined
                        onClick={() =>
                          handleCopy(
                            ocpInfo?.password
                              ? JSON.stringify(ocpInfo, null, 4)
                              : '',
                          )
                        }
                      />
                    </a>
                  </div>
                ),

                okText: intl.formatMessage({
                  id: 'OBD.component.InstallResult.Exit',
                  defaultMessage: '退出',
                }),
                okButtonProps: {
                  danger: true,
                },
                onOk: () => {
                  suicide();
                },
              });
            }}
          >
            {intl.formatMessage({
              id: 'OBD.component.InstallResult.Complete',
              defaultMessage: '完成',
            })}
          </Button>
        ) : (
          <>
            <ExitBtn />
            <Button
              loading={destroyOCPLoading}
              onClick={() => {
                destroyOcp({ id: connectId });
              }}
            >
              {intl.formatMessage({
                id: 'OBD.component.InstallResult.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            <Button
              type="primary"
              loading={reInstallOcpLoading}
              onClick={() => {
                Modal.confirm({
                  title: intl.formatMessage({
                    id: 'OBD.component.InstallResult.PleaseConfirmWhetherTheInstallation',
                    defaultMessage: '请确认是否已定位安装失败原因并修复问题？',
                  }),
                  icon: <ExclamationCircleOutlined />,
                  content: intl.formatMessage({
                    id: 'OBD.component.InstallResult.ReinstallationWillFirstCleanUp',
                    defaultMessage: '重新安装将先清理失败的 OCP 安装环境',
                  }),
                  okText: intl.formatMessage({
                    id: 'OBD.component.InstallResult.Ok',
                    defaultMessage: '确定',
                  }),
                  cancelText: intl.formatMessage({
                    id: 'OBD.component.InstallResult.Cancel',
                    defaultMessage: '取消',
                  }),
                  onOk: () => {
                    reInstallOcp({ id: connectId });
                  },
                });
              }}
            >
              {intl.formatMessage({
                id: 'OBD.component.InstallResult.Redeploy',
                defaultMessage: '重新部署',
              })}
            </Button>
          </>
        )}
      </CustomFooter>
    </div>
  );
};

export default InstallResult;
