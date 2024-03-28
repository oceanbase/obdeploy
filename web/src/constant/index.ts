import moment from 'moment';
import { MICROSECOND } from '@/constant/must-ignore';
import { intl } from '@/utils/intl';

export const ALL = '__OCP_ALL_CONSTANT_VALUE__';

// 通配符
export const WILDCARD = '*';

// OB 官网链接
export const OB_SITE_LINK = 'https://www.oceanbase.com';


export const SMLL_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 12,
  },

  wrapperCol: {
    span: 12,
  },
};

export const FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 4,
  },

  wrapperCol: {
    span: 20,
  },
};

export const MODAL_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 24,
  },

  wrapperCol: {
    span: 18,
  },
};

export const DRAWER_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 24,
  },

  wrapperCol: {
    span: 12,
  },
};

export const MODAL_HORIZONTAL_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 6,
  },

  wrapperCol: {
    span: 18,
  },
};

export const NEST_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 3,
  },

  wrapperCol: {
    span: 21,
  },
};

export const FORM_ITEM_SMALL_LAYOUT = {
  labelCol: {
    span: 4,
  },

  wrapperCol: {
    span: 10,
  },
};

export const TAIL_FORM_ITEM_LAYOUT = {
  wrapperCol: {
    span: 20,
    offset: 4,
  },
};

export const MIDDLE_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 6,
  },

  wrapperCol: {
    span: 18,
  },
};

export const MIDDLE_TAIL_FORM_ITEM_LAYOUT = {
  wrapperCol: {
    span: 18,
    offset: 6,
  },
};

export const LARGE_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 8,
  },

  wrapperCol: {
    span: 16,
  },
};

export const MAX_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 24,
  },

  wrapperCol: {
    span: 24,
  },
};

export const LARGE_TAIL_FORM_ITEM_LAYOUT = {
  wrapperCol: {
    span: 16,
    offset: 8,
  },
};

export const SUPERSIZE_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 10,
  },

  wrapperCol: {
    span: 14,
  },
};

export const PAGE_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 4,
  },

  wrapperCol: {
    span: 12,
  },
};

export const PAGR_TAIL_FORM_ITEM_LAYOUT = {
  labelCol: {
    span: 0,
  },

  wrapperCol: {
    offset: 4,
    span: 12,
  },
};

export const DEFAULT_LIST_DATA = {
  page: {
    totalElements: 0,
    totalPages: 0,
    number: 0,
    size: 0,
  },

  contents: [],
};

export const PAGINATION_OPTION_10 = {
  defaultPageSize: 10,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50', '100'],
  // showTotal,
};

export const PAGINATION_OPTION_5 = {
  defaultPageSize: 5,
  showSizeChanger: true,
  pageSizeOptions: ['5', '10', '20', '50'],
  // showTotal,
};

export const EMAIL_DOMAIN_LIST = [
  'aliyun.com',
  '163.com',
  '126.com',
  'foxmail.com',
  'gmail.com',
  'outlook.com',
  'msn.com',
  'sohu.com',
  'sina.com',
  'hotmail.com',
  'qq.com',
];

export function getRanges() {
  const rangeList = [
    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.Minutes',
        defaultMessage: '1 分钟',
      }),
      value: () => [moment().subtract(1, 'minute'), moment()],
    },

    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.Minutes.1',
        defaultMessage: '5 分钟',
      }),
      value: () => [moment().subtract(5, 'minute'), moment()],
    },

    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.Minutes.2',
        defaultMessage: '10 分钟',
      }),
      value: () => [moment().subtract(10, 'minute'), moment()],
    },

    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.Minutes.3',
        defaultMessage: '20 分钟',
      }),
      value: () => [moment().subtract(20, 'minute'), moment()],
    },

    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.HalfAnHour',
        defaultMessage: '半小时',
      }),
      value: () => [moment().subtract(30, 'minute'), moment()],
    },

    {
      label: intl.formatMessage({
        id: 'ocp-express.src.constant.AnHour',
        defaultMessage: '一小时',
      }),
      value: () => [moment().subtract(60, 'minute'), moment()],
    },
  ];

  const ranges = {};
  rangeList.forEach((item) => {
    ranges[item.label] = (item.value && item.value()) || [];
  });
  return ranges;
}

// OCP 实时监控的刷新频率，单位为 s
export const FREQUENCY = 5;

export const TIME_UNIT_LIST = [MICROSECOND, 'ms', 's', 'min'];
export const SIZE_UNIT_LIST = ['byte', 'KB', 'MB', 'GB', 'TB', 'PB'];

// 提供给 Select 组件做分词使用，支持（逗号、空格、逗号 + 空格、换行符、逗号 + 换行符）等 5 种场景，因为 Select 组件默认支持换行符分隔，所以不显示定义 (换行符、逗号 + 换行符）
export const SELECT_TOKEN_SPEARATORS = [',', ', ', ' '];

export const OCP_UPGRADE_STATUS_LIST = [
  {
    label: intl.formatMessage({
      id: 'OBD.src.constant.Checking',
      defaultMessage: '检查中',
    }),

    value: 'RUNNING',
    badgeStatus: 'processing',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.src.constant.Pass',
      defaultMessage: '通过',
    }),

    value: 'PASSED',
    badgeStatus: 'success',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.src.constant.Failed',
      defaultMessage: '未通过',
    }),

    value: 'FAILED',
    badgeStatus: 'error',
  },
  {
    label: intl.formatMessage({
      id: 'OBD.src.constant.Ignored',
      defaultMessage: '已忽略',
    }),

    value: 'IGNORED',
    badgeStatus: 'ignored',
  },
];