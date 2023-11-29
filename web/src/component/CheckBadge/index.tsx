import React from 'react';
import { Space } from '@oceanbase/design';
import {
  CloseCircleFilled,
  CheckCircleFilled,
  Loading3QuartersOutlined,
  MinusCircleFilled,
} from '@ant-design/icons';
import styles from './index.less';

export interface CheckBadgeProps {
  className?: string;
  status?: string; // 设置 Badge 为状态点
  text?: React.ReactNode;
}

const CheckBadge = ({ status, text, className, ...restProps }: CheckBadgeProps) => {
  const statusTextNode = !text ? <></> : <span className="status-text">{text}</span>;
  let statusIcon: React.ReactNode | undefined = undefined;
  if (status === 'processing') {
    statusIcon = <Loading3QuartersOutlined className={`${styles.rotate} ${styles.success}`} />;
  } else if (status === 'success') {
    statusIcon = <CheckCircleFilled className={styles.success} />;
  } else if (status === 'error') {
    statusIcon = <CloseCircleFilled className={styles.error} />;
  } else if (status === 'ignored') {
    statusIcon = <MinusCircleFilled className={styles.ignored} />;
  }
  return (
    <Space>
      {statusIcon}
      {statusTextNode}
    </Space>
  );
};

export default CheckBadge;
