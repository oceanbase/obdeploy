/* eslint-disable react-hooks/rules-of-hooks */
import { useRequest } from '@umijs/max';
import type {
  CombineService,
  BaseOptions,
} from '@ahooksjs/use-request/lib/types';
import { handleResponseError } from '@/utils';
import { requestHandler } from '@/pages/Layout';
import { message } from 'antd';

interface Options<R = any, P extends any[] = any> extends BaseOptions<R, P> {
  skipRequestPipeline?: boolean;
}

export const requestPipeline = {
  data:[],
  processExit:false,
  push:(res:any)=>{
    /**
     * 获取连续服务端拒绝报错，所以当请求结果不是服务端拒绝连接时，清空 requestPipeline.data
     * 当后端服务挂掉时，经测试直接请求返回code:ERR_NETWORK 通过代理请求返回code:ERR_BAD_RESPONSE
     */
    if (res.code !== 'ERR_NETWORK' && res.code !== 'ERR_BAD_RESPONSE') {
      requestPipeline.data = []
      return;
    }
    requestPipeline.data.push(res)
  }
}

const errorHandle = (error: any, onError: any, skipRequestPipeline: boolean) => {
  const { response } = error;
  if (!skipRequestPipeline) {
    requestPipeline.push(error);
  }
  if (onError) {
    onError(skipRequestPipeline ? error : { ...error, errorPipeline: requestPipeline.data });
  }
  return response;
};

const successHandle = (onSuccess: () => void, res: any, arg: any, skipRequestPipeline: boolean) => {
  if (onSuccess) {
    onSuccess(res, ...arg);
  }
  if (!res.success) {
    handleResponseError(res.msg || res.data?.message);
  }
  if (!skipRequestPipeline) {
    requestPipeline.push(res)
  }
};

const request: any = <R, P extends any[]>(
  service: CombineService<R, P>,
  options?: Options<R, P>,
) => {
  const { skipRequestPipeline = false, ...requestOptions } = options || {};
  const response = useRequest(service, {
    manual: true,
    throwOnError: requestOptions.throwOnError || false,
    formatResult: (result: any) => result,
    ...requestOptions,
    onError: (error: any) => errorHandle(error, requestOptions.onError, skipRequestPipeline),
    onSuccess: (res, ...arg) => successHandle(requestOptions.onSuccess, res, arg, skipRequestPipeline),
  });
  return { ...response, data: response?.data?.data };
};

export default request;
