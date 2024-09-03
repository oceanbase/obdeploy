import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { Col } from 'antd';
import PasswordCard from '../PasswordCard';
import styles from './index.less';
import React from 'react';

interface UserCheckInfoProps {
  title: string | React.ReactNode;
  user: string;
  password?: string;
  className?: string
}

export default function UserCheckInfo({
  title,
  user,
  password,
  className
}: UserCheckInfoProps) {
  return (
    <ProCard
      title={title}
      className={`${className} card-padding-bottom-24`}
    >
      <Col span={12}>
        <ProCard className={styles.infoSubCard} split="vertical">
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.Username',
              defaultMessage: '用户名',
            })}
          >
            {user}
          </ProCard>
          {password ? <PasswordCard password={password} /> : null}
        </ProCard>
      </Col>
    </ProCard>
  );
}
