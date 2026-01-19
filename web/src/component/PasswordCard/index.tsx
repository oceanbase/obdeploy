import { intl } from '@/utils/intl';
import { useState } from 'react';
import { ProCard } from '@ant-design/pro-components';
import { Tooltip } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';

import styles from './index.less';

export default function PasswordCard({ password }: { password: string }) {
  const [showPwd, setShowPwd] = useState<boolean>(false);
  return (
    <div
      title={intl.formatMessage({
        id: 'OBD.component.PasswordCard.Password',
        defaultMessage: '密码',
      })}
      className={styles.passwordCardContainer}

    >
      {password ? (
        <div style={{ position: 'relative' }}>
          {showPwd ? (
            <div>
              <Tooltip title={password} placement="topLeft">
                <div
                  className="ellipsis"
                  style={{ width: 'calc(100% - 20px)' }}
                >
                  {password}
                </div>
              </Tooltip>
              <EyeOutlined
                className={styles.pwdIcon}
                onClick={() => setShowPwd(false)}
              />
            </div>
          ) : (
            <div>
              {password.replace(/./g, '*')}
              <EyeInvisibleOutlined
                className={styles.pwdIcon}
                onClick={() => setShowPwd(true)}
              />
            </div>
          )}
        </div>
      ) : (
        '-'
      )}
    </div>
  );
}
