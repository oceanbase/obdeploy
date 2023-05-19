import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import { Modal, Progress, message } from 'antd';
import { getDestroyTaskInfo } from '@/services/ob-deploy-web/Deployments';
import useRequest from '@/utils/useRequest';
import { checkLowVersion, getErrorInfo } from '@/utils';
import NP from 'number-precision';
import { oceanbaseComponent } from '../constants';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface Props {
  visible: boolean;
  name: string;
  onCancel: () => void;
  setOBVersionValue: (value: string) => void;
}

let timerProgress: NodeJS.Timer;
let timerFetch: NodeJS.Timer;

const statusConfig = {
  RUNNING: 'normal',
  SUCCESSFUL: 'success',
  FAILED: 'exception',
};

export default function DeleteDeployModal({
  visible,
  name,
  onCancel,
  setOBVersionValue,
}: Props) {
  const {
    setConfigData,
    setIsDraft,
    setClusterMore,
    setComponentsMore,
    componentsVersionInfo,
    setComponentsVersionInfo,
    setCurrentType,
    getInfoByName,
    setLowVersion,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');

  const [status, setStatus] = useState('RUNNING');
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [isFinished, setIsFinished] = useState(false);

  const { run: fetchDestroyTaskInfo } = useRequest(getDestroyTaskInfo, {
    onSuccess: async ({ success, data }: API.OBResponseTaskInfo_) => {
      if (success) {
        if (data?.status !== 'RUNNING') {
          clearInterval(timerFetch);
        }
        clearInterval(timerProgress);
        if (data?.status === 'RUNNING') {
          const newProgress = NP.times(
            NP.divide(data?.finished, data?.total),
            100,
          );

          setProgress(newProgress);
          let step = NP.minus(newProgress, progress);
          let stepNum = 1;
          timerProgress = setInterval(() => {
            setShowProgress(
              NP.plus(progress, NP.times(NP.divide(step, 100), stepNum)),
            );

            stepNum += 1;
          }, 10);
        } else if (data?.status === 'SUCCESSFUL') {
          let step = NP.minus(100, progress);
          let stepNum = 1;
          timerProgress = setInterval(() => {
            setShowProgress(
              NP.plus(progress, NP.times(NP.divide(step, 100), stepNum)),
            );

            stepNum += 1;
          }, 10);
          try {
            const { success: nameSuccess, data: nameData } =
              await getInfoByName({ name });
            if (nameSuccess) {
              const { config } = nameData;
              const { components = {} } = config;
              setConfigData(config || {});
              setLowVersion(checkLowVersion(components?.oceanbase?.version));
              setClusterMore(!!components?.oceanbase?.parameters?.length);
              setComponentsMore(!!components?.obproxy?.parameters?.length);
              setIsDraft(true);
              setCurrentType(
                components?.oceanbase && !components?.obproxy ? 'ob' : 'all',
              );

              const newSelectedVersionInfo = componentsVersionInfo?.[
                oceanbaseComponent
              ]?.dataSource?.filter(
                (item: any) => item.md5 === components?.oceanbase?.package_hash,
              )[0];
              if (newSelectedVersionInfo) {
                setOBVersionValue(
                  `${components?.oceanbase?.version}-${components?.oceanbase?.release}-${components?.oceanbase?.package_hash}`,
                );

                setComponentsVersionInfo({
                  ...componentsVersionInfo,
                  [oceanbaseComponent]: {
                    ...componentsVersionInfo[oceanbaseComponent],
                    ...newSelectedVersionInfo,
                  },
                });
              }
              setTimeout(() => {
                onCancel();
              }, 2000);
            } else {
              setIsDraft(false);
              message.error(
                intl.formatMessage({
                  id: 'OBD.pages.components.DeleteDeployModal.FailedToObtainConfigurationInformation',
                  defaultMessage: '获取配置信息失败',
                }),
              );
              onCancel();
            }
          } catch (e: any) {
            const errorInfo = getErrorInfo(e);
            setErrorVisible(true);
            setErrorsList([...errorsList, errorInfo]);
          }
        } else {
          message.error(data?.msg);
          onCancel();
        }
        setStatus(data?.status);
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  useEffect(() => {
    fetchDestroyTaskInfo({ name });
    timerFetch = setInterval(() => {
      fetchDestroyTaskInfo({ name });
    }, 1000);
    return () => {
      clearInterval(timerProgress);
      clearInterval(timerFetch);
    };
  }, []);

  useEffect(() => {
    if (status !== 'RUNNING') {
      setTimeout(() => {
        clearInterval(timerProgress);
        setIsFinished(true);
      }, 1000);
    }
  }, [status]);

  return (
    <Modal
      open={visible}
      closable={false}
      maskClosable={false}
      footer={false}
      width={424}
    >
      <div className={styles.deleteDeployContent}>
        {isFinished ? (
          <>
            <div
              className={styles.deleteDeployText}
              style={{ marginBottom: '25px' }}
            >
              {status === 'SUCCESSFUL'
                ? intl.formatMessage({
                    id: 'OBD.pages.components.DeleteDeployModal.FailedHistoryDeploymentEnvironmentCleared',
                    defaultMessage: '清理失败历史部署环境成功',
                  })
                : intl.formatMessage({
                    id: 'OBD.pages.components.DeleteDeployModal.FailedToCleanUpThe',
                    defaultMessage: '清理失败历史部署环境失败',
                  })}
            </div>
            <Progress
              className={styles.deleteDeployProgress}
              type="circle"
              percent={100}
              width={48}
              status={statusConfig[status]}
            />
          </>
        ) : (
          <>
            <div className={styles.deleteDeployText}>
              {intl.formatMessage({
                id: 'OBD.pages.components.DeleteDeployModal.CleaningFailedHistoricalDeploymentEnvironments',
                defaultMessage: '正在清理失败的历史部署环境',
              })}

              <div>
                {intl.formatMessage({
                  id: 'OBD.pages.components.DeleteDeployModal.PleaseWaitPatiently',
                  defaultMessage: '请耐心等待',
                })}
              </div>
            </div>
            <Progress
              className={styles.deleteDeployProgress}
              type="circle"
              percent={showProgress}
              width={48}
            />
          </>
        )}
      </div>
    </Modal>
  );
}
