import { intl } from '@/utils/intl';
import { ProForm } from '@ant-design/pro-components';
import { Input, Button, message } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { NamePath } from 'rc-field-form/lib/interface';
import { generateRandomPassword } from '@/utils';
import { copyText } from '@/utils/helper';

interface CustomPasswordInputProps {
  onChange: (value: string) => void;
  value: string;
  label: React.ReactNode;
  name: NamePath | undefined;
  showCopyBtn?: boolean;
  form: FormInstance<any>;
  msgInfo: MsgInfoType;
  setMsgInfo: React.Dispatch<React.SetStateAction<MsgInfoType | undefined>>;
}

type MsgInfoType = {
  validateStatus: 'success' | 'error';
  errorMsg: string | null;
};
const passwordReg =
  /^(?=.*[A-Z].*[A-Z])(?=.*[a-z].*[a-z])(?=.*\d.*\d)(?=.*[~!@#%^&*_\-+=`|(){}[\]:;',.?/].*[~!@#%^&*_\-+=`|(){}[\]:;',.?/])[A-Za-z\d~!@#%^&*_\-+=`|(){}[\]:;',.?/]{8,32}$/;
export default function CustomPasswordInput({
  onChange,
  value,
  showCopyBtn = false,
  form,
  name,
  msgInfo,
  setMsgInfo,
  ...props
}: CustomPasswordInputProps) {
  const textStyle = { marginTop: '8px' };
  const validateInput = (value: string): MsgInfoType => {
    const regex = /^[A-Za-z\d~!@#%^&*_\-+=`|(){}[\]:;',.?/]*$/;
    if (value.length < 8 || value.length > 32) {
      return {
        validateStatus: 'error',
        errorMsg: intl.formatMessage({
          id: 'OBD.component.CustomPasswordInput.TheLengthShouldBeTo',
          defaultMessage: '长度应为 8~32 个字符',
        }),
      };
    } else if (!regex.test(value)) {
      return {
        validateStatus: 'error',
        errorMsg: intl.formatMessage({
          id: 'OBD.component.CustomPasswordInput.CanOnlyContainLettersNumbers',
          defaultMessage:
            "只能包含字母、数字和特殊字符~!@#%^&*_-+=`|(){}[]:;',.?/",
        }),
      };
    } else if (!passwordReg.test(value)) {
      return {
        validateStatus: 'error',
        errorMsg: intl.formatMessage({
          id: 'OBD.component.CustomPasswordInput.AtLeastUppercaseAndLowercase',
          defaultMessage: '大小写字母、数字和特殊字符都至少包含 2 个',
        }),
      };
    }
    return {
      validateStatus: 'success',
      errorMsg: null,
    };
  };
  const handleChange = (value: string) => {
    setMsgInfo(validateInput(value));
    onChange(value);
  };

  const handleRandomGenerate = () => {
    const password = generateRandomPassword();
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
        })}

        <a onClick={() => passwordCopy()}>
          {intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.CopyPassword',
            defaultMessage: '复制密码',
          })}
        </a>
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
      ]}
      name={name}
      {...props}
    >
      <div style={{ display: 'flex' }}>
        <Input.Password
          onChange={(e) => handleChange(e.target.value)}
          value={value}
          style={{ width: 328 }}
        />

        <Button onClick={handleRandomGenerate} style={{ margin: '0 12px' }}>
          {intl.formatMessage({
            id: 'OBD.component.CustomPasswordInput.RandomlyGenerated',
            defaultMessage: '随机生成',
          })}
        </Button>
        {showCopyBtn && (
          <Button onClick={passwordCopy}>
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
