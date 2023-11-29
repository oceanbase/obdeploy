import React from 'react';
import { Card, Spin } from '@oceanbase/design';
import styles from './index.less';

export interface TaskSuccessProps {
  children: React.ReactNode;
  loading?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

const PageCard: React.FC<TaskSuccessProps> = ({
  children,
  loading = false,
  className,
  ...restProps
}) => (
  <Card bordered={false} divided={false} className={`${styles.card} ${className}`} {...restProps}>
    <Spin spinning={loading}>{children}</Spin>
  </Card>
);

export default PageCard;
