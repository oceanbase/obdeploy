import { intl } from '@/utils/intl';
import { useEffect, useRef, useState } from 'react';
import { Space, InputNumber, Input, Select } from 'antd';
import { getLocale } from 'umi';
import { getUnit, isTakeUnit, takeNewUnit } from './helper';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface ParameterProps {
  value?: API.ParameterValue;
  onChange?: (value?: API.ParameterValue) => void;
  onBlur?: () => void;
  defaultValue?:string
}

interface AdaptiveInputProps {
  parameterValue: API.ParameterValue;
  onBlur?: () => void;
  setParameterValue: (prop: API.ParameterValue) => void;
  unit: string;
  setUnit: React.Dispatch<React.SetStateAction<string>>;
}

type OptionsType = {
  label: string;
  value: string | Boolean;
}[];

const optionConfig: OptionsType = [
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

const unitOption: OptionsType = [
  {
    label: 'KB',
    value: 'KB',
  },
  {
    label: 'MB',
    value: 'MB',
  },
  {
    label: 'GB',
    value: 'GB',
  },
];

const booleanOption: OptionsType = [
  {
    label: 'True',
    value: 'True',
  },
  {
    label: 'False',
    value: 'False',
  },
];

const AdaptiveInput = ({
  parameterValue,
  onBlur,
  setParameterValue,
  unit,
  setUnit,
}: AdaptiveInputProps) => {
  const { type } = parameterValue;
  if (type === 'int' || type === 'Integer') {
    return (
      <InputNumber
        placeholder={intl.formatMessage({
          id: 'OBD.pages.components.Parameter.PleaseEnter',
          defaultMessage: '请输入',
        })}
        defaultValue={parameterValue?.value}
        className={styles.paramterInput}
        min="0"
        disabled={parameterValue?.adaptive}
        onBlur={onBlur}
        onChange={(value) =>
          value !== null && setParameterValue({ ...parameterValue, value })
        }
        value={parameterValue.value}
      />
    );
  }
  if (type === 'CapacityMB' || type === 'Capacity') {
    return (
      <div style={{ maxWidth: 126 }}>
        <InputNumber
          placeholder={intl.formatMessage({
            id: 'OBD.pages.components.Parameter.PleaseEnter',
            defaultMessage: '请输入',
          })}
          defaultValue={
            parameterValue?.value?.match(/\d+/g)?.[0] || parameterValue?.value
          }
          min="0"
          disabled={parameterValue?.adaptive}
          onBlur={onBlur}
          value={
            parameterValue?.value?.match(/\d+/g)?.[0] || parameterValue?.value
          }
          onChange={(value) => {
            if (value !== null) {
              setParameterValue({
                ...parameterValue,
                value: String(value) + unit,
              });
            }
          }}
          addonAfter={
            <Select
              value={unit}
              onChange={(value) => {
                setUnit(value);
                if (parameterValue.value) {
                  if (!isTakeUnit(parameterValue.value)) {
                    setParameterValue({
                      ...parameterValue,
                      value: `${parameterValue.value}${value}`,
                    });
                  } else {
                    setParameterValue({
                      ...parameterValue,
                      value: takeNewUnit(parameterValue.value, value),
                    });
                  }
                }
              }}
              dropdownMatchSelectWidth={false}
              disabled={parameterValue?.adaptive}
              style={{ width: 65 }}
            >
              {unitOption.map((option) => (
                <Select.Option value={option.value} key={`${option.value}`}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          }
        />
      </div>
    );
  }

  if (type === 'Boolean') {
    return (
      <Select
        defaultValue={parameterValue?.value || 'False'}
        // className={styles.paramterSelect}
        style={{ width: 126 }}
        onChange={(value) =>
          setParameterValue({
            ...parameterValue,
            value,
          })
        }
        value={parameterValue.value}
        dropdownMatchSelectWidth={false}
        disabled={parameterValue?.adaptive}
      >
        {booleanOption.map((option) => (
          <Select.Option value={option.value} key={`${option.value}`}>
            {option.label}
          </Select.Option>
        ))}
      </Select>
    );
  }

  return (
    <Input
      placeholder={intl.formatMessage({
        id: 'OBD.pages.components.Parameter.PleaseEnter',
        defaultMessage: '请输入',
      })}
      value={parameterValue.value}
      defaultValue={parameterValue?.value}
      className={styles.paramterInput}
      disabled={parameterValue?.adaptive}
      onBlur={onBlur}
      onChange={(e) =>
        setParameterValue({ ...parameterValue, value: e.target.value })
      }
    />
  );
};
//参数来由：当Parameter在form.item下时自带有onchange，value
export default function Parameter({
  value: itemValue,
  onChange,
  onBlur,
  defaultValue,
}: ParameterProps) {
  const [parameterValue, setParameterValue] = useState<API.ParameterValue>(
    itemValue || {},
  );
  const { type } = parameterValue;
  const defaultUnit = useRef<string>(
    type === 'CapacityMB' || type === 'Capacity'
      ? getUnit(parameterValue.value)
      : null,
  );
  const [unit, setUnit] = useState<string>(defaultUnit.current);
  useEffect(() => {
    if (onChange) {
      if (
        itemValue?.adaptive !== parameterValue?.adaptive ||
        itemValue?.value !== parameterValue?.value ||
        itemValue?.type !== parameterValue?.type
      ) {
        onChange(parameterValue);
      }
    }
  }, [parameterValue]);
  return (
    <Space size={4}>
      <Select
        defaultValue={parameterValue?.adaptive}
        // className={styles.paramterSelect}
        onChange={(isAuto) => {
          if (isAuto) {
            setParameterValue({
              ...parameterValue,
              adaptive: isAuto,
              value: defaultValue,
            });
            setUnit(defaultUnit.current);
          } else {
            setParameterValue({ ...parameterValue, adaptive: isAuto });
          }
        }}
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
      <AdaptiveInput
        parameterValue={parameterValue}
        onBlur={onBlur}
        setParameterValue={setParameterValue}
        unit={unit}
        setUnit={setUnit}
      />
    </Space>
  );
}
