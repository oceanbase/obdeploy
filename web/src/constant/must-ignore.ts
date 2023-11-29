import { intl } from '@/utils/intl';
export const LOCALE_LIST = [
  {
    label: 'English',
    value: 'en-US',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.src.constant.must-ignore.SimplifiedChinese',
      defaultMessage: '简体中文',
    }),
    value: 'zh-CN',
  },
];

// μs 会被 must 视别为中文字符
export const MICROSECOND = 'μs';
export type MICROSECOND_TYPE = 'μs';
