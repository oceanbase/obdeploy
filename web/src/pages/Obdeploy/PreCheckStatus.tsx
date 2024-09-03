import {
  createDeploymentConfig,
  deployAndStartADeployment,
  preCheck,
  preCheckStatus,
  recover,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import { intl } from '@/utils/intl';
import { message } from 'antd';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';

import PreCehckComponent from '@/component/PreCheck/preCheck';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import useRequest from '@/utils/useRequest';
import NP from 'number-precision';
import { formatConfigData } from './CheckInfo';

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
    setCurrentStep,
    configData,
    setCheckOK,
    getInfoByName,
    setConfigData,
    setErrorVisible,
    setErrorsList,
    scenarioParam,
    errorsList,
    ERR_CODE,
  } = useModel('global');
  const oceanbase = configData?.components?.oceanbase;
  const name = configData?.components?.oceanbase?.appname;
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
  const [firstErrorTimestamp, setFirstErrorTimestamp] = useState<number>();



  const { run: fetchPreCheckStatus } = useRequest(preCheckStatus, {
    onSuccess: ({ success, data }: API.OBResponsePreCheckResult_) => {
      if (success) {
        let timer: NodeJS.Timer;
        setStatusData(formatDataSource(data) || {});
        if (data?.status === 'RUNNING') {
          timer = setTimeout(() => {
            fetchPreCheckStatus({ name });
          }, 1000);
        }
        if (data?.status === 'FAILED') {
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
        } else {
          if (data?.all_passed) {
            setFailedList([]);
            setShowFailedList([]);
          } else {
            const newFailedList =
              data?.info?.filter((item) => item.result === 'FAILED') || [];
            newFailedList.forEach((item) => {
              if (item.recoverable) {
                setHasAuto(true);
              } else {
                setHasManual(true);
              }
            });
            setFailedList(newFailedList);
            setShowFailedList(newFailedList);
          }
          const isFinished = !!data?.total && data?.finished === data?.total;
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

              timelineContainer.scrollTop = NP.minus(
                NP.strip(runningItemDom?.offsetTop),
                150,
              );
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
        if (loading) {
          setLoading(false);
        }
      }
    },
    onError: ({ response, data, type }: any) => {
      const handleError = () => {
        const errorInfo = getErrorInfo({ response, data, type });
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      };
      if (response?.status === 504 || (!response && type === 'TypeError')) {
        const nowTime = Date.now();
        if (!firstErrorTimestamp) {
          setFirstErrorTimestamp(nowTime);
        }
        if (NP.divide(nowTime - firstErrorTimestamp) > 60000) {
          handleError();
          setCheckStatus(false);
          if (loading) {
            setLoading(false);
          }
        } else {
          if (currentPage) {
            setTimeout(() => {
              fetchPreCheckStatus({ name });
            }, 1000);
          }
        }
      } else {
        handleError();
      }
    },
  });

  const { run: handlePreCheck, loading: preCheckLoading } = useRequest(
    preCheck,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          handleStartCheck();
        }
      },
      onError: (e: any) => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const { run: handleInstallConfirm, loading:installLoading } = useRequest(deployAndStartADeployment, {
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const handelCheck = async () => {
    setLoading(true);
    try {
      await handlePreCheck({ name });
    } catch {
      setLoading(false);
    }
  };

  const { run: handleCreateConfig, loading: createLoading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          handelCheck();
        }
        setLoading(false);
      },
      onError: (e: any) => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const handleRetryCheck = async(newConfigData?: any) => {
    setStatusData({});
    setFailedList([]);
    setShowFailedList([]);
    setCheckFinished(false);
    let params = { ...configData };
    if (newConfigData) {
      params = { ...newConfigData };
    }
    setLoading(true);
    const { data: publicKey } = await getPublicKey();
    handleCreateConfig(
      { name: oceanbase?.appname },
      formatConfigData(params, scenarioParam, publicKey),
    );
  };

  const { run: handleRecover, loading: recoverLoading } = useRequest(recover, {
    onSuccess: async ({
      success,
    }: API.OBResponseDataListRecoverChangeParameter_) => {
      if (success) {
        message.success(
          intl.formatMessage({
            id: 'OBD.pages.components.PreCheckStatus.AutomaticRepairSucceeded',
            defaultMessage: '自动修复成功',
          }),
        );
        try {
          const { success: nameSuccess, data: nameData } = await getInfoByName({
            name,
          });
          if (nameSuccess) {
            const { config } = nameData;
            //后端不会返回密码 需要从原配置中获取
            let newConfigData = config
              ? {
                  ...config,
                  auth: {
                    ...config?.auth,
                    password: configData.auth?.password,
                  },
                }
              : {};
            setConfigData(newConfigData);
            handleRetryCheck(newConfigData);
          } else {
            message.error(
              intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.FailedToObtainConfigurationInformation',
                defaultMessage: '获取配置信息失败',
              }),
            );
          }
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
  });

  const handleStartCheck = () => {
    fetchPreCheckStatus({ name });
  };

  const prevStep = () => {
    setCheckOK(false);
    setCurrentStep(3);
    setCurrentPage(false);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const handleInstall = async () => {
    const { success } = await handleInstallConfirm({ name });
    if (success) {
      setCurrentStep(5);
      setCurrentPage(false);
      setErrorVisible(false);
      setErrorsList([]);
    }
  };

  const handleAutoRepair = () => {
    setHasAuto(false);
    handleRecover({ name });
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
    handelCheck();
  }, []);
  return (
    <PreCehckComponent
      checkFinished={checkFinished}
      checkStatus={checkStatus}
      preCheckLoading={preCheckLoading}
      loading={loading}
      hasManual={hasManual}
      hasAuto={hasAuto}
      recoverLoading={recoverLoading}
      createLoading={createLoading}
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
    />
  );
}
