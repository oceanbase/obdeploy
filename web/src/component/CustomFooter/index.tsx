import React from 'react';
import { Space } from 'antd';
import styles from './index.less';

export default function CustomFooter(
  props: React.PropsWithChildren<any>,
) {
  return (
    <footer className={styles.pageFooterContainer}>
      <div className={styles.pageFooter}>
        <Space className={styles.foolterAction}>{props.children}</Space>
      </div>
    </footer>
  );
}
