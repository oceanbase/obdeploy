import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { Space, Input, Select } from 'antd';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface Props {
  value?: API.ParameterValue;
  onChange?: (value?: API.ParameterValue) => void;
  onBlur?: () => void;
}

const optionConfig = [
  {
    label: intl.formatMessage({
      id: 'OBD.pages.components.Parameter.AutomaticAllocation',
      defaultMessage: '自动分配',
    }),
    value: true,
  },
  {
    label: intl.formatMessage({
      id: 'OBD.pages.components.Parameter.Custom',
      defaultMessage: '自定义',
    }),
    value: false,
  },
];

export default function Parameter({
  value: itemValue,
  onChange,
  onBlur,
}: Props) {
  const [parameterValue, setParameterValue] =
    useState<API.ParameterValue>(itemValue);

  useEffect(() => {
    if (onChange) {
      if (
        itemValue?.adaptive !== parameterValue?.adaptive ||
        itemValue?.value !== parameterValue?.value
      ) {
        onChange(parameterValue);
      }
    }
  }, [parameterValue]);
  return (
    <Space size={4}>
      <Select
        defaultValue={parameterValue?.adaptive}
        className={styles.paramterSelect}
        onChange={(value) =>
          setParameterValue({ ...parameterValue, adaptive: value })
        }
        disabled={!parameterValue?.auto}
        dropdownMatchSelectWidth={false}
        style={locale === 'zh-CN' ? { width: 100 } : { width: 180 }}
      >
        {optionConfig.map((option) => (
          <Select.Option value={option.value} key={`${option.value}`}>
            {option.label}
          </Select.Option>
        ))}
      </Select>
      <Input
        placeholder={intl.formatMessage({
          id: 'OBD.pages.components.Parameter.PleaseEnter',
          defaultMessage: '请输入',
        })}
        defaultValue={parameterValue?.value}
        className={styles.paramterInput}
        style={{ width: 86 }}
        disabled={parameterValue?.adaptive}
        onBlur={onBlur}
        onChange={(e) =>
          setParameterValue({ ...parameterValue, value: e.target.value })
        }
      />
    </Space>
  );
}
