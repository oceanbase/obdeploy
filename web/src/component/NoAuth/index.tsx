import { intl } from '@/utils/intl';
import React from 'react';
import type { EmptyProps } from '@/component/Empty';
import Empty from '@/component/Empty';

type NoAuthProps = EmptyProps;

export default ({
  image = '/assets/common/no_auth.svg',
  title = intl.formatMessage({
    id: 'OBD.component.NoAuth.NoPermissionToView',
    defaultMessage: '暂无权限查看',
  }),
  description = intl.formatMessage({
    id: 'OBD.component.NoAuth.ContactTheAdministratorToActivate',
    defaultMessage: '请联系管理员开通权限',
  }),
  ...restProps
}: NoAuthProps) => (
  <Empty image={image} title={title} description={description} {...restProps} />
);
