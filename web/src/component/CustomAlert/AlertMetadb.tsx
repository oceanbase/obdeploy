import { intl } from '@/utils/intl';
import CustomAlert from '.';

export default function AlertMetadb() {
  return (
    <CustomAlert
      type="warning"
      showIcon={true}
      description={intl.formatMessage({
        id: 'OBD.component.CustomAlert.AlertMetadb.DoNotUseMetadbAs',
        defaultMessage: '请勿使用 MetaDB 作为业务集群使用',
      })}
      style={{
        marginBottom: 24,
        height: 40,
      }}
    />
  );
}
