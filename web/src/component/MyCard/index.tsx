import React from 'react';
import { Card, Spin } from '@oceanbase/design';
import type { CardProps } from '@oceanbase/design/es/card';
import styles from './index.less';

export interface MyCardProps extends CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  extra?: React.ReactNode;
  loading?: boolean;
  className?: string;
  headStyle?: React.CSSProperties;
}

const MyCard = ({
  children,
  title,
  extra,
  loading = false,
  className,
  headStyle,
  bodyStyle,
  ...restProps
}: MyCardProps) => (
  <Card
    className={`${className} ${styles.card}`}
    bordered={false}
    divided={false}
    bodyStyle={{ padding: '20px 24px', ...bodyStyle }}
    {...restProps}
  >
    {(title || extra) && (
      <div className={styles.header} style={headStyle}>
        {title && <span className={styles.title}>{title}</span>}
        {extra && <span className={styles.extra}>{extra}</span>}
      </div>
    )}
    <div style={{ width: '100%' }}>
      <Spin spinning={loading}>{children}</Spin>
    </div>
  </Card>
);

export default MyCard;
