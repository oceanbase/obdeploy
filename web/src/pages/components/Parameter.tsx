import { useEffect, useState } from 'react';
import { Space, Input, Select } from 'antd';
import styles from './index.less';

interface Props {
  value?: API.ParameterValue;
  onChange?: (value?: API.ParameterValue) => void;
  onBlur?: () => void;
}

const optionConfig = [
  { label: '自动分配', value: true },
  { label: '自定义', value: false },
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
      >
        {optionConfig.map((option) => (
          <Select.Option value={option.value} key={`${option.value}`}>
            {option.label}
          </Select.Option>
        ))}
      </Select>
      <Input
        placeholder="请输入"
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
