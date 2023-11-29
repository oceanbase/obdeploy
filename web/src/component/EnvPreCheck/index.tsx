import { intl } from '@/utils/intl';
import React, { useEffect } from 'react';
import { Card, Row, Col } from '@oceanbase/design';
import { useRequest } from 'ahooks';
import { errorHandler } from '@/utils';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import CheckItem from './CheckItem';
import CheckFailuredItem from './CheckFailuredItem';
import ContentWithQuestion from '../ContentWithQuestion';
import styles from './index.less';

export interface EnvPreCheckProps {
  id?: number;
  installType?: string;
}

const EnvPreCheck: React.FC<EnvPreCheckProps> = ({ id, installType }) => {
  // const dispatch = useDispatch();
  let precheckStatus, precheckMetadbResult;

  // const { precheckStatus, precheckMetadbResult } = useSelector(
  //   (state: DefaultRootState) => state.global
  // );

  // 发起MetaDb的预检查
  const {
    run: precheckMetadbDeploymentFn,
    refresh: rePrecheckMetadbDeployment,
  } = useRequest(Metadb.precheckMetadbDeployment, {
    manual: true,
    onSuccess: (res) => {
      if (res.success) {
        // dispatch({
        //   type: 'global/update',
        //   payload: {
        //     precheckStatus: res?.data?.status,
        //     precheckResult: res?.data?.result,
        //   },
        // });
        getMetadbPrecheckTask({
          id: id,
          task_id: res.data?.id,
        });
      }
    },
  });

  //MetaDb的预检查结果
  const {
    data: metadbPrecheckTaskData,
    run: getMetadbPrecheckTask,
    refresh: reGetMetadbPrecheckTask,
    loading: metadbPrecheckTaskLoading,
  } = useRequest(Metadb.getMetadbPrecheckTask, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        // dispatch({
        //   type: 'global/update',
        //   payload: {
        //     precheckResult: res?.data?.task_info?.result || '',
        //     precheckStatus: res?.data?.task_info?.status || '',
        //     precheckMetadbResult: res?.data || {},
        //   },
        // });
        if (res?.data?.task_info?.status === 'RUNNING') {
          setTimeout(() => {
            reGetMetadbPrecheckTask();
          }, 2000);
        }
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const precheckMetadTask = metadbPrecheckTaskData?.data || {};

  // 发起OCP的预检查
  const { run: precheckOcpDeployment, refresh: rePrecheckOcpDeployment } =
    useRequest(OCP.precheckOcpDeployment, {
      manual: true,
      onSuccess: (res) => {
        if (res.success) {
          // dispatch({
          //   type: 'global/update',
          //   payload: {
          //     precheckStatus: res?.data?.status,
          //     precheckResult: res?.data?.result,
          //   },
          // });
          precheckOcp({
            id: id,
            task_id: res.data?.id,
          });
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    });

  const {
    data: precheckOcpDatas,
    run: precheckOcp,
    refresh,
    loading,
  } = useRequest(OCP.precheckOcp, {
    manual: true,
    onSuccess: (res) => {
      if (res?.success) {
        // dispatch({
        //   type: 'global/update',
        //   payload: {
        //     precheckResult: res?.data?.task_info?.result || '',
        //     precheckStatus: res?.data?.task_info?.status || '',
        //     precheckMetadbResult: res?.data || {},
        //   },
        // });
        if (res?.data?.task_info?.status === 'RUNNING') {
          setTimeout(() => {
            refresh();
          }, 2000);
        }
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const precheckOcpData = precheckOcpDatas?.data || {};

  useEffect(() => {
    if (id) {
      if (installType === 'OCP') {
        precheckOcpDeployment({
          id: id,
        });
      } else {
        precheckMetadbDeploymentFn({
          id: id,
        });
      }
    }
  }, [id]);

  return (
    <Card
      divided={false}
      bordered={false}
      className={styles.precheck}
      loading={loading || metadbPrecheckTaskLoading}
      title={
        precheckStatus === 'FINISHED' ? (
          intl.formatMessage({
            id: 'OBD.component.EnvPreCheck.CheckCompleted',
            defaultMessage: '检查完成',
          })
        ) : (
          <ContentWithQuestion
            content={intl.formatMessage({
              id: 'OBD.component.EnvPreCheck.Checking',
              defaultMessage: '检查中',
            })}
            tooltip={{
              title: intl.formatMessage({
                id: 'OBD.component.EnvPreCheck.VerifyingThatYourEnvironmentMeets',
                defaultMessage:
                  '正在验证您的环境是否满足安装和配置 MetaDB 及 OCP 的所有最低要求。',
              }),
            }}
          />
        )
      }
      bodyStyle={{ paddingTop: 0, minHeight: 680 }}
    >
      {installType === 'OCP' ? (
        <div
          data-aspm="c323717"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.component.EnvPreCheck.InstallAndDeployOcpEnvironment',
            defaultMessage: '安装部署OCP环境预检查页',
          })}
          data-aspm-param={``}
          data-aspm-expo
        />
      ) : (
        <div
          data-aspm="c323718"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.component.EnvPreCheck.InstallAndDeployMetadbEnvironment',
            defaultMessage: '安装部署MetaDB环境预检查页',
          })}
          data-aspm-param={``}
          data-aspm-expo
        />
      )}

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <CheckItem
            refresh={() => {
              if (installType === 'OCP') {
                rePrecheckOcpDeployment();
              } else {
                rePrecheckMetadbDeployment();
              }
            }}
            precheckMetadbResult={
              id
                ? installType === 'OCP'
                  ? precheckOcpData
                  : precheckMetadTask
                : precheckMetadbResult
            }
          />
        </Col>
        <Col span={12}>
          <CheckFailuredItem
            loading={precheckStatus === 'RUNNING'}
            id={id}
            onSuccess={() => {
              if (installType === 'OCP') {
                rePrecheckOcpDeployment();
              } else {
                rePrecheckMetadbDeployment();
              }
            }}
            precheckMetadbResult={
              id
                ? installType === 'OCP'
                  ? precheckOcpData
                  : precheckMetadTask
                : precheckMetadbResult
            }
          />
        </Col>
      </Row>
    </Card>
  );
};

export default EnvPreCheck;
