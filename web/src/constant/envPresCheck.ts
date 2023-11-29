export const ERROR_CODE_LIST = [
  {
    value: '1000',
    label: 'Configuration conflict x.x.x.x: xxx port is used for x.x.x.x',
  },
  {
    value: '1001',
    label: 'x.x.x.x:xxx port is already used',
  },
  {
    value: '1002',
    label: 'Fail to init x.x.x.x path',
  },
  {
    value: '1003',
    label: 'fail to clean x.x.x.x:xxx',
  },
  {
    value: '1004',
    label: 'Configuration conflict x.x.x.x: xxx is used for x.x.x.x',
  },
  {
    value: '1005',
    label: 'Some of the servers in the cluster have been stopped',
  },
  {
    value: '1006',
    label: 'Failed to connect to xxx',
  },
  {
    value: '1007',
    label: '(x.x.x.x) xxx must not be less than xxx (Current value: xxx)',
  },
  {
    value: '1008',
    label: '(x.x.x.x) failed to get fs.aio-max-nr and fs.aio-nr',
  },
  {
    value: '1009',
    label: 'x.x.x.x xxx need config: xxx',
  },
  {
    value: '1010',
    label: 'x.x.x.x No such net interface: xxx',
  },
  {
    value: '1011',
    label:
      '(x.x.x.x) Insufficient AIO remaining (Avail: xxx, Need: xxx), The recommended value of fs.aio-max-nr is 1048576',
  },
  {
    value: '1012',
    label: 'xxx',
  },
  {
    value: '1013',
    label: 'xxx@x.x.x.x connect failed: xxx',
  },
  {
    value: '2000',
    label: 'x.x.x.x not enough memory',
  },
  {
    value: '2001',
    label: 'server can not migrate in',
  },
  {
    value: '2002',
    label: 'failed to start x.x.x.x observer',
  },
  {
    value: '2003',
    label:
      'not enough disk space for clog. Use redo_dir to set other disk for clog, or reduce the value of datafile_size',
  },
  {
    value: '2004',
    label: 'Invalid: xxx is not a single server configuration item',
  },
  {
    value: '2005',
    label: 'Failed to register cluster. xxx may have been registered in xxx',
  },
  {
    value: '2006',
    label: 'x.x.x.x has more than one network interface. Please set devname for x.x.x.x',
  },
  {
    value: '2007',
    label: 'x.x.x.x xxx fail to ping x.x.x.x. Please check configuration devname',
  },
  {
    value: '2008',
    label: 'Cluster clocks are out of sync',
  },
  {
    value: '2009',
    label: 'x.x.x.x: when production_mode is True, xxx can not be less then xxx',
  },
  {
    value: '2010',
    label:
      'x.x.x.x: system_memory too large. system_memory must be less than memory_limit/memory_limit_percentage',
  },
  {
    value: '2011',
    label:
      "x.x.x.x: fail to get memory info.\nPlease configure 'memory_limit' manually in configuration file",
  },
  {
    value: '3000',
    label: 'parse cmd failed',
  },
  {
    value: '3001',
    label: 'xxx.sql not found',
  },
  {
    value: '3002',
    label: 'Failed to load data',
  },
  {
    value: '3003',
    label: 'Failed to run TPC-C benchmark',
  },
  {
    value: '4000',
    label: 'Fail to reload x.x.x.x',
  },
  {
    value: '4001',
    label: 'Fail to send config file to x.x.x.x',
  },
  {
    value: '4100',
    label: 'x.x.x.x need config "rs_list" or "obproxy_config_server_url"',
  },
  {
    value: '4101',
    label: 'failed to start x.x.x.x obproxy: xxx',
  },
  {
    value: '4200',
    label: "x.x.x.x grafana admin password should not be 'admin'",
  },
  {
    value: '4201',
    label: 'x.x.x.x grafana admin password length should not be less than 5',
  },
  {
    value: '4300',
    label: 'x.x.x.x: failed to query java version, you may not have java installed',
  },
  {
    value: '4301',
    label: 'x.x.x.x: ocp-express need java with version xxx',
  },
  {
    value: '4302',
    label: 'x.x.x.x not enough memory. (Free: xxx, Need: xxx)',
  },
  {
    value: '4303',
    label: 'x.x.x.x xxx not enough disk space. (Avail: xxx, Need: xxx)',
  },
  {
    value: '4304',
    label: 'OCP express xxx needs to use xxx with version xxx or above',
  },
  {
    value: '4305',
    label: 'There is not enough xxx for ocp meta tenant',
  },
];
