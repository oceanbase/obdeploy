import { getLocale } from 'umi';
import type { RequestConfig } from 'umi';

const locale = getLocale() || 'zh-CN';
export const request: RequestConfig = {
  errorConfig: {
    adaptor: (resData) => {
      return {
        ...resData,
        success: resData.success,
        showType: 0,
      };
    },
  },
  requestInterceptors: [
    (url, options) => {
      return {
        url: url,
        options: {
          ...options,
          timeout: 180000,
          errorHandler: (e) => {
            console.log('---------------------------------------------');
            console.log('error.name:', e.name);
            console.log('error.response:', e.response);
            console.log('error.request:', e.request);
            console.log('error.type:', e.type);
            console.log('=============================================');
            throw e;
          },
        },
      };
    },
  ],
  headers: {
    'Accept-Language': locale,
  },
};
