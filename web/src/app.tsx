import type { RequestConfig } from '@umijs/max';
import { getLocale } from '@umijs/max';

export const request: RequestConfig = {
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
  responseInterceptors: [
    (response) => {
      const { data } = response;
      if (!data.success) {
        return {
          ...response,
          success: response.success,
          showType: 0,
        };
      }
      return response;
    },
  ],
};
export const rootContainer = (element: JSX.Element) => {
  const locale = getLocale() || 'zh-CN';
  request.headers = {
    'Accept-Language': locale,
  };
  return <>{element}</>;
};
