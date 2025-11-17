import * as OCP from '@/services/ocp_installer_backend/OCP';
import * as Process from '@/services/ocp_installer_backend/Process';
import { errorHandler } from '@/utils';
import { handleCopy } from '@/utils/helper';
import { intl } from '@/utils/intl';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Col,
  Result,
  Space,
  Table,
  Tag,
} from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { Alert, Descriptions, Modal, } from 'antd';
import type { ResultProps } from 'antd/es/result';
import { isEmpty } from 'lodash';
import React, { useEffect, useState } from 'react';
import { history, useModel } from 'umi';
import CustomFooter from '@/component/CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import styles from './index.less';
import { ColumnsType } from 'antd/es/table';

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

const InstallFinished: React.FC<InstallResultProps> = () => {

  const {
    configData = {},
    setCurrentStep,
    selectedOmsType
  } = useModel('global');

  const {
    logData,
    setInstallStatus,
    setInstallResult,
    setIsReinstall,
    connectId: id,
    installResult,
    installStatus,
    setInstallTaskId
  } = useModel('ocpInstallData');

  const [openLog, setOpenLog] = useState(
    installResult === 'FAILED' ? true : false,
  );

  // 重装 OMS
  const {
    run: reinstallOms,
    loading: reinstallOmsLoading,
  } = useRequest(OCP.reinstallOms, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success && res.data) {
        const taskId = (res.data as any)?.id;
        if (taskId) {
          setInstallTaskId(taskId);
        }
        setIsReinstall(true);
        setInstallStatus('RUNNING');
        setCurrentStep(5);
      }
    },
    onError: (error: any) => {
      errorHandler({ request: error?.request, response: error?.response, data: error?.data });
    },
  });

  // 退出
  const { run: suicide, } = useRequest(
    Process.suicide,
    {
      manual: true,
      onSuccess: (res) => {
        if (res?.success) {
          setInstallStatus('');
          setInstallResult(undefined);
          history.push(`/quit?type=install`);
        }
      },
      onError: (error: any) => {
        errorHandler({ request: error?.request, response: error?.response, data: error?.data });
      },
    },
  );

  // 销毁 oms 安装残留
  const { run: destroyOms, loading: destroyOmsLoading } = useRequest(
    OCP.destroyOms,
    {
      manual: true,
      onSuccess: (data) => {
        if (data?.success) {
          setCurrentStep(3);
        }
      },
      onError: (error: any) => {
        errorHandler({ request: error?.request, response: error?.response, data: error?.data });
      },
    },
  );

  const omsConnectColumns: ColumnsType<API.ConnectionInfo> = [
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.RegionIdentifier',
        defaultMessage: '地域标识',
      }),
      dataIndex: 'cm_location',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.EnglishRegionIdentifier',
        defaultMessage: '英文地域标志',
      }),
      dataIndex: 'cm_region',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.AccessAddress',
        defaultMessage: '访问地址',
      }),
      dataIndex: 'cm_nodes',
      // 任意节点ip:nginx_server_port
      render: (text) => {
        return (
          <a href={`http://${text[0]}:${configData?.nginx_server_port}`} target="_blank">{text[0]}:{configData?.nginx_server_port}</a>
        )
      }
      ,
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.Account',
        defaultMessage: '账号',
      }),
      dataIndex: 'user',
      render: (_) => 'admin',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.Password',
        defaultMessage: '密码',
      }),
      dataIndex: 'password',
      render: (_) => intl.formatMessage({
        id: 'OBD.pages.Oms.InstallFinished.FirstLoginSetup',
        defaultMessage: '首次登陆设置',
      }),
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
              {intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.OmsDeploymentSuccessful',
                defaultMessage: 'OMS 部署成功！',
              })}
            </div>
          ) : (
            <div>
              {intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.OmsDeploymentFailed',
                defaultMessage: 'OMS 部署失败',
              })}
            </div>
          )
        }
        subTitle={
          installResult === 'FAILED' &&
          intl.formatMessage({
            id: 'OBD.component.InstallResult.PleaseCheckTheLogInformation',
            defaultMessage: '请查看日志信息获取失败原因，联系技术支持同学处理',
          })
        }
      />

      <div style={{ marginBottom: 16 }}>
        {installResult === 'SUCCESSFUL' ? (
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
                      id: 'OBD.pages.Oms.InstallFinished.PleaseSaveAccessAddressAndAccountInformation',
                      defaultMessage: '请妥善保存以下访问地址及账号信息，丢失后无法找回。',
                    })}
                  </div>
                  <Button
                    type="primary"
                    onClick={() => {
                      const data = (configData?.regions || [])?.map((item: any) => ({
                        cm_location: item.cm_location,
                        cm_region: item.cm_region,
                        cm_is_default: item.cm_is_default,
                        cm_url: `http://${item.cm_nodes[0]}:${configData?.nginx_server_port}`,
                      }))
                      handleCopy(
                        JSON.stringify(data || [], null, 4)
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

            <Table
              className={`${styles.connectTable} ob-table`}
              columns={omsConnectColumns as any}
              dataSource={configData?.regions || []}
              rowKey="cm_location"
              pagination={false}
            />
          </Card>
        ) : null}
      </div>
      <Col span={24}>
        <Card
          bordered={false}
          divided={false}
          title={
            <Space>
              {intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.DeploymentReport',
                defaultMessage: '部署报告',
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
            background: '#fff',
          }}
        >
          <Descriptions
            layout="vertical"
            column={3}
          >
            <Descriptions.Item
              label={intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.Product',
                defaultMessage: '产品',
              })}
            >
              OMS
              <Tag style={{ marginLeft: 6 }}>{selectedOmsType?.includes('ce') ? intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.CommunityEdition',
                defaultMessage: '社区版',
              }) : intl.formatMessage({
                id: 'OBD.pages.Oms.ConnectionInfo.CommercialEdition',
                defaultMessage: '商业版',
              })}</Tag>
            </Descriptions.Item>
            <Descriptions.Item
              label={intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.Version',
                defaultMessage: '版本',
              })}
            >
              V {selectedOmsType?.toUpperCase()}
            </Descriptions.Item>
            <Descriptions.Item
              label={intl.formatMessage({
                id: 'OBD.pages.Oms.InstallFinished.InstallationResult',
                defaultMessage: '安装结果',
              })}
            >
              {
                installResult === 'SUCCESSFUL'
                  ? <div >
                    <CheckCircleFilled style={{ color: '#4dcca2', marginRight: 6 }} />
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallFinished.Success',
                      defaultMessage: '成功',
                    })}
                  </div>
                  : <div>
                    <CloseCircleFilled style={{ color: 'rgba(255,75,75,1)', marginRight: 6 }} />
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.InstallFinished.Failed',
                      defaultMessage: '失败',
                    })}
                  </div>
              }

            </Descriptions.Item>
          </Descriptions>
          {
            openLog && <div style={{ marginBottom: 16, color: '#8592ad' }}>
              {intl.formatMessage({
                id: 'OBD.component.InstallResult.DeploymentLogs',
                defaultMessage: '部署日志',
              })}
            </div>
          }
          <pre
            className={styles.installLog}
            id="installLog"
            style={{
              height: openLog ? 360 : 0,
              padding: openLog ? 16 : 0,
              backgroundColor: '#f5f8fea6',
            }}
          >
            {openLog && (
              <>
                <div style={{ color: '#8592ad' }}>
                  {(() => {
                    // 优先使用 logData.log，如果没有则尝试 logData.items
                    if (logData) {
                      if ((logData as any)?.log) {
                        return (logData as any).log;
                      }
                      if (logData?.items && Array.isArray(logData.items) && logData.items.length > 0) {
                        return logData.items.map((item: any) => item.log).join('\n');
                      }
                    }
                    return '';
                  })()}
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
            onClick={() => {
              suicide();
            }}
          >
            {intl.formatMessage({
              id: 'OBD.component.InstallResult.Complete',
              defaultMessage: '完成',
            })}
          </Button>
        ) : (
          <>
            <Button
              loading={destroyOmsLoading}
              onClick={() => {
                destroyOms({ id });
              }}
            >
              {intl.formatMessage({
                id: 'OBD.component.InstallResult.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            <Button
              type="primary"
              loading={reinstallOmsLoading}
              onClick={() => {
                Modal.confirm({
                  title: intl.formatMessage({
                    id: 'OBD.component.InstallResult.PleaseConfirmWhetherTheInstallation',
                    defaultMessage: '请确认是否已定位安装失败原因并修复问题？',
                  }),
                  icon: <ExclamationCircleOutlined />,
                  content: intl.formatMessage({
                    id: 'OBD.pages.Oms.InstallFinished.ReinstallWillCleanFailedOmsInstallationEnvironment',
                    defaultMessage: '重新安装将会清理失败的 OMS 安装环境',
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
                    reinstallOms({ id });
                  },
                });
              }}
            >
              {intl.formatMessage({
                id: 'OBD.component.InstallResult.Redeploy',
                defaultMessage: '重新部署',
              })}
            </Button>
            <ExitBtn />
          </>
        )}
      </CustomFooter>
    </div >
  );
};

export default InstallFinished;
