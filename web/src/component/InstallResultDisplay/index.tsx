import { intl } from '@/utils/intl';
import React, { useEffect } from 'react';
// import { useSelector } from 'umi';
import {
  Result,
  Descriptions,
  Card,
  Space,
  Table,
  Typography,
  Button,
  Row,
  Col,
  Tag,
} from '@oceanbase/design';
import { ProCard } from '@ant-design/pro-components';
import { useRequest } from 'ahooks';
import { useModel } from 'umi';
import { Alert } from 'antd';
import { errorHandler } from '@/utils';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import type { ResultProps } from 'antd/es/result';
import ArrowIcon from '@/component/Icon/ArrowIcon';
import NewIcon from '@/component/Icon/NewIcon';
import { copyText } from '@/utils';
import styles from './index.less';

const { Text } = Typography;

export interface InstallResultDisplayProps extends ResultProps {
  upgradeOcpInfo?: API.connectMetaDB;
  ocpInfo?: any;
  installStatus?: string; // RUNNING, FINISHED
  installResult?: string; // SUCCESSFUL, FAILED
  taskId?: number;
  installType?: string;
  type?: string; // install  update
}

const InstallResultDisplay: React.FC<InstallResultDisplayProps> = ({
  ocpInfo,
  upgradeOcpInfo,
  installStatus,
  installResult,
  type,
  installType,
  ...restProps
}) => {
  let isHaveMetadb;
  const { ocpConfigData, RELEASE_RECORD, OCP_DOCS } = useModel('global');
  const version: string = ocpConfigData?.components?.ocpserver?.version;
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

  const upgraadeHosts = upgraadeAgentHosts?.data || {};

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
        id: 'OBD.component.InsstallResult.ComponentName',
        defaultMessage: '组件名称',
      }),
      dataIndex: 'name',
      width: '20%',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.component.InsstallResult.NodeIp',
        defaultMessage: '节点 IP',
      }),
      dataIndex: 'ip',
      render: (ip: string[]) => {
        if (!ip || !ip.length) {
          return '-';
        }
        return ip.map((item: string) => <Tag>{item}</Tag>);
      },
    },
  ];

  return (
    <div
      style={{
        backgroundColor: installType === 'OCP' ? '#F5F8FE' : '#fff',
        paddingBottom: installType === 'MetaDB' ? 24 : 0,
      }}
    >
      <Result
        style={{
          backgroundColor: installType === 'OCP' ? '#F5F8FE' : '#fff',
          paddingBottom: 0,
        }}
        icon={
          <img
            src={
              installResult === 'SUCCESSFUL'
                ? installType === 'OCP'
                  ? '/assets/install/successful.png'
                  : '/assets/install/metadbSuccessful.png'
                : installType === 'OCP'
                  ? '/assets/install/failed.png'
                  : '/assets/install/metadbFailed.png'
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
                    id: 'OBD.component.InsstallResult.UpgradeSuccessful',
                    defaultMessage: '升级成功',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.component.InsstallResult.OcpUpgradedSuccessfully',
                    defaultMessage: 'OCP 升级成功',
                  })}
                </span>
              ) : (
                <span>
                  {installType === 'OCP' ? (
                    <>
                      {isHaveMetadb === 'install' ? (
                        <span
                          data-aspm="c323710"
                          data-aspm-desc={intl.formatMessage({
                            id: 'OBD.component.InsstallResult.InstallationAndDeploymentNoMetadb',
                            defaultMessage: '安装部署无MetaDB部署成功',
                          })}
                          data-aspm-param={``}
                          data-aspm-expo
                        >
                          {intl.formatMessage({
                            id: 'OBD.component.InsstallResult.OcpDeployedSuccessfully',
                            defaultMessage: 'OCP 部署成功',
                          })}
                        </span>
                      ) : (
                        <span
                          data-aspm="c323708"
                          data-aspm-desc={intl.formatMessage({
                            id: 'OBD.component.InsstallResult.MetadbIsDeployedSuccessfully',
                            defaultMessage: '安装部署有MetaDB部署成功',
                          })}
                          data-aspm-param={``}
                          data-aspm-expo
                        >
                          {intl.formatMessage({
                            id: 'OBD.component.InsstallResult.OcpDeployedSuccessfully',
                            defaultMessage: 'OCP 部署成功',
                          })}
                        </span>
                      )}
                    </>
                  ) : (
                    <span
                      data-aspm="c323712"
                      data-aspm-desc={intl.formatMessage({
                        id: 'OBD.component.InsstallResult.InstallationAndDeploymentMetadbDeployment',
                        defaultMessage: '安装部署MetaDB部署成功',
                      })}
                      data-aspm-param={``}
                      data-aspm-expo
                    >
                      {intl.formatMessage({
                        id: 'OBD.component.InsstallResult.MetadbDeployedSuccessfully',
                        defaultMessage: 'MetaDB 部署成功',
                      })}
                    </span>
                  )}
                </span>
              )}
            </div>
          ) : (
            <>
              {type === 'update' ? (
                <div
                  data-aspm="c323713"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.component.InsstallResult.UpgradeFailed',
                    defaultMessage: '升级失败',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.component.InsstallResult.OcpUpgradeFailed',
                    defaultMessage: 'OCP 升级失败',
                  })}
                </div>
              ) : (
                <div>
                  {installType === 'OCP' ? (
                    <>
                      {isHaveMetadb === 'install' ? (
                        <span
                          data-aspm="c323714"
                          data-aspm-desc={intl.formatMessage({
                            id: 'OBD.component.InsstallResult.InstallationAndDeploymentNoMetadb.1',
                            defaultMessage: '安装部署无MetaDB部署失败',
                          })}
                          data-aspm-param={``}
                          data-aspm-expo
                        >
                          {intl.formatMessage({
                            id: 'OBD.component.InsstallResult.OcpDeploymentFailed',
                            defaultMessage: 'OCP 部署失败',
                          })}
                        </span>
                      ) : (
                        <span
                          data-aspm="c323715"
                          data-aspm-desc={intl.formatMessage({
                            id: 'OBD.component.InsstallResult.FailedToInstallAndDeploy',
                            defaultMessage: '安装部署有MetaDB部署失败',
                          })}
                          data-aspm-param={``}
                          data-aspm-expo
                        >
                          {intl.formatMessage({
                            id: 'OBD.component.InsstallResult.OcpDeploymentFailed',
                            defaultMessage: 'OCP 部署失败',
                          })}
                        </span>
                      )}
                    </>
                  ) : (
                    <span
                      data-aspm="c323712"
                      data-aspm-desc={intl.formatMessage({
                        id: 'OBD.component.InsstallResult.FailedToInstallAndDeploy.1',
                        defaultMessage: '安装部署MetaDB部署失败',
                      })}
                      data-aspm-param={``}
                      data-aspm-expo
                    >
                      {intl.formatMessage({
                        id: 'OBD.component.InsstallResult.MetadbDeploymentFailed',
                        defaultMessage: 'MetaDB 部署失败',
                      })}
                    </span>
                  )}
                </div>
              )}
            </>
          )
        }
        subTitle={
          installResult === 'FAILED' &&
          installStatus === 'FINISHED' &&
          intl.formatMessage({
            id: 'OBD.component.InsstallResult.PleaseCheckTheLogInformation',
            defaultMessage: '请查看日志信息获取失败原因，联系技术支持同学处理',
          })
        }
        {...restProps}
      />

      {installStatus === 'FINISHED' && (
        <>
          {installStatus === 'FINISHED' && installResult === 'SUCCESSFUL' ? (
            <>
              {type === 'update' ? (
                <Card
                  divided={false}
                  className={styles.upgradeReport}
                  bordered={false}
                  title={intl.formatMessage({
                    id: 'OBD.component.InsstallResult.UpgradeReport',
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
                  <Alert
                    type="info"
                    style={{
                      marginBottom: 24,
                    }}
                    showIcon={true}
                    description={intl.formatMessage({
                      id: 'OBD.component.InsstallResult.TheSystemWillUpgradeOcp',
                      defaultMessage:
                        '系统将默认升级 OCP Agent，请前往 OCP 任务中心查看升级进度',
                    })}
                  />
                  <Row gutter={[24, 16]}>
                    <Col span={24} className={styles.versionContainer}>
                      <div className={styles.ocpVersion}>
                        {intl.formatMessage({
                          id: 'OBD.component.InsstallResult.PreUpgradeVersion',
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
                          id: 'OBD.component.InsstallResult.UpgradedVersion',
                          defaultMessage: '升级后版本：',
                        })}
                        <span>
                          V {version}{' '}
                          <NewIcon
                            size={36}
                            className={styles.newVersionIcon}
                          />
                        </span>
                      </div>
                    </Col>
                  </Row>
                  <ProCard
                    type="inner"
                    className={`${styles.componentCard}`}
                    style={{ border: '1px solid #e2e8f3' }}
                  //   key={oceanBaseInfo.group}
                  >
                    <Table
                      className={`${styles.componentTable} ob-table`}
                      rowKey="name"
                      // loading={loading}
                      columns={columns}
                      pagination={false}
                      dataSource={
                        upgradeOcpInfo?.component
                          ? upgradeOcpInfo?.component
                          : []
                      }
                    />
                  </ProCard>
                  <Space
                    style={{
                      marginTop: 16,
                    }}
                  >
                    {intl.formatMessage({
                      id: 'OBD.component.InsstallResult.Click',
                      defaultMessage: '点击',
                    })}

                    <a target="_blank" href={RELEASE_RECORD}>
                      {' '}
                      {intl.formatMessage({
                        id: 'OBD.component.InsstallResult.OcpReleaseRecords',
                        defaultMessage: 'OCP 发布记录',
                      })}{' '}
                    </a>
                    {intl.formatMessage({
                      id: 'OBD.component.InsstallResult.LearnMoreAboutTheNew',
                      defaultMessage: '了解新版本更多信息',
                    })}
                  </Space>
                </Card>
              ) : (
                <>
                  {installType === 'OCP' && (
                    <Card
                      className={styles.upgradeReport}
                      bordered={false}
                      title={intl.formatMessage({
                        id: 'OBD.component.InsstallResult.AccessAddressAndAccountSecret',
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
                          height: 54,
                          marginBottom: 24,
                        }}
                        message={
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              padding: '0 4px',
                              lineHeight: '32px',
                            }}
                          >
                            <div>
                              {intl.formatMessage({
                                id: 'OBD.component.InsstallResult.PleaseKeepTheFollowingAccess',
                                defaultMessage:
                                  '请妥善保存以下访问地址及账密信息，及时更新 OCP\n                              初始密码，如需了解更多，请访问',
                              })}{' '}
                              <a target="_blank" href={OCP_DOCS}>
                                {intl.formatMessage({
                                  id: 'OBD.component.InsstallResult.OceanbaseDocumentCenter',
                                  defaultMessage: 'OceanBase 文档中心',
                                })}
                              </a>
                            </div>
                            <Button
                              type="primary"
                              onClick={() => {
                                copyText(
                                  ocpInfo
                                    ? JSON.stringify(ocpInfo, null, 4)
                                    : '',
                                );
                              }}
                            >
                              {intl.formatMessage({
                                id: 'OBD.component.InsstallResult.CopyInformation',
                                defaultMessage: '复制信息',
                              })}
                            </Button>
                          </div>
                        }
                      />

                      <Descriptions
                        layout="vertical"
                        column={installType === 'OCP' ? 3 : 2}
                        style={{
                          padding: 16,
                          backgroundColor: '#F5F8FE',
                        }}
                      >
                        <Descriptions.Item
                          label={intl.formatMessage({
                            id: 'OBD.component.InsstallResult.AccessAddress',
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
                            id: 'OBD.component.InsstallResult.AdministratorAccount',
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
                            id: 'OBD.component.InsstallResult.InitialPassword',
                            defaultMessage: '初始密码',
                          })}
                          style={{
                            paddingLeft: 16,
                          }}
                        >
                          {ocpInfo?.password ? (
                            <Text
                              copyable={{
                                text: ocpInfo?.password,
                              }}
                            >
                              {ocpInfo?.password}
                            </Text>
                          ) : (
                            '-'
                          )}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  )}
                </>
              )}
            </>
          ) : null}
        </>
      )}
    </div>
  );
};

export default InstallResultDisplay;
