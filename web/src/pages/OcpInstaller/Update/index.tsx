import CustomFooter from '@/component/CustomFooter';
import DeployConfig from '@/component/DeployConfig';
import ExitBtn from '@/component/ExitBtn';
import InstallProcess from '@/component/InstallProcess';
import Steps from '@/component/Steps';
import { METADB_OCP_UPDATE, STEPS_KEYS_UPDATE } from '@/constant/configuration';
import {
  destroyDeployment,
  getDestroyTaskInfo,
} from '@/services/ob-deploy-web/Deployments';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { errorHandler } from '@/utils';
import { intl } from '@/utils/intl';
import { Button, Form, message, Space, Tooltip } from '@oceanbase/design';
import { PageContainer } from '@oceanbase/ui';
import { useRequest } from 'ahooks';
import { find } from 'lodash';
import React, { useEffect, useState } from 'react';
import { history, useLocation, useModel } from 'umi';
import { encrypt } from '@/utils/encrypt';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import ConnectionInfo from './Component/ConnectionInfo';
import UpdatePreCheck from './Component/UpdatePreCheck';

const Update: React.FC = () => {
  const location = useLocation();
  const step = location.search?.split('=')[1];
  const [form] = Form.useForm();
  const [systemUserForm] = Form.useForm();
  const { validateFields } = form;
  const {
    checkConnectInfo,
    setCheckConnectInfo,
    installStatus,
    setInstallStatus,
    installResult,
    setInstallResult,
    needDestroy
  } = useModel('ocpInstallData');
  const { ocpConfigData, setOcpConfigData } = useModel('global');
  const [current, setCurrent] = useState(step ? Number(step) : -1);
  const [precheckNoPassed, setPrecheckNoPassed] = useState(false);
  const [preCheckLoading, setPreCheckLoading] = useState<boolean>(false);
  const [allowInputUser, setAllowInputUser] = useState<boolean>(true);
  // const [serverErrorInfo, setServerErrorInfo] = useState();
  // 操作系统用户验证状态
  const [checkStatus, setCheckStatus] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');

  const { components = {} } = ocpConfigData;
  const { oceanbase = {}, ocpserver = {} } = components;
  const cluster_name = oceanbase?.appname;
  const version = ocpserver?.version;
  const package_hash = ocpserver?.package_hash;

  useEffect(() => {
    if (cluster_name && !upgradeOcpInfo?.id && step === 2) {
      upgradeOcp({
        cluster_name,
        version,
        usable: package_hash,
      });
    }
  }, [cluster_name, step]);

  const {
    data: connectReqData,
    run: connectMetaDB,
    loading,
  } = useRequest(OCP.connectMetaDB, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
        if (data?.user) {
          setAllowInputUser(false);
          systemUserForm.setFieldValue('user', data.user);
        }
        setCheckConnectInfo('success');
      } else {
        setCheckConnectInfo('fail');
      }
    },
    onError: ({ response, data }: any) => {
      setCheckConnectInfo('fail');
      // const errorInfo = data?.msg || data?.detail || response?.statusText;
      // Modal.error({
      //   title: 'MetaDB 连接失败，请检查连接配置',
      //   icon: <CloseCircleOutlined />,
      //   content: errorInfo,
      //   okText: '我知道了',
      // });
    },
  });

  const updateInfo = connectReqData?.data;

  const { run: createOcpPrecheck } = useRequest(OCP.createUpgradePrecheck, {
    manual: true,
    onSuccess: (res) => {
      precheckOcpUpgrade({ cluster_name });
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 发起OCP的预检查
  const {
    run: precheckOcpUpgrade,
    refresh: refreshPrecheckOcpUpgrade,
    loading: precheckOcpUpgradeLoading,
  } = useRequest(OCP.precheckOcpUpgrade, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        history.push('/update');
        getOcpUpgradePrecheckTask({
          cluster_name,
          task_id: res?.data?.id,
        });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // OCP的预检查结果
  const {
    data: ocpUpgradePrecheckTaskData,
    run: getOcpUpgradePrecheckTask,
    cancel: stopPreCheck,
  } = useRequest(OCP.getOcpUpgradePrecheckTask, {
    manual: true,
    pollingInterval: 1000,
    onSuccess: (res) => {
      if (res?.success) {
        if (res?.data?.task_info?.status !== 'RUNNING') {
          stopPreCheck();
          setPreCheckLoading(false);
        } else {
          setPreCheckLoading(true);
        }
        if (find(res.data?.precheck_result || [], ['result', 'FAILED'])) {
          setPrecheckNoPassed(true);
        } else {
          setPrecheckNoPassed(false);
        }
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const ocpUpgradePrecheckTask = ocpUpgradePrecheckTaskData?.data;
  const precheckOcpUpgradeStatus = ocpUpgradePrecheckTask?.task_info?.status;
  const precheckOcpUpgradeResult = ocpUpgradePrecheckTask?.task_info?.result;

  // 升级ocp
  const {
    data: upgradeOcpData,
    run: upgradeOcp,
    refresh,
    loading: upgradeOcpLoading,
  } = useRequest(OCP.upgradeOcp, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        getOcpInfo({
          cluster_name,
        });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 清理环境
  const { run: handleDestroyDeployment } = useRequest(destroyDeployment, {
    manual: true,
    onSuccess: ({ success }) => {
      if (success) {
        handleGetDestroyTaskInfo({ name: cluster_name });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 获取清理结果
  const { run: handleGetDestroyTaskInfo, cancel: stopGetDestroyTaskInfo } =
    useRequest(getDestroyTaskInfo, {
      manual: true,
      pollingInterval: 1000,
      onSuccess: ({ success, data }) => {
        if (success && data?.status !== 'RUNNING') {
          stopGetDestroyTaskInfo();
          if (data?.status === 'SUCCESSFUL') {
            refresh();
            setInstallStatus('RUNNING');
          }
          if (data?.status === 'FAILED') {
            message.error(data?.msg);
          }
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    });

  const upgradeOcpInfo = upgradeOcpData?.data || {};

  // 获取ocp 信息
  const {
    data: ocpInfoData,
    run: getOcpInfo,
    loading: getOcpInfoLoading,
  } = useRequest(OCP.getOcpInfo, {
    manual: true,
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const ocpInfo = ocpInfoData?.data || {};

  const handleSubmit = (currentStep: number) => {
    switch (currentStep) {
      case 0:
        break;
      case 1:
        createOcpPrecheck({ name: cluster_name });
        break;
      case 2:
        if (cluster_name && version) {
          upgradeOcp({
            cluster_name,
            version,
            usable: package_hash,
          }).then(() => {
            setCurrent(current + 1);
          });
        }
        break;
      default:
        break;
    }
  };

  const handleCheck = () => {
    validateFields().then(async (values) => {
      const { host, port, database, accessUser, accessCode } = values;
      const { data: publicKey } = await getPublicKey();
      setOcpConfigData({
        ...ocpConfigData,
        updateConnectInfo: {
          ...ocpConfigData.updateConnectInfo,
          ...values,
        },
      });
      connectMetaDB({
        host,
        port,
        database,
        user: accessUser,
        password: encrypt(accessCode, publicKey) || accessCode,
        cluster_name,
      });
    });
  };

  const preStep = () => {
    setCurrent(current - 1);
  };

  const resetConnectState = () => {
    systemUserForm.setFieldsValue({
      user: '',
      password: '',
      systemPort: 22,
    });
    setCheckConnectInfo('unchecked');
  };

  return (
    <PageContainer style={{ paddingBottom: 90, backgroundColor: '#f5f8ff' }}>
      {installResult !== 'FAILED' && installResult !== 'SUCCESSFUL' && (
        <Steps
          currentStep={current + 2}
          stepsItems={METADB_OCP_UPDATE}
          showStepsKeys={STEPS_KEYS_UPDATE}
        />
      )}

      <div
        className="page-body"
        style={{
          paddingTop: installStatus !== 'RUNNING' && current === 2 ? 0 : 150,
          width: '1040px',
          margin: '0 auto',
          overflow: 'auto',
        }}
      >
        {current == -1 && (
          <DeployConfig
            current={current}
            clearConnection={resetConnectState}
            connectForm={form}
            setCurrent={setCurrent}
          />
        )}

        {current == 0 && (
          <ConnectionInfo
            // upgraadeHosts={upgraadeHosts}
            allowInputUser={allowInputUser}
            form={form}
            systemUserForm={systemUserForm}
            updateInfo={updateInfo}
            handleCheck={handleCheck}
            checkLoading={loading}
            checkConnectInfo={checkConnectInfo}
            setCheckConnectInfo={setCheckConnectInfo}
            checkStatus={checkStatus}
            setCheckStatus={setCheckStatus}
          />
        )}

        {current == 1 && (
          <UpdatePreCheck
            updateInfo={updateInfo}
            refresh={refreshPrecheckOcpUpgrade}
            changePrecheckNoPassed={(val) => {
              setPrecheckNoPassed(val);
            }}
            getOcpInfoLoading={getOcpInfoLoading}
            ocpUpgradePrecheckTask={ocpUpgradePrecheckTask}
            precheckOcpUpgradeLoading={
              precheckOcpUpgradeLoading || preCheckLoading
            }
            cluster_name={cluster_name}
          />
        )}

        {current == 2 && (
          <InstallProcess
            installType="OCP"
            type="update"
            installInfo={upgradeOcpInfo}
            upgradeOcpInfo={updateInfo}
            ocpInfo={ocpInfo}
            cluster_name={cluster_name}
            installStatus={installStatus || ''}
            setInstallStatus={setInstallStatus}
            setInstallResult={setInstallResult}
          />
        )}
      </div>
      {current === 2 && installStatus === 'RUNNING' ? null : (
        <>
          {current !== -1 && (
            <CustomFooter>
              <Space size={16}>
                {current === 2 && installStatus === 'RUNNING' ? null : (
                  <ExitBtn />
                )}

                {current < 2 ? (
                  <>
                    {current > 0 && (
                      <Tooltip
                        title={
                          current === 1 &&
                            precheckOcpUpgradeLoading ?
                            intl.formatMessage({
                              id: 'OBD.OcpInstaller.Update.InThePreCheckProcess',
                              defaultMessage: '预检查中，暂不支持进入上一步',
                            }) : ''
                        }
                      >
                        <Button
                          disabled={current === 1 && precheckOcpUpgradeLoading}
                          onClick={() => {
                            // setCheckConnectInfo('unchecked')
                            setCheckStatus('unchecked');
                            setCurrent(current > 0 ? current - 1 : 0);
                            history.push('/update');
                          }}
                        >
                          {intl.formatMessage({
                            id: 'OBD.OcpInstaller.Update.PreviousStep',
                            defaultMessage: '上一步',
                          })}
                        </Button>
                      </Tooltip>
                    )}

                    {current === 0 && (
                      <Button onClick={() => preStep()}>
                        {intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.PreviousStep',
                          defaultMessage: '上一步',
                        })}
                      </Button>
                    )}

                    <Tooltip
                      title={
                        current === 1 &&
                        precheckOcpUpgradeStatus === 'RUNNING' &&
                        intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.InThePreCheckProcess.1',
                          defaultMessage: '预检查中，暂不支持进入下一步',
                        })
                      }
                    >

                      <Button
                        disabled={
                          (current === 1 &&
                            (precheckOcpUpgradeStatus === 'RUNNING' ||
                              precheckNoPassed)) ||
                          checkStatus !== 'success'
                        }
                        type="primary"
                        loading={
                          loading ||
                          precheckOcpUpgradeStatus === 'RUNNING' ||
                          upgradeOcpLoading
                        }
                        onClick={() => {
                          if (
                            current === 1 &&
                            ocpUpgradePrecheckTask?.task_info?.status ===
                            'FINISHED' &&
                            (ocpUpgradePrecheckTask?.task_info?.result ===
                              'SUCCESSFUL' ||
                              !precheckNoPassed)
                          ) {
                            handleSubmit(current + 1);
                            history.push('/update');
                          } else if (current === 0) {
                            validateFields().then((val) => {
                              setOcpConfigData({
                                ...ocpConfigData,
                                updateConnectInfo: {
                                  ...ocpConfigData.updateConnectInfo,
                                  ...val,
                                },
                              });
                              setCurrent(current + 1);
                              history.push('/update');
                            });
                          } else {
                            handleSubmit(current);
                          }
                        }}
                      >
                        {current === 1 &&
                          ocpUpgradePrecheckTask?.task_info?.status !==
                          'FINISHED' &&
                          ocpUpgradePrecheckTask?.task_info?.result !==
                          'SUCCESSFUL'
                          ? intl.formatMessage({
                            id: 'OBD.OcpInstaller.Update.PreCheck',
                            defaultMessage: '预检查',
                          })
                          : intl.formatMessage({
                            id: 'OBD.OcpInstaller.Update.NextStep',
                            defaultMessage: '下一步',
                          })}
                      </Button>
                    </Tooltip>
                  </>
                ) : (
                  <>
                    {installResult === 'FAILED' ? (
                      <Button
                        data-aspm="c323703"
                        data-aspm-desc={intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.UpgradeAgain',
                          defaultMessage: '重新升级',
                        })}
                        data-aspm-param={``}
                        data-aspm-expo
                        type="primary"
                        disabled={precheckOcpUpgradeLoading || preCheckLoading}
                        loading={precheckOcpUpgradeLoading || preCheckLoading}
                        onClick={() => {
                          if (needDestroy) {
                            handleDestroyDeployment({ name: cluster_name });
                          } else {
                            refresh();
                            setInstallStatus('RUNNING');
                          }
                        }}
                      >
                        {intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.UpgradeAgain',
                          defaultMessage: '重新升级',
                        })}
                      </Button>
                    ) : null}
                  </>
                )}
              </Space>
            </CustomFooter>
          )}
        </>
      )}
    </PageContainer>
  );
};

export default Update;
