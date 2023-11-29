import { intl, history } from 'umi';
import React from 'react';
import AobException from '@/component/AobException';

export default () => {
  return (
    <AobException
      title="404"
      desc={intl.formatMessage({
        id: 'OBD.OcpInstaller.Error.404.SorryThePageYouVisited',
        defaultMessage: '抱歉，你访问的页面不存在',
      })}
      img="/assets/common/404.svg"
      backText={intl.formatMessage({
        id: 'OBD.OcpInstaller.Error.404.ReturnToHomePage',
        defaultMessage: '返回首页',
      })}
      onBack={() => {
        history.push(`/`);
      }}
      style={{
        paddingTop: 50,
        height: '100%',
      }}
    />
  );
};
