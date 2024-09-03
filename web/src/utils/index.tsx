import { intl } from '@/utils/intl';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { message, Modal, notification } from 'antd';
import type { FormInstance } from 'antd/lib/form';
import RandExp from 'randexp';
import { getLocale, history } from 'umi';
import { SPECIAL_SYMBOLS_OCP } from './helper';
import { PASSWORD_SUPPORT_CHARACTERS } from '@/constant';

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
export function isEnglish() {
  return getLocale() === 'en-US';
}

export function isZhCN() {
  return getLocale() === 'zh-CN';
}
export function validatePassword(passed) {
  return (rule, value, callback) => {
    if (value && !passed) {
      callback(
        intl.formatMessage({
          id: 'ocp-express.src.util.ThePasswordDoesNotMeet',
          defaultMessage: '密码设置不符合要求',
        }),
      );
    }
    callback();
  };
}
export const copyText = (text: string) => {
  // navigator.clipboard 并不存在，可能被依赖库改写了
  if (navigator.clipboard) {
    setTimeout(() => {
      navigator.clipboard.writeText(text);
    }, 100);
  } else {
    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    // 隐藏此输入框
    textarea.style.position = 'fixed';
    textarea.style.clip = 'rect(0 0 0 0)';
    textarea.style.top = '10px';
    // 赋值
    textarea.value = text;
    // 延迟一下复制操作，确保最终的值不会被其它操作覆盖剪贴板
    setTimeout(() => {
      // 选中
      textarea.select();
      // 复制
      document.execCommand('copy', true);
      // 移除输入框
      document.body.removeChild(textarea);
    }, 100);
  }
};
export const handleQuit = (
  handleQuitProgress: () => void,
  setCurrentStep: (step: number) => void,
  isFinshed?: boolean,
  finalStep?: number
) => {
  const quitRequest = async () => {
    await handleQuitProgress();
    setCurrentStep(finalStep ? finalStep : 7);
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

export const getErrorInfo = ({ response, data, type, errorPipeline }: any) => {
  if (errorPipeline?.length >= 5) {
    return {
      title: intl.formatMessage({
        id: 'OBD.src.utils.BackendProcessesMayExit',
        defaultMessage: '后端进程可能退出',
      }),
      desc: intl.formatMessage({
        id: 'OBD.src.utils.AfterExitingTheDeploymentWill',
        defaultMessage: '退出后，部署工作将被终止，请谨慎操作。',
      }),
      showModal: true,
    };
  }
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
  }
  if (!response) {
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
/**
 * 异常处理程序
 * response 为浏览器的 Response 对象，而 data 才是后端实际返回的响应数据
 */
export const errorHandler = ({ response, data }) => {
  const { status } = response || {};
  // 所有的 500 状态报错，报错信息结构一致
  if (status !== 500) {
    // message.error(statusCodeMessage[status], 3);
  } else if (status === 504) {
    // dispatch({
    //   type: 'global/update',
    //   payload: {
    //     installStatus: 'FINISHED',
    //     installResult: 'FAILED',
    //   },
    // });
    return;
  } else {
    const { detail } = data || {};
    // 错误展示一定要在 throw err 之前执行，否则抛错之后就无法展示了
    // 优先展示后端返回的错误信息，如果没有，则根据 status 进行展示
    const msg = detail;
    // || statusCodeMessage[status];
    // 有对应的错误信息才进行展示，避免遇到 204 等状态码(退出登录) 时，报一个空错误
    if (msg) {
      message.error(msg, 3);
    }
    // 403 状态为无权限情况，跳转到 403 页面
    if (status === 403) {
      history.push('/error/403');
    } else if (status === 404) {
      history.push('/error/404');
    }
    return data;
  }
};

//ip格式
export const serverReg =
  /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
// 数据库名仅支持英文、数字，长度不超过20个字符
// export const dbReg = /^[a-zA-Z0-9]{1,20}$/;
// 网站的地址：要求以http/https开始，包含VIP地址/域名/端口的网址，且结尾不含斜杠 /
export const siteReg =
  /^(http|https):\/\/([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+(:[0-9]+)?(?<!\/)$/;
//集群名格式：以英文字母开头、英文或数字结尾，可包含英文、数字和下划线，且长度为 2 ~ 32
export const clusterNameReg = /^[a-zA-Z][a-zA-Z0-9_]{0,30}[a-zA-Z0-9]$/;
export const updateClusterNameReg = /^[a-zA-Z][a-zA-Z0-9_-]{0,30}[a-zA-Z0-9]$/;
//用户格式：以英文字母开头，可包含英文、数字、下划线和连字符，且不超过32位
export const nameReg = /^[a-zA-Z][a-zA-Z0-9_-]{0,31}$/;

export const ocpServersValidator = (_: any, value: string[]) => {
  let validtor = true;
  if (value && value.length) {
    value.some((item) => {
      validtor = serverReg.test(item.trim());
      return !serverReg.test(item.trim());
    });
  }
  if (validtor) {
    return Promise.resolve();
  }
  return Promise.reject(
    new Error(
      intl.formatMessage({
        id: 'OBD.src.utils.SelectTheCorrectOcpNode',
        defaultMessage: '请选择正确的 OCP 节点',
      }),
    ),
  );
};

export const validateErrors = async (
  errorFileds: any[],
  form: FormInstance<any>,
  finalValidate: any,
  id: string,
) => {
  for (let filed of errorFileds) {
    if (
      filed.errors.length &&
      filed.name[1] === 'servers' &&
      filed.name[0] !== id
    ) {
      finalValidate.current = true;
      await form.validateFields([filed.name]);
      finalValidate.current = false;
    }
  }
};

export const serversValidator = (_: any, value: string[], type: string) => {
  let validtor = true;
  if (value && value.length) {
    value.some((item) => {
      validtor = serverReg.test(item.trim());
      return !serverReg.test(item.trim());
    });
  }
  if (validtor) {
    return Promise.resolve();
  }
  if (type === 'OBServer') {
    return Promise.reject(
      new Error(
        intl.formatMessage({
          id: 'OBD.pages.components.NodeConfig.EnterTheCorrectIpAddress',
          defaultMessage: '请输入正确的 IP 地址',
        }),
      ),
    );
  } else if (type === 'obconfigserver') {
    return Promise.reject(
      new Error(
        intl.formatMessage({
          id: 'OBD.src.utils.SelectTheCorrectObconfigserverNode',
          defaultMessage: '请选择正确的 obconfigserver 节点',
        }),
      ),
    );
  } else {
    return Promise.reject(
      new Error(
        intl.formatMessage({
          id: 'OBD.pages.components.NodeConfig.SelectTheCorrectObproxyNode',
          defaultMessage: '请选择正确的 OBProxy 节点',
        }),
      ),
    );
  }
};

export function generateRandomPassword() {
  const length = Math.floor(Math.random() * 25) + 8; // 生成8到32之间的随机长度
  const characters = `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789${SPECIAL_SYMBOLS_OCP}`; // 可用字符集合

  let password = '';
  let countUppercase = 0; // 大写字母计数器
  let countLowercase = 0; // 小写字母计数器
  let countNumber = 0; // 数字计数器
  let countSpecialChar = 0; // 特殊字符计数器

  // 生成随机密码
  for (let i = 0; i < length; i++) {
    const randomIndex = Math.floor(Math.random() * PASSWORD_SUPPORT_CHARACTERS.length);
    const randomChar = PASSWORD_SUPPORT_CHARACTERS[randomIndex];
    password += randomChar;

    // 判断字符类型并增加相应计数器
    if (/[A-Z]/.test(randomChar)) {
      countUppercase++;
    } else if (/[a-z]/.test(randomChar)) {
      countLowercase++;
    } else if (/[0-9]/.test(randomChar)) {
      countNumber++;
    } else {
      countSpecialChar++;
    }
  }

  // 检查计数器是否满足要求
  if (
    countUppercase < 2 ||
    countLowercase < 2 ||
    countNumber < 2 ||
    countSpecialChar < 2
  ) {
    return generateRandomPassword(); // 重新生成密码
  }

  return password;
}
