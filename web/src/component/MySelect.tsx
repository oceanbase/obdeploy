import { intl } from '@/utils/intl';
import React from 'react';
import { Select } from '@oceanbase/design';
import type { SelectProps } from 'antd/es/select';

const { Option, OptGroup } = Select;

const MySelect: React.FC<SelectProps<any>> = ({ children, ...restProps }) => (
  <Select
    placeholder={intl.formatMessage({
      id: 'OBD.src.component.MySelect.PleaseSelect',
      defaultMessage: '请选择',
    })}
    {...restProps}
  >
    {children}
  </Select>
);

MySelect.Option = Option;
MySelect.OptGroup = OptGroup;

export default MySelect;
