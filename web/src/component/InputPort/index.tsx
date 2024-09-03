import { PORT_MAX, PORT_MIN } from '@/constant';
import { commonStyle } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { ProFormDigit } from '@ant-design/pro-components';
import { NamePath } from 'antd/es/form/interface';

interface InputPortProps {
  name: NamePath;
  label: React.ReactNode;
  fieldProps?: any;
  message?: string;
  limit?: boolean; //是否需要限制端口号范围
}

/**
 * default port range 1025~65535
 */
export default function InputPort({
  name,
  label,
  fieldProps,
  message,
  limit = true,
}: InputPortProps) {
  const rules: any = [
    {
      required: true,
      message:
        message ||
        intl.formatMessage({
          id: 'OBD.component.InputPort.PleaseEnter',
          defaultMessage: '请输入',
        }),
    },
  ];
  if (limit) {
    rules.push(() => ({
      validator(_: any, value: number) {
        if (value < PORT_MIN || value > PORT_MAX) {
          return Promise.reject(
            intl.formatMessage({
              id: 'OBD.component.InputPort.ThePortNumberCanOnly',
              defaultMessage: '端口号只支持 1025~65535 范围',
            }),
          );
        }
        return Promise.resolve();
      },
    }));
  }
  return (
    <ProFormDigit
      name={name}
      label={label}
      fieldProps={{ style: commonStyle, ...fieldProps }}
      placeholder={intl.formatMessage({
        id: 'OBD.component.InputPort.PleaseEnter',
        defaultMessage: '请输入',
      })}
      rules={rules}
    />
  );
}
