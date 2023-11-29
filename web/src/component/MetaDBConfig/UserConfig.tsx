import { intl } from '@/utils/intl';
import { ProForm, ProFormDigit } from '@ant-design/pro-components';
import { Input, Checkbox, Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd/lib/form';
import { useModel } from 'umi';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';

import { commonStyle } from '@/pages/constants';
import { nameReg } from '@/utils';
import styles from './indexZh.less';
import { useState } from 'react';
import { getTailPath } from '@/utils/helper';
import { DOCS_USER } from '@/constant/docs';

type UserInfoType = {
  user?: string;
  password?: string;
  launch_user?: string;
};

export default function UserConfig({ form }: { form: FormInstance<any> }) {
  const { useRunningUser, setUseRunningUser, setUsername } =
    useModel('ocpInstallData');
  const { ocpConfigData = {} } = useModel('global');
  const { auth = {}, launch_user = '' } = ocpConfigData;
  const [userInfo, setUserInfo] = useState<UserInfoType>({
    ...auth,
    launch_user,
  });
  const isNewDB = getTailPath() === 'install';
  const onChange = (e: CheckboxChangeEvent) => {
    setUseRunningUser(e.target.checked);
    if (e.target.checked) {
      setUsername(form.getFieldValue('launch_user'));
    } else {
      if (form.getFieldValue('launch_user')) {
        form.setFieldValue('launch_user', undefined);
        setUserInfo({ ...userInfo, launch_user: undefined });
      }
      if (userInfo.user) {
        if (isNewDB) {
          form.setFieldValue(
            ['obproxy', 'home_path'],
            `/home/${userInfo.user}`,
          );
          form.setFieldValue(
            ['oceanbase', 'home_path'],
            `/home/${userInfo.user}`,
          );
        }
        form.setFieldValue(
          ['ocpserver', 'home_path'],
          `/home/${userInfo.user}`,
        );
        form.setFieldValue(
          ['ocpserver', 'log_dir'],
          `/home/${userInfo.user}/logs`,
        );
        form.setFieldValue(
          ['ocpserver', 'soft_dir'],
          `/home/${userInfo.user}/software`,
        );
      }
      setUsername(form.getFieldValue(['auth', 'user']));
    }
  };

  const passwordChange = (e: any) => {
    userInfo
      ? setUserInfo({ ...userInfo, password: e.target.value })
      : setUserInfo({ password: e.target.value });
    form.setFieldValue(['auth', 'password'], e.target.value);
  };
  const userChange = (e: any) => {
    userInfo
      ? setUserInfo({ ...userInfo, user: e.target.value })
      : setUserInfo({ user: e.target.value });
    form.setFieldValue(['auth', 'user'], e.target.value);
    if (!form.getFieldValue('launch_user')) {
      let value = '';
      if (e.target.value !== 'root') {
        value = `/home/${e.target.value}`;
      } else {
        value = `/${e.target.value}`;
      }
      if (isNewDB) {
        form.setFieldValue(['obproxy', 'home_path'], value);
        form.setFieldValue(['oceanbase', 'home_path'], value);
      }
      form.setFieldValue(['ocpserver', 'home_path'], value);
      form.setFieldValue(
        ['ocpserver', 'log_dir'],
        `/home/${e.target.value}/logs`,
      );
      form.setFieldValue(
        ['ocpserver', 'soft_dir'],
        `/home/${e.target.value}/software`,
      );
    }
    setUsername(e.target.value);
  };

  const launchUserChange = (e: any) => {
    userInfo
      ? setUserInfo({ ...userInfo, launch_user: e.target.value })
      : setUserInfo({ launch_user: e.target.value });
    form.setFieldValue('launch_user', e.target.value);
    if (isNewDB) {
      form.setFieldValue(['obproxy', 'home_path'], `/home/${e.target.value}`);
      form.setFieldValue(['oceanbase', 'home_path'], `/home/${e.target.value}`);
    }
    form.setFieldValue(['ocpserver', 'home_path'], `/home/${e.target.value}`);
    form.setFieldValue(
      ['ocpserver', 'log_dir'],
      `/home/${e.target.value}/logs`,
    );
    form.setFieldValue(
      ['ocpserver', 'soft_dir'],
      `/home/${e.target.value}/software`,
    );
    setUsername(e.target.value);
  };
  return (
    <div className={styles.userConfigContainer}>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.DeployUserConfiguration',
          defaultMessage: '部署用户配置',
        })}
      </p>
      <ProForm.Item
        name={['auth', 'user']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.Username',
          defaultMessage: '用户名',
        })}
        rules={
          !useRunningUser
            ? [
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.component.MetaDBConfig.UserConfig.EnterAUsername',
                    defaultMessage: '请输入用户名',
                  }),
                },
              ]
            : []
        }
      >
        <Input
          value={userInfo?.user}
          style={commonStyle}
          disabled={useRunningUser}
          onChange={userChange}
        />
      </ProForm.Item>
      <p className={styles.descText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.PleaseProvideTheHostUser',
          defaultMessage: '请提供主机用户名用以自动化配置平台专用操作系统用户',
        })}

        <a href={DOCS_USER} target="_blank" style={{ marginLeft: '8px' }}>
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.UserConfig.ViewHelpDocuments',
            defaultMessage: '查看帮助文档',
          })}
        </a>
      </p>
      <ProForm.Item
        name={['auth', 'password']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.PasswordOptional',
          defaultMessage: '密码（可选）',
        })}
      >
        <Input.Password
          value={userInfo?.password}
          onChange={passwordChange}
          style={{ width: 328, marginBottom: 21 }}
          autoComplete="new-password"
          disabled={useRunningUser}
          placeholder={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.UserConfig.IfYouHaveConfiguredPassword',
            defaultMessage: '如已配置免密登录，则无需再次输入密码',
          })}
        />
      </ProForm.Item>
      <ProFormDigit
        style={{ padding: 0 }}
        name={['auth', 'port']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.SshPort',
          defaultMessage: 'SSH端口',
        })}
        fieldProps={{ style: { width: 216 } }}
        placeholder={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.PleaseEnter',
          defaultMessage: '请输入',
        })}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.UserConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
      />

      <Checkbox
        style={{ margin: '16px 0 16px 4px' }}
        checked={useRunningUser}
        onChange={onChange}
      >
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.UseTheRunningUser',
          defaultMessage: '使用运行用户',
        })}
      </Checkbox>
      {useRunningUser && (
        <ProForm.Item
          name="launch_user"
          label={
            <>
              {intl.formatMessage({
                id: 'OBD.component.MetaDBConfig.UserConfig.RunningUsername',
                defaultMessage: '运行用户名',
              })}
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.component.MetaDBConfig.UserConfig.OperatingSystemUsersRunningOcp',
                  defaultMessage: '运行 OCP 服务的操作系统用户',
                })}
              >
                <QuestionCircleOutlined className="ml-10" />
              </Tooltip>
            </>
          }
          rules={
            useRunningUser
              ? [
                  {
                    required: true,
                    message: intl.formatMessage({
                      id: 'OBD.component.MetaDBConfig.UserConfig.EnterARunningUsername',
                      defaultMessage: '请输入运行用户名',
                    }),
                  },
                  {
                    pattern: nameReg,
                    message: intl.formatMessage({
                      id: 'OBD.component.MetaDBConfig.UserConfig.ItStartsWithALetter',
                      defaultMessage:
                        '以英文字母开头，可包含英文、数字、下划线和连字符，且不超过32位',
                    }),
                  },
                ]
              : []
          }
        >
          <Input
            value={userInfo?.launch_user}
            onChange={launchUserChange}
            style={{ width: 216 }}
            placeholder={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.UserConfig.PleaseEnter',
              defaultMessage: '请输入',
            })}
          />
        </ProForm.Item>
      )}
    </div>
  );
}
