import { errorHandler, getErrorInfo } from '@/utils';
import { intl } from '@/utils/intl';
import { message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useModel } from 'umi';
import PreCehckComponent from '@/component/PreCheck/preCheck';
import useRequest from '@/utils/useRequest';
import NP from 'number-precision';
import * as OCP from '@/services/ocp_installer_backend/OCP';
export const formatDataSource = (dataSource: API.PreCheckResult) => {
  dataSource.timelineData = dataSource.info?.map(
    (item: API.PreCheckInfo, index: number) => {
      return {
        isRunning:
          (dataSource?.info[index - 1]?.status === 'FINISHED' &&
            item.status === 'PENDING') ||
          (dataSource?.all_passed && index === dataSource?.info.length - 1),
        result: item.status === 'FINISHED' ? item.result : item.status,
      };
    },
  );
  return { ...dataSource };
};

export default function PreCheckStatus() {
  const {
    setCheckOK,
    setErrorVisible,
    setErrorsList,
    errorsList,
    configData,
    ERR_CODE,
    setCurrentStep
  } = useModel('global');
  const { setInstallTaskId, connectId } = useModel('ocpInstallData');

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
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const emptyResultRetryCountRef = useRef<number>(0);

  const formatOcpPreCheckStatusData = (
    dataSource: API.PrecheckTaskInfo,
  ) => {
    dataSource.finished =
      dataSource?.task_info?.info.filter(
        (item) => item.result === 'SUCCESSFUL' || item.result === 'FAILED',
      ).length || 0;
    dataSource.total = dataSource?.precheck_result?.length || 0;
    dataSource.all_passed = dataSource.task_info.result === 'SUCCESSFUL';

    dataSource.timelineData = dataSource.task_info.info.map((item) => {
      let result = {};
      result.isRunning = item?.result === 'RUNNING';
      result.result = item?.result;
      return result;
    });
    return { ...dataSource };
  };

  const { run: preCheckOms, refresh, loading: preCheckOmsLoading } = useRequest(OCP.preCheckOms, {
    manual: true,
    onSuccess: (res: any) => {
      if (res?.success) {
        const { data } = res;

        setStatusData(formatOcpPreCheckStatusData(data) || {});

        // 如果 precheck_result 为空数组，重新执行检查
        const isEmptyResult = !data?.precheck_result || data?.precheck_result?.length === 0;
        const isRunning = data?.task_info?.status === 'RUNNING';
        const isFinished = data?.task_info?.status === 'FINISHED';

        // 清理之前的 timer
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }

        // 如果结果不为空数组，重置重试计数器
        if (!isEmptyResult) {
          emptyResultRetryCountRef.current = 0;
        }

        // 如果任务还在运行中，则继续轮询
        // 如果结果为空数组（无论任务状态如何），且重试次数未超过限制，则重新执行
        const MAX_EMPTY_RESULT_RETRY = 5;
        const shouldRetryEmptyResult = isEmptyResult && emptyResultRetryCountRef.current < MAX_EMPTY_RESULT_RETRY;

        if (isRunning || shouldRetryEmptyResult) {
          if (shouldRetryEmptyResult) {
            emptyResultRetryCountRef.current += 1;
          }
          timerRef.current = setTimeout(() => {
            refresh();
          }, 2000);
        }
        if (
          data?.task_info?.result === 'FAILED' &&
          data?.precheck_result?.find((item: any) => item.result === 'RUNNING')
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

          const isFinished = data.task_info.status === 'FINISHED';
          setCheckFinished(isFinished);
          // 只有当结果不为空且任务已完成时，才清理 timer
          // 如果结果为空数组，即使任务已完成，也应该继续重试
          const isEmptyResult = !data?.precheck_result || data?.precheck_result?.length === 0;
          if (isFinished && !isEmptyResult) {
            if (timerRef.current) {
              clearTimeout(timerRef.current);
              timerRef.current = null;
            }
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

  // 发起OMS的预检查
  const {
    run: preCheckOmsDeployment,
    refresh: repreCheckOmsDeployment,
    loading: preCheckLoading,
  } = useRequest(OCP.preCheckOmsDeployment, {
    manual: true,
    onSuccess: (res: any) => {
      if (res.success) {
        preCheckOms({
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
        await preCheckOmsDeployment({ id: connectId });
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
    // 重置空结果重试计数器
    emptyResultRetryCountRef.current = 0;
    // 清理之前的 timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    let params = { ...configData };
    if (newConfigData) {
      params = { ...newConfigData };
    }
    preCheckOmsDeployment({ id: connectId });
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
            repreCheckOmsDeployment();
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
    setCurrentStep(3);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const { run: installOms, loading: installLoading } = useRequest(
    OCP.installOms,
    {
      manual: true,
      onSuccess: ({ data, success }) => {
        if (success) {
          setInstallTaskId(data?.id);
          setCurrentStep(5);
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
    installOms({
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
    if (connectId) {
      preCheckOmsDeployment({ id: connectId });
    } else {
      // 如果connectId为空，直接设置为检查完成状态
      setCheckFinished(true);
      setCheckStatus(true);
    }
  }, []);

  // 组件卸载时清理 timer
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);
  return (
    <PreCehckComponent
      checkFinished={checkFinished}
      checkStatus={checkStatus}
      preCheckLoading={preCheckLoading}
      preCheckOmsLoading={preCheckOmsLoading}
      loading={loading}
      hasManual={hasManual}
      hasAuto={hasAuto}
      recoverLoading={recoverLoading}
      failedList={failedList}
      statusData={statusData}
      errCodeLink={ERR_CODE}
      showFailedList={showFailedList}
      setIsScrollFailed={setIsScrollFailed}
      setIsScroll={setIsScroll}
      handelCheck={handelCheck}
      handleAutoRepair={handleAutoRepair}
      handleRetryCheck={handleRetryCheck}
      prevStep={prevStep}
      handleInstall={handleInstall}
      setOnlyManual={setOnlyManual}
      installLoading={installLoading}
      type='OMS'
    />
  );
}
