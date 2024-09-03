import { PARAMETER_TYPE } from '@/constant/configuration';
import { changeUnit, isTakeUnit, takeNewUnit } from '@/constant/unit';
import { CONFIGSERVER_LOG_LEVEL } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { Input, InputNumber, Select, Space } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getLocale } from 'umi';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface ParameterProps {
  value?: API.ParameterValue;
  onChange?: (value?: API.ParameterValue) => void;
  onBlur?: () => void;
  defaultValue?: string;
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
  const { type, value } = parameterValue;

  if (
    type === PARAMETER_TYPE.numberLogogram ||
    type === PARAMETER_TYPE.number
  ) {
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
        onChange={(value) => {
          setParameterValue({
            ...parameterValue,
            value,
            isChanged: true,
          });
        }}
        value={parameterValue.value}
      />
    );
  }
  if (type === PARAMETER_TYPE.capacity || type === PARAMETER_TYPE.capacityMB) {
    return (
      <div style={{ width: 126 }}>
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
                value: String(value?.toFixed()) + unit,
                isChanged: true,
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
                      isChanged: true,
                    });
                  } else {
                    setParameterValue({
                      ...parameterValue,
                      value: takeNewUnit(parameterValue.value, value),
                      isChanged: true,
                    });
                  }
                }
              }}
              dropdownMatchSelectWidth={false}
              disabled={parameterValue?.adaptive || parameterValue?.unitDisable}
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

  if (type === PARAMETER_TYPE.boolean) {
    return (
      <Select
        defaultValue={parameterValue?.value || 'False'}
        // className={styles.paramterSelect}
        style={{ width: 126 }}
        onChange={(value) =>
          setParameterValue({
            ...parameterValue,
            value,
            isChanged: true,
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

  if (value && CONFIGSERVER_LOG_LEVEL.includes(value)) {
    return (
      <Select
        defaultValue={value}
        style={{ width: 126 }}
        onChange={(value) =>
          setParameterValue({
            ...parameterValue,
            value,
            isChanged: true,
          })
        }
        value={parameterValue.value}
        dropdownMatchSelectWidth={false}
        disabled={parameterValue?.adaptive}
        options={CONFIGSERVER_LOG_LEVEL.map((level) => ({
          value: level,
          label: level,
        }))}
      />
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
        setParameterValue({
          ...parameterValue,
          value: e.target.value,
          isChanged: true,
        })
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
    type === PARAMETER_TYPE.capacity || type === PARAMETER_TYPE.capacityMB
      ? changeUnit(parameterValue.value)
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
    <Space className={parameterValue?.auto && styles.paramContent} size={8}>
      <Select
        defaultValue={parameterValue?.adaptive}
        // className={styles.paramterSelect}
        onChange={(isAuto) => {
          if (isAuto) {
            setParameterValue({
              ...parameterValue,
              adaptive: isAuto,
              value: defaultValue,
              isChanged: true,
            });
            setUnit(defaultUnit.current);
          } else {
            setParameterValue({
              ...parameterValue,
              adaptive: isAuto,
              isChanged: true,
            });
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
