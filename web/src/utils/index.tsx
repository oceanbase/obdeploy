import { intl } from '@/utils/intl';
import { notification, Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import RandExp from 'randexp';

export const handleResponseError = (desc: any, msg?: string | undefined) => {
  notification.error({
    description: typeof desc === 'string' ? desc : JSON.stringify(desc),
    message:
      msg ||
      intl.formatMessage({
        id: 'OBD.src.utils.RequestError',
        defaultMessage: '请求错误',
      }),
    duration: null,
  });
};

export const handleQuit = (
  handleQuitProgress: () => void,
  setCurrentStep: (step: number) => void,
  isFinshed?: boolean,
) => {
  const quitRequest = async () => {
    await handleQuitProgress();
    setCurrentStep(7);
  };
  if (isFinshed) {
    quitRequest();
    return;
  }
  Modal.confirm({
    title: intl.formatMessage({
      id: 'OBD.src.utils.ExitTheDeploymentProgram',
      defaultMessage: '退出部署程序',
    }),
    content: intl.formatMessage({
      id: 'OBD.src.utils.AfterExitingTheDeploymentWill',
      defaultMessage: '退出后，部署工作将被终止，请谨慎操作。',
    }),
    okText: intl.formatMessage({
      id: 'OBD.src.utils.Exit',
      defaultMessage: '退出',
    }),
    cancelText: intl.formatMessage({
      id: 'OBD.src.utils.Cancel',
      defaultMessage: '取消',
    }),
    icon: <ExclamationCircleOutlined style={{ color: '#ff4b4b' }} />,
    okButtonProps: { type: 'primary', danger: true },
    onOk: () => {
      return new Promise<void>(async (resolve) => {
        try {
          await quitRequest();
          resolve();
        } catch {
          resolve();
        }
      });
    },
  });
};

export const checkLowVersion = (version: string) => {
  return Number(version.split('')[0]) < 4;
};

export const getErrorInfo = ({ response, data, type }: any) => {
  if (type === 'Timeout') {
    return {
      title: intl.formatMessage({
        id: 'OBD.src.utils.NetworkTimeout',
        defaultMessage: '网络超时',
      }),
      desc: intl.formatMessage({
        id: 'OBD.src.utils.YourNetworkIsAbnormalAnd',
        defaultMessage: '您的网络发生异常，无法连接服务器',
      }),
    };
  } else if (!response) {
    return {
      title: intl.formatMessage({
        id: 'OBD.src.utils.NetworkException',
        defaultMessage: '网络异常',
      }),
      desc: intl.formatMessage({
        id: 'OBD.src.utils.YourNetworkIsAbnormalAnd',
        defaultMessage: '您的网络发生异常，无法连接服务器',
      }),
    };
  }
  const desc = data?.msg || data?.detail || response?.statusText;
  return {
    title: intl.formatMessage({
      id: 'OBD.src.utils.RequestError',
      defaultMessage: '请求错误',
    }),
    desc: typeof desc === 'string' ? desc : JSON.stringify(desc),
  };
};

export const getRandomPassword = (isToken?: boolean) => {
  const randomPasswordReg = isToken
    ? /[A-Za-z\d]{32}/
    : /^(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*\d){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[A-Za-z\d~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32}$/;
  const newValue = new RandExp(randomPasswordReg).gen();
  if (randomPasswordReg.test(newValue)) {
    return newValue;
  }
  return getRandomPassword(isToken);
};
