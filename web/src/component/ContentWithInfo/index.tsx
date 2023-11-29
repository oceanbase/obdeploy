import React from 'react';
import type { SpaceProps } from '@oceanbase/design';
import { Space } from '@oceanbase/design';
import { InfoCircleFilled } from '@ant-design/icons';
import styles from './index.less';

export interface ContentWithInfoProps extends SpaceProps {
  content: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const ContentWithInfo: React.FC<ContentWithInfoProps> = ({ content, className, ...restProps }) => (
  <Space className={`${styles.container} ${className}`} {...restProps}>
    <InfoCircleFilled className={styles.icon} />
    <span className={styles.content}>{content}</span>
  </Space>
);

export default ContentWithInfo;
