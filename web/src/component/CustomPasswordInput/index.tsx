import {
  copyText,
  generateRandomPassword,
  OB_PASSWORD_ERROR_REASON,
  OCP_PASSWORD_ERROR_REASON,
  OCP_PASSWORD_ERROR_REASON_OLD,
  passwordCheck,
  passwordCheckLowVersion,
} from '@/utils/helper';
import { intl } from '@/utils/intl';
import { ProForm } from '@ant-design/pro-components';
import { Button, Input, message } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { NamePath } from 'rc-field-form/lib/interface';

interface CustomPasswordInputProps {
  onChange: (value: string) => void;
  value: string;
  label: React.ReactNode;
  name: NamePath | undefined;
  showCopyBtn?: boolean;
  form: FormInstance<any>;
  msgInfo: MsgInfoType;
  useOldRuler?: boolean;
  useFor: 'ob' | 'ocp';
  style?: React.CSSProperties;
  innerInputStyle?: React.CSSProperties;
  setMsgInfo: React.Dispatch<React.SetStateAction<MsgInfoType | undefined>>;
}

type MsgInfoType = {
  validateStatus: 'success' | 'error';
  errorMsg: string | null;
};

/**
 *
 * @param useOldRuler ocp版本<4.2.2用之前的密码校验规则
 * @returns
 */
export default function CustomPasswordInput({
  onChange,
  value,
  showCopyBtn = false,
  form,
  name,
  msgInfo,
  setMsgInfo,
  useOldRuler = false,
  useFor,
  innerInputStyle = { width: 328 },
  ...props
}: CustomPasswordInputProps) {
  const textStyle = { marginTop: '8px', marginBottom: '24px' };
  const oldValidateInput = (value: string): MsgInfoType => {
    if (!passwordCheckLowVersion(value)) {
      return {
        validateStatus: 'error',
        errorMsg: OCP_PASSWORD_ERROR_REASON_OLD,
      };
    }
    return {
      validateStatus: 'success',
      errorMsg: null,
    };
  };
  const newValidateInput = (value: string): MsgInfoType => {
    if (!passwordCheck(value, useFor)) {
      const REASON =
        useFor === 'ob' ? OB_PASSWORD_ERROR_REASON : OCP_PASSWORD_ERROR_REASON;
      return {
        validateStatus: 'error',
        errorMsg: REASON,
      };
    }
    return {
      validateStatus: 'success',
      errorMsg: null,
    };
  };
  const validateInput = useOldRuler ? oldValidateInput : newValidateInput;
  const handleChange = (value: string) => {
    setMsgInfo(validateInput(value));
    onChange(value);
  };

  const handleRandomGenerate = () => {
    const password = generateRandomPassword(useFor, useOldRuler);
    setMsgInfo(validateInput(password));
    onChange(password);
  };
  const passwordCopy = () => {
    if (value) {
      if (copyText(value)) {
        message.success(
          intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.CopiedSuccessfully',
            defaultMessage: '复制成功',
          }),
        );
      } else {
        message.warning(
          intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.TheCurrentBrowserDoesNot',
            defaultMessage: '当前浏览器不支持文本复制',
          }),
        );
      }
    }
  };
  const Help = () => {
    if (showCopyBtn) {
      return (
        <p style={textStyle}>
          {intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.KeepThePasswordInMind',
            defaultMessage: '请牢记密码，也可复制密码并妥善保存',
          })}
        </p>
      );
    }
    return (
      <p style={textStyle}>
        {intl.formatMessage({
          id: 'OBD.component.CustomPasswordInput.PleaseRememberThePasswordOr',
          defaultMessage: '请牢记密码，也可',
        })}{' '}
        <a onClick={() => passwordCopy()}>
          {intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.CopyPassword',
            defaultMessage: '复制密码',
          })}
        </a>{' '}
        {intl.formatMessage({
          id: 'OBD.component.CustomPasswordInput.AndKeepItProperly',
          defaultMessage: '并妥善保存',
        })}
      </p>
    );
  };

  return (
    <ProForm.Item
      validateStatus={msgInfo?.validateStatus}
      help={
        msgInfo?.errorMsg ? (
          <p style={textStyle}>{msgInfo?.errorMsg}</p>
        ) : (
          <Help />
        )
      }
      rules={[
        {
          required: true,
          message: intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.EnterAPassword',
            defaultMessage: '请输入密码',
          }),
        },
        {
          validator: (_, value) => {
            let validateRes = validateInput(value);
            if (validateRes.validateStatus === 'success') {
              return Promise.resolve();
            } else {
              return Promise.reject(new Error(validateRes.errorMsg!));
            }
          },
        },
      ]}
      name={name}
      {...props}
    >
      <div style={{ display: 'flex' }}>
        <Input.Password
          onChange={(e) => handleChange(e.target.value)}
          value={value}
          style={innerInputStyle}
        />

        <Button onClick={handleRandomGenerate} style={{ marginLeft: 12 }}>
          {intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.RandomlyGenerated',
            defaultMessage: '随机生成',
          })}
        </Button>
        {showCopyBtn && (
          <Button style={{ marginLeft: 12 }} onClick={passwordCopy}>
            {intl.formatMessage({
              id: 'OBD.component.CustomPasswordInput.CopyPassword',
              defaultMessage: '复制密码',
            })}
          </Button>
        )}
      </div>
    </ProForm.Item>
  );
}
