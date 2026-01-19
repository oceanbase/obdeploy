import CustomFooter from '@/component/CustomFooter';
import DeployConfig from './Component/DeployConfig';
import ExitBtn from '@/component/ExitBtn';
import InstallProcess from '../InstallProcess';
import Steps from '@/component/Steps';
import { METADB_OMS_UPDATE, STEPS_KEYS_UPDATE_OMS } from '@/constant/configuration';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { errorHandler } from '@/utils';
import { intl } from '@/utils/intl';
import { Button, Form, message, Space, Tooltip } from '@oceanbase/design';
import { PageContainer } from '@oceanbase/ui';
import { useRequest } from 'ahooks';
import { find, isEmpty } from 'lodash';
import React, { useEffect, useState } from 'react';
import { useLocation, useModel } from 'umi';
import ConnectionInfo from './Component/ConnectionInfo';
import UpdatePreCheck from './Component/UpdatePreCheck';
import InstallFinished from '../InstallFinished';
import Backup from './Component/Backup';

const Update: React.FC = () => {
  const location = useLocation();
  const step = location.search?.split('=')[1];
  const [form] = Form.useForm();
  const {
    installStatus,
    installResult,
    setConnectId,
  } = useModel('ocpInstallData');
  const { ocpConfigData } = useModel('global');
  const [current, setCurrent] = useState(step ? Number(step) : -1);
  const [backupStatus, setBackupStatus] = useState('INIT');
  const [openBackupModal, setOpenBackupModal] = useState(false);
  const [checkErrorInfo, setCheckErrorInfo] = useState<string>('');

  const cluster_name = ocpConfigData?.cluster_name;
  const version = ocpConfigData?.version;

  // 发起 oms 的预检查
  const {
    run: precheckOmsUpgrade,
    refresh: refreshPrecheckOmsUpgrade,
    loading: precheckOmsUpgradeLoading,
  } = useRequest(OCP.precheckOmsUpgrade, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        getOmsUpgradePrecheckTask({
          cluster_name,
          task_id: res?.data?.id,
        });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // OMS 的预检查结果
  const {
    data: omsUpgradePrecheckTaskData,
    run: getOmsUpgradePrecheckTask,
    cancel: stopPreCheck,
    loading: getOmsUpgradePrecheckTaskLoading,
  } = useRequest(OCP.getOmsUpgradePrecheckTask, {
    manual: true,
    pollingInterval: 1000,
    onSuccess: (res) => {
      if (res?.success) {
        // 如果状态不是 RUNNING，停止轮询
        if (res?.data?.task_info?.status !== 'RUNNING') {
          stopPreCheck();
        }
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
      stopPreCheck();
    },
  });
  const omsUpgradePrecheckTask = omsUpgradePrecheckTaskData?.data;
  const precheckOmsUpgradeStatus = omsUpgradePrecheckTask?.task_info?.status;

  // 升级 oms
  const {
    run: upgradeOms,
    loading: upgradeOmsLoading,
  } = useRequest(OCP.upgradeOms, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        setCurrent(current + 1);
        setConnectId(res?.data?.id);
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const offlineUpgrade = ocpConfigData?.upgrade_mode === 'offline' && current === 0;

  const {
    run: backupOms,
    loading: backupOmsLoading,
  } = useRequest(OCP.backupOms, {
    manual: true,
    onSuccess: (res) => {
      if (res?.data?.success) {
        setOpenBackupModal(false);
        setBackupStatus('SUCCESSFUL');
        if (cluster_name && version) {
          upgradeOms({
            cluster_name,
            version,
            image_name: ocpConfigData?.image_name,
            upgrade_mode: ocpConfigData?.upgrade_mode,
          });
        }
      } else {
        setCheckErrorInfo(res?.data?.error);
        setOpenBackupModal(false);
        setBackupStatus('FAILED');
      }
    },
    onError: () => {
      setOpenBackupModal(false);
      setBackupStatus('FAILED');
    },
  });

  const handleSubmit = (currentStep: number) => {
    switch (currentStep) {
      case 0:
        break;
      // 预检查
      case 1:
        precheckOmsUpgrade({ cluster_name, default_oms_files_path: offlineUpgrade ? '' : ocpConfigData?.path });
        setCurrent(current + 1)
        break;
      // 备份
      case 2:
        setCurrent(current + 1);
        break;
      // 升级部署
      case 3:
        if (ocpConfigData?.backup_method === 'data_backup') {
          setBackupStatus('RUNNING');
          setOpenBackupModal(true);
          backupOms({
            backup_path: ocpConfigData?.backup_path,
            pre_check: false
          })
        } else if (ocpConfigData?.backup_method === 'not_backup') {
          if (cluster_name && version) {
            upgradeOms({
              cluster_name,
              version,
              image_name: ocpConfigData?.image_name,
              upgrade_mode: ocpConfigData?.upgrade_mode,
            });
          }
        }
        break;
    }
  };

  const preStep = () => {
    setCurrent(current - 1);
    if (current === 1) {
      stopPreCheck();
    }
  };

  // 获取已部署的集群列表 适用于 OBD 部署
  const { data: clusterListsRes, run: getClusterList, loading: getClusterListLoading } = useRequest(
    OCP.listOmsDeployments,
    {
      manual: true,
      onError: () => {
        // 静默处理错误，避免显示不必要的错误提示
        // 集群列表获取失败不影响升级流程
      },
    },
  );
  const clusterList = clusterListsRes?.data;


  const {
    run: getOmsDisplay,
    data: omsDisplayData,
  } = useRequest(OCP.getOmsDisplay, {
    manual: true,
  });

  useEffect(() => {
    if (current === -1) {
      getClusterList();
    }
    if (current === 3 && installResult === 'SUCCESSFUL') {
      getOmsDisplay();
    }
  }, [current, installResult]);

  return (
    <PageContainer style={{ paddingBottom: 90, backgroundColor: '#f5f8ff' }}>
      {installResult !== 'FAILED' && installResult !== 'SUCCESSFUL' && (
        <Steps
          currentStep={current + 2}
          stepsItems={METADB_OMS_UPDATE}
          showStepsKeys={STEPS_KEYS_UPDATE_OMS}
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
            connectForm={form}
            setCurrent={setCurrent}
            clusterList={clusterList}
            getClusterListLoading={getClusterListLoading}
          />
        )}

        {current == 0 && (
          <ConnectionInfo
            type={'update'}
          />
        )}

        {current == 1 && (
          <UpdatePreCheck
            omsUpgradePrecheckTask={omsUpgradePrecheckTask}
            precheckOmsUpgradeLoading={
              precheckOmsUpgradeLoading || getOmsUpgradePrecheckTaskLoading
            }
            refreshPrecheckOmsUpgrade={refreshPrecheckOmsUpgrade}
          />
        )}
        {current == 2 && (
          <Backup
            current={current}
            setCurrent={setCurrent}
            setBackupStatus={setBackupStatus}
            backupStatus={backupStatus}
            openBackupModal={openBackupModal}
            setOpenBackupModal={setOpenBackupModal}
            checkErrorInfo={checkErrorInfo}
            setCheckErrorInfo={setCheckErrorInfo}
            backupOmsLoading={backupOmsLoading}
          />
        )}
        {
          current == 3 &&
          (
            installStatus === 'RUNNING' ?
              <InstallProcess
                type="update"
              />
              :
              <InstallFinished
                type="update"
                setCurrent={setCurrent}
              />
          )
        }
      </div>
      {current === 3 && installStatus === 'RUNNING' ? null : (
        <>
          {current !== -1 && (
            <CustomFooter>
              <Space size={16}>
                {current === 3 && installStatus === 'RUNNING' ? null : (
                  <ExitBtn />
                )}
                {current < 3 ? (
                  <>
                    {(
                      <Button onClick={() => preStep()}>
                        {intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.PreviousStep',
                          defaultMessage: '上一步',
                        })}
                      </Button>
                    )}
                    <Tooltip
                      title={
                        (current === 1 &&
                          precheckOmsUpgradeStatus === 'RUNNING' && !isEmpty(omsUpgradePrecheckTask) &&
                          intl.formatMessage({
                            id: 'OBD.OcpInstaller.Update.InThePreCheckProcess.1',
                            defaultMessage: '预检查中，暂不支持进入下一步',
                          }))
                      }
                    >
                      <Button
                        disabled={
                          (current === 1 &&
                            omsUpgradePrecheckTask?.task_info?.result !== 'SUCCESSFUL')
                          || (current === 2 && backupStatus !== 'SUCCESSFUL' && ocpConfigData?.backup_method === 'data_backup')
                        }
                        type="primary"
                        loading={
                          upgradeOmsLoading
                          || (current === 0 && precheckOmsUpgradeLoading)
                        }
                        onClick={() => {
                          handleSubmit(current + 1);
                        }}
                      >
                        {intl.formatMessage({
                          id: 'OBD.OcpInstaller.Update.NextStep',
                          defaultMessage: '下一步',
                        })}
                      </Button>
                    </Tooltip>
                  </>
                ) : null}
                {
                  current === 3 && installResult === 'SUCCESSFUL' &&
                  <Button
                    type="primary"
                    onClick={() => {
                      if (omsDisplayData?.data) {
                        // 确保 URL 是完整的，如果不是则以 http:// 开头
                        // omsDisplayData.data 可能是字符串或对象，需要转换为字符串
                        const urlValue = typeof (omsDisplayData.data as any) === 'string'
                          ? (omsDisplayData.data as any)
                          : String(omsDisplayData.data);
                        let url = urlValue;
                        // 如果 URL 不是以 http:// 或 https:// 开头，添加 http:// 前缀
                        if (url && typeof url === 'string' && !url.startsWith('http://') && !url.startsWith('https://')) {
                          url = `http://${url}`;
                        }
                        if (url && typeof url === 'string') {
                          window.open(url, '_blank');
                        }
                      }
                    }}
                  >
                    {intl.formatMessage({
                      id: 'OBD.pages.Oms.Update.GoToExperienceNewVersion',
                      defaultMessage: '去体验新版',
                    })}
                  </Button>
                }


              </Space>
            </CustomFooter>
          )}
        </>
      )}
    </PageContainer>
  );
};

export default Update;
