import { commonInputStyle, commonPortStyle } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { ProForm, ProFormDigit } from '@ant-design/pro-components';
import { Checkbox, Input, Tooltip } from 'antd';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import type { FormInstance } from 'antd/lib/form';
import { useModel } from 'umi';

import { nameReg } from '@/utils';
import styles from './index.less';

export default function UserConfig({ form }: { form: FormInstance<any> }) {
  const { useRunningUser, setUseRunningUser, setDeployUser } =
    useModel('ocpInstallData');
  const { DOCS_USER } = useModel('global');
  const onChange = (e: CheckboxChangeEvent) => {
    let { checked } = e.target;
    setUseRunningUser(checked);
    if (checked) {
      let launch_user = form.getFieldValue('launch_user');
      launch_user && setDeployUser(launch_user);
    } else {
      let user = form.getFieldValue(['auth', 'user']);
      user && setDeployUser(user);
    }
  };

  const userChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    setDeployUser(value);
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
        label={
          <span className={styles.labelText}>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.UserConfig.Username',
              defaultMessage: '用户名',
            })}
          </span>
        }
        style={commonInputStyle}
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
        <Input disabled={useRunningUser} onChange={userChange} />
      </ProForm.Item>
      <p className={styles.descText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.UserConfig.PleaseProvideTheHostUser',
          defaultMessage: '请提供主机用户名用以自动化配置平台专用操作系统用户',
        })}

        <a href={DOCS_USER} target="_blank" style={{ marginLeft: '4px' }}>
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.UserConfig.ViewHelpDocuments',
            defaultMessage: '查看帮助文档',
          })}
        </a>
      </p>
      <ProForm.Item
        name={['auth', 'password']}
        style={commonInputStyle}
        label={
          <span className={styles.labelText}>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.UserConfig.PasswordOptional',
              defaultMessage: '密码（可选）',
            })}
          </span>
        }
      >
        <Input.Password
          style={{ marginBottom: 21 }}
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
        label={
          <span className={styles.labelText}>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.UserConfig.SshPort',
              defaultMessage: 'SSH端口',
            })}
          </span>
        }
        fieldProps={{ style: commonPortStyle }}
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
        style={{ margin: '24px 0 24px 4px' }}
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
          style={commonInputStyle}
          label={
            <span className={styles.labelText}>
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
            </span>
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
            onChange={userChange}
            style={{ marginBottom: 24 }}
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
