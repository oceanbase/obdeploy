import type { SelectedCluster } from '@/models/componentDeploy';
import { intl } from '@/utils/intl';
import { Select } from 'antd';
import styles from './index.less';

interface SelectClusterProps {
  value?: SelectedCluster;
  onChange?: (val: string) => void;
  options?: API.DeployName[];
}

export default function SelectCluster({
  value,
  onChange,
  options,
}: SelectClusterProps) {
  return (
    <div className={styles.deployObjContent}>
      <div className={styles.clusterSelector}>
        <div>
          {intl.formatMessage({
            id: 'OBD.component.SelectCluster.Cluster',
            defaultMessage: '集群',
          })}
        </div>
        <Select
          placeholder={intl.formatMessage({
            id: 'OBD.component.SelectCluster.PleaseSelect',
            defaultMessage: '请选择',
          })}
          style={{ width: 328 }}
          value={value && options ? JSON.stringify(value) : ''}
          onChange={onChange}
          options={options?.map((cluster) => ({
            label: cluster.name,
            value: JSON.stringify(cluster),
          }))}
        />
      </div>
      <div className={styles.version}>
        <div>
          {intl.formatMessage({
            id: 'OBD.component.SelectCluster.OceanbaseVersionNumber',
            defaultMessage: 'OceanBase 版本号',
          })}
        </div>
        <span>{value?.ob_version || '-'}</span>
      </div>
      <div className={styles.createDate}>
        <div>
          {intl.formatMessage({
            id: 'OBD.component.SelectCluster.CreationDate',
            defaultMessage: '创建日期',
          })}
        </div>
        <span>{value?.create_date || '-'}</span>
      </div>
    </div>
  );
}
