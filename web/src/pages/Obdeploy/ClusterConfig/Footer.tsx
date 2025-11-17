import { Space, Button, Tooltip } from 'antd';
import { getLocale, useModel } from 'umi';

import { intl } from '@/utils/intl';
import { handleQuit } from '@/utils';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface FooterProps {
  prevStep: () => void;
  nextStep: () => void;
}

export default function Footer({ prevStep, nextStep }: FooterProps) {
  const { handleQuitProgress, setCurrentStep } = useModel('global');

  return (
    <footer className={styles.pageFooterContainer}>
      <div className={styles.pageFooter}>
        <Space className={styles.foolterAction}>
          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.TheCurrentPageConfigurationHas',
              defaultMessage: '当前页面配置已保存',
            })}
          >
            <Button
              onClick={prevStep}
              data-aspm-click="c307508.d317281"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationPreviousStep',
                defaultMessage: '集群配置-上一步',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
          </Tooltip>
          <Button
            type="primary"
            onClick={nextStep}
            data-aspm-click="c307508.d317283"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationNextStep',
              defaultMessage: '集群配置-下一步',
            })}
            data-aspm-param={``}
            data-aspm-expo
          >
            {intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.NextStep',
              defaultMessage: '下一步',
            })}
          </Button>
          <Button
            onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
            data-aspm-click="c307508.d317282"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationExit',
              defaultMessage: '集群配置-退出',
            })}
            data-aspm-param={``}
            data-aspm-expo
          >
            {intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.Exit',
              defaultMessage: '退出',
            })}
          </Button>
        </Space>
      </div>
    </footer>
  );
}
