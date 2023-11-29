import React from 'react';
import { Affix } from '@oceanbase/design';
import type { AffixProps } from '@oceanbase/design';

import styles from './index.less';

export interface BatchOperationBarProps extends AffixProps {
  style?: React.CSSProperties;
}

const FooterToolbar: React.FC<BatchOperationBarProps> = ({ children, style, ...restProps }) => {
  return (
    <Affix
      {...restProps}
      style={{
        ...style,
      }}
    >
      <div className={styles.container}>{children}</div>
    </Affix>
  );
};

export default FooterToolbar;
