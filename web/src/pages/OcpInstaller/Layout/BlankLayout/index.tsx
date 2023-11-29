import React from 'react';
import { Layout } from '@oceanbase/design';
import styles from './index.less';

const BlankLayout: React.FC = ({ children, ...restProps }) => (
  <div className={styles.main} {...restProps}>
    <Layout className={styles.layout}>{children}</Layout>
  </div>
);

export default BlankLayout;
