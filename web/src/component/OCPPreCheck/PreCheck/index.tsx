import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import { message } from 'antd';

import * as OCP from '@/services/ocp_installer_backend/OCP';
import { useRequest } from 'ahooks';
import { getErrorInfo, errorHandler } from '@/utils';
import PreCehckComponent from '@/component/PreCheck/preCheck';
import { formatOcpPreCheckStatusData } from '../helper';
import NP from 'number-precision';

interface PreCheckProps {
  isNewDB: boolean;
}

// result: RUNNING | FALIED | SUCCESSFUL
// status: RUNNING | FINISHED
export default function PreCheck({
  current,
  setCurrent,
}: PreCheckProps & API.StepProp) {
  const {
    setCheckOK,
    setErrorVisible,
    setErrorsList,
    errorsList,
    ocpConfigData,
    ERR_CODE
  } = useModel('global');
  const { setInstallTaskId } = useModel('ocpInstallData');

  const { connectId } = useModel('ocpInstallData');
  const [statusData, setStatusData] = useState<API.PreCheckResult>({});
  const [failedList, setFailedList] = useState<API.PreCheckInfo[]>([]);
  const [showFailedList, setShowFailedList] = useState<API.PreCheckInfo[]>([]);
  const [hasAuto, setHasAuto] = useState(false);
  const [hasManual, setHasManual] = useState(false);
  const [onlyManual, setOnlyManual] = useState(false);
  const [checkFinished, setCheckFinished] = useState(false);
  const [isScroll, setIsScroll] = useState(false);
  const [isScrollFailed, setIsScrollFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkStatus, setCheckStatus] = useState(true);
  const [currentPage, setCurrentPage] = useState(true);
  const { run: precheckOcp, refresh } = useRequest(OCP.precheckOcp, {
    manual: true,
    onSuccess: (res: any) => {
      if (res?.success) {
        const { data } = res;
        let timer: NodeJS.Timer;
        setStatusData(formatOcpPreCheckStatusData(data) || {});
        if (data?.task_info?.status === 'RUNNING') {
          timer = setTimeout(() => {
            refresh();
          }, 2000);
        }
        if (
          data?.task_info?.result === 'FAILED' &&
          data?.precheck_result.find((item: any) => item.result === 'RUNNING')
        ) {
          const newFailedList =
            data?.precheck_result?.filter(
              (item: any) => item.result === 'FAILED',
            ) || [];
          setShowFailedList(newFailedList);
          setFailedList(newFailedList);
          let errorInfo: API.ErrorInfo = {
            title: intl.formatMessage({
              id: 'OBD.pages.components.PreCheckStatus.RequestError',
              defaultMessage: '请求错误',
            }),
            desc: data?.message,
          };
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
          setCheckStatus(false);
          setCheckFinished(true);
        } else {
          if (data.all_passed) {
            setFailedList([]);
            setShowFailedList([]);
          } else {
            const newFailedList =
              data?.precheck_result?.filter(
                (item: any) => item.result === 'FAILED',
              ) || [];
            newFailedList.forEach((item: any) => {
              if (item.recoverable) {
                setHasAuto(true);
              } else {
                setHasManual(true);
              }
            });
            setFailedList(newFailedList);
            setShowFailedList(newFailedList);
          }
          // const isFinished = !!data?.total && data?.finished === data?.total;
          const isFinished = data.task_info.status === 'FINISHED';
          setCheckFinished(isFinished);
          if (isFinished) {
            clearTimeout(timer);
          }
          if (!isScroll && !isFinished) {
            setTimeout(() => {
              const timelineContainer =
                document.getElementById('timeline-container');
              const runningItemDom = document.getElementById(
                'running-timeline-item',
              );
              if (timelineContainer) {
                timelineContainer.scrollTop = NP.minus(
                  NP.strip(runningItemDom?.offsetTop),
                  150,
                );
              }
            }, 10);
          }

          if (!isScrollFailed && !isFinished && failedList) {
            setTimeout(() => {
              const failedContainer =
                document.getElementById('failed-container');
              if (failedContainer) {
                failedContainer.scrollTop = NP.strip(
                  failedContainer?.scrollHeight,
                );
              }
            }, 10);
          }
          setCheckStatus(true);
        }
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 发起OCP的预检查
  const {
    run: precheckOcpDeployment,
    refresh: rePrecheckOcpDeployment,
    loading: preCheckLoading,
  } = useRequest(OCP.precheckOcpDeployment, {
    manual: true,
    onSuccess: (res: any) => {
      if (res.success) {
        precheckOcp({
          id: connectId,
          task_id: res.data?.id,
        });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const handelCheck = async () => {
    setLoading(true);
    try {
      if (connectId) {
        await precheckOcpDeployment({ id: connectId });
      }
    } catch {
      setLoading(false);
    }
  };

  const handleRetryCheck = (newConfigData?: any) => {
    setStatusData({});
    setFailedList([]);
    setShowFailedList([]);
    setCheckFinished(false);
    let params = { ...ocpConfigData };
    if (newConfigData) {
      params = { ...newConfigData };
    }
    precheckOcpDeployment({ id: connectId });
  };

  const { run: handleRecover, loading: recoverLoading } = useRequest(
    OCP.recoverOcpDeployment,
    {
      manual: true,
      onSuccess: async ({ success }) => {
        if (success) {
          message.success(
            intl.formatMessage({
              id: 'OBD.OCPPreCheck.PreCheck.AutomaticRepairSucceeded',
              defaultMessage: '自动修复成功',
            }),
          );
          try {
            rePrecheckOcpDeployment();
          } catch (e: any) {
            const errorInfo = getErrorInfo(e);
            setErrorVisible(true);
            setErrorsList([...errorsList, errorInfo]);
          }
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const prevStep = () => {
    setCheckOK(false);
    setCurrent(current - 1);
    setCurrentPage(false);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const { run: installOcp, loading: installLoading } = useRequest(
    OCP.installOcp,
    {
      manual: true,
      onSuccess: ({ data, success }) => {
        if (success) {
          setInstallTaskId(data?.id);
          setCurrent(5);
          setCurrent(current + 1);
          setCurrentPage(false);
          setErrorVisible(false);
          setErrorsList([]);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const handleInstall = async () => {
    installOcp({
      id: connectId,
    });
  };

  const handleAutoRepair = () => {
    setHasAuto(false);
    handleRecover({ id: connectId });
  };

  useEffect(() => {
    if (onlyManual) {
      const newShowFailedList = failedList.filter((item) => !item.recoverable);
      setShowFailedList(newShowFailedList);
    } else {
      setShowFailedList(failedList);
    }
  }, [onlyManual]);

  useEffect(() => {
    precheckOcpDeployment({ id: connectId });
  }, []);

  return (
    <PreCehckComponent
      checkFinished={checkFinished}
      checkStatus={checkStatus}
      errCodeLink={ERR_CODE}
      preCheckLoading={preCheckLoading}
      loading={loading}
      hasManual={hasManual}
      hasAuto={hasAuto}
      recoverLoading={recoverLoading}
      failedList={failedList}
      statusData={statusData}
      showFailedList={showFailedList}
      setIsScrollFailed={setIsScrollFailed}
      setIsScroll={setIsScroll}
      handelCheck={handelCheck}
      handleAutoRepair={handleAutoRepair}
      handleRetryCheck={handleRetryCheck}
      prevStep={prevStep}
      handleInstall={handleInstall}
      installLoading={installLoading}
      setOnlyManual={setOnlyManual}
    />
  );
}
