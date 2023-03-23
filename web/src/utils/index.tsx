import { notification } from 'antd';
import { Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

export const handleResponseError = (desc: any, msg?: string | undefined) => {
  notification.error({
    description: typeof desc === 'string' ? desc : JSON.stringify(desc),
    message: msg || '请求错误',
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
    title: '退出部署程序',
    content: '退出后，部署工作将被终止，请谨慎操作。',
    okText: '退出',
    cancelText: '取消',
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
