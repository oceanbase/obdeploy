/* eslint-disable react-hooks/rules-of-hooks */
import { useRequest } from 'umi';
import type {
  CombineService,
  BaseOptions,
} from '@ahooksjs/use-request/lib/types';
import { handleResponseError } from '@/utils';

interface Options<R = any, P extends any[] = any> extends BaseOptions<R, P> {
  skipStatusError?: boolean;
  skipTypeError?: boolean;
}

const errorHandle = (
  error: any,
  onError: any,
  skipStatusError?: boolean,
  skipTypeError?: boolean,
) => {
  const { response, data, type } = error;

  if (onError) {
    onError(error);
  }
  if (!skipStatusError) {
    if (response && response.status) {
      handleResponseError(data?.msg || data?.detail || response?.statusText);
    }
  }

  if (type === 'Timeout') {
    handleResponseError('您的网络发生异常，无法连接服务器', '网络超时');
  } else if (!response && !skipTypeError) {
    handleResponseError('您的网络发生异常，无法连接服务器', '网络异常');
  }

  return response;
};

const successHandle = (onSuccess: () => void, res: any, arg: any) => {
  if (onSuccess) {
    onSuccess(res, ...arg);
  }
  if (!res.success) {
    handleResponseError(res.msg || res.data?.message);
  }
};

const request: any = <R, P extends any[]>(
  service: CombineService<R, P>,
  options?: Options<R, P>,
) => {
  const response = useRequest(service, {
    manual: true,
    throwOnError: options?.throwOnError || false,
    formatResult: (result: any) => result,
    ...options,
    onError: (error: any) =>
      errorHandle(
        error,
        options?.onError,
        options?.skipStatusError,
        options?.skipTypeError,
      ),
    onSuccess: (res, ...arg) => successHandle(options?.onSuccess, res, arg),
  });
  return { ...response, data: response?.data?.data };
};

export default request;
