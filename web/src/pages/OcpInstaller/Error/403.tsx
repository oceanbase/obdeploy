import { history } from 'umi';
import { intl } from '@/utils/intl';
import React from 'react';
import AobException from '@/component/AobException';

export default () => {
  return (
    <AobException
      title="403"
      desc={intl.formatMessage({
        id: 'OBD.OcpInstaller.Error.403.SorryYouAreNotAuthorized',
        defaultMessage: '抱歉，你无权访问此页面',
      })}
      img="/assets/common/403.svg"
      backText={intl.formatMessage({
        id: 'OBD.OcpInstaller.Error.403.ReturnToHomePage',
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
