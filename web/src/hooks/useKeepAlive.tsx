import { validateOrSetKeepAliveToken } from '@/services/ob-deploy-web/Common';
import { getErrorInfo, getRandomPassword } from '@/utils';
import { intl } from '@/utils/intl';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Modal } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useModel } from '@umijs/max';

export interface UseKeepAliveOptions {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  /** step to navigate when another page takes over the session */
  progressQuitStep: number;
  /** when currentStep > threshold, send is_clear once */
  installPhaseStepThreshold: number;
  enabled?: boolean;
  onInit?: () => Promise<{ skipKeepAlive?: boolean } | void>;
}

export function useKeepAlive({
  currentStep,
  setCurrentStep,
  progressQuitStep,
  installPhaseStepThreshold,
  enabled = true,
  onInit,
}: UseKeepAliveOptions) {
  const uuid = window.localStorage.getItem('uuid');
  const {
    errorsList,
    setErrorVisible,
    setErrorsList,
    first,
    setFirst,
    token,
    setToken,
    aliveTokenTimer,
  } = useModel('global');
  const [isInstall, setIsInstall] = useState(false);
  const currentStepRef = useRef(currentStep);
  const tokenRef = useRef(token);
  const isInstallRef = useRef(isInstall);
  const keepAliveActiveRef = useRef(false);

  const stopKeepAlive = () => {
    keepAliveActiveRef.current = false;
    if (aliveTokenTimer.current) {
      clearTimeout(aliveTokenTimer.current);
      aliveTokenTimer.current = null;
    }
  };

  const scheduleKeepAlive = () => {
    if (requestPipeline.processExit || !keepAliveActiveRef.current) {
      return;
    }
    aliveTokenTimer.current = setTimeout(() => {
      if (!keepAliveActiveRef.current) {
        return;
      }
      handleValidateOrSetKeepAliveToken({ token: tokenRef.current });
    }, 1000);
  };

  useEffect(() => {
    currentStepRef.current = currentStep;
  }, [currentStep]);

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  useEffect(() => {
    isInstallRef.current = isInstall;
  }, [isInstall]);

  const { run: handleValidateOrSetKeepAliveToken } = useRequest(
    validateOrSetKeepAliveToken,
    {
      onSuccess: ({ success, data }: API.OBResponse) => {
        if (!keepAliveActiveRef.current) {
          return;
        }
        if (success) {
          const step = currentStepRef.current;
          if (!data) {
            if (first) {
              Modal.confirm({
                className: 'new-page-confirm',
                title: intl.formatMessage({
                  id: 'OBD.src.pages.ItIsDetectedThatYou',
                  defaultMessage:
                    '检测到您打开了一个新的部署流程页面，请确认是否使用新页面继续部署工作？',
                }),
                icon: <InfoCircleOutlined />,
                content: intl.formatMessage({
                  id: 'OBD.src.pages.UseTheNewPageTo',
                  defaultMessage:
                    '使用新的页面部署，原部署页面将无法再提交任何部署请求',
                }),
                onOk: () => {
                  handleValidateOrSetKeepAliveToken({
                    token: tokenRef.current,
                    overwrite: true,
                  });
                },
                onCancel: () => {
                  setCurrentStep(progressQuitStep);
                },
              });
              setTimeout(() => {
                (document.activeElement as HTMLElement | null)?.blur();
              }, 100);
            } else {
              setCurrentStep(progressQuitStep);
            }
          } else if (step > installPhaseStepThreshold) {
            if (!isInstallRef.current && !requestPipeline.processExit) {
              handleValidateOrSetKeepAliveToken({
                token: tokenRef.current,
                is_clear: true,
              });
              setIsInstall(true);
            }
          } else {
            scheduleKeepAlive();
          }
          setFirst(false);
        }
      },
      onError: (err: any) => {
        if (!keepAliveActiveRef.current) {
          return;
        }
        if (err?.errorPipeline?.length >= 5) {
          const errorInfo = getErrorInfo(err);
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
        }
        if (
          currentStepRef.current > installPhaseStepThreshold &&
          !requestPipeline.processExit
        ) {
          handleValidateOrSetKeepAliveToken({
            token: tokenRef.current,
            is_clear: true,
          });
        } else {
          scheduleKeepAlive();
        }
      },
    },
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }

    keepAliveActiveRef.current = true;

    const initKeepAlive = async () => {
      if (onInit) {
        const result = await onInit();
        if (result?.skipKeepAlive || !keepAliveActiveRef.current) {
          return;
        }
      }

      if (!keepAliveActiveRef.current) {
        return;
      }

      if (!token) {
        let newToken = '';
        if (uuid) {
          newToken = uuid;
        } else {
          newToken = `${Date.now()}${getRandomPassword(true)}`;
        }
        setToken(newToken);
        handleValidateOrSetKeepAliveToken({ token: newToken });
      } else {
        handleValidateOrSetKeepAliveToken({ token });
      }
      window.localStorage.setItem('uuid', '');
    };

    initKeepAlive();

    const sendBeacon = () => {
      const url =
        window.location.origin +
        '/api/v1/connect/keep_alive?token=' +
        tokenRef.current +
        '&is_clear=true';
      navigator.sendBeacon(url);
    };
    window.addEventListener('beforeunload', sendBeacon);
    return () => {
      stopKeepAlive();
      window.removeEventListener('beforeunload', sendBeacon);
    };
  }, [enabled]);

  return { handleValidateOrSetKeepAliveToken, stopKeepAlive };
}
