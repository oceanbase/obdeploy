import React from 'react';
import { Spin } from '@oceanbase/design';
import type { SpinProps } from 'antd/es/spin';

const PageLoading: React.FC<SpinProps> = props => (
  <div style={{ paddingTop: 100, textAlign: 'center' }}>
    <Spin size="large" {...props} />
  </div>
);

export default PageLoading;
