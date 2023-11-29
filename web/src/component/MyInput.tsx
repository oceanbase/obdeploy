import { intl } from '@/utils/intl';
import React from 'react';
import { Input } from '@oceanbase/design';
import type { InputProps } from 'antd/es/input';

interface MyInputProps extends React.FC<InputProps> {
  Search: typeof Input.Search;
  Password: typeof Input.Password;
  TextArea: typeof Input.TextArea;
}

const MyInput: MyInputProps = (props) => {
  return (
    <Input
      placeholder={intl.formatMessage({
        id: 'OBD.src.component.MyInput.PleaseEnter',
        defaultMessage: '请输入',
      })}
      {...props}
    />
  );
};

MyInput.Search = Input.Search;
MyInput.Password = Input.Password;
MyInput.TextArea = Input.TextArea;

export default MyInput;
