import G6 from '@antv/g6';
import { Spin, Button, Space } from 'antd';
import { ZoomInOutlined, ZoomOutOutlined, CompressOutlined, ExpandOutlined, FullscreenOutlined } from '@ant-design/icons';
import _ from 'lodash';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useModel } from 'umi';
import { config, registerConfigDataNodes } from './G6register';
import { createDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { appenAutoShapeListener, addServerIconsToOBProxy, addIconsToZone, addIconsToCluster } from './helper';
import { buildTopoDataFromConfig } from './configDataHelper';
import styles from './index.less';
import { intl } from '@/utils/intl';
import { getErrorInfo, handleQuit } from '@/utils';
import { formatConfigData } from '../CheckInfo';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import useRequest from '@/utils/useRequest';

interface TopoProps {
  loading?: boolean;
}

export default function TopoComponent({ loading }: TopoProps) {
  const {
    configData,
    handleQuitProgress,
    setCurrentStep,
    setErrorVisible,
    setErrorsList,
    errorsList,
    scenarioParam,


  } = useModel('global');

  const { oceanbase } = configData?.components || {};
  const graph = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 从 configData 构建拓扑图数据
  const configTopoData = useMemo(() => {
    if (configData) {
      return buildTopoDataFromConfig(configData);
    }
    return null;
  }, [configData]);

  const { run: handleCreateConfig, loading: createConfigLoading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          setCurrentStep(5);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const prevStep = () => {
    setCurrentStep(3);
    window.scrollTo(0, 0);
  };

  const handlePreCheck = async () => {
    const { data: publicKey } = await getPublicKey();
    handleCreateConfig(
      { name: oceanbase?.appname },
      formatConfigData(configData, scenarioParam, publicKey),
    );
  };

  //Initialize g6
  const init = (topoData: any) => {
    const container = document.getElementById('topoContainer');
    if (!container) return;

    const width = container.scrollWidth || 1280;
    const height = container.scrollHeight || 500;

    graph.current = new G6.TreeGraph(config(width, height));

    // 注册基于 configData 的自定义节点
    registerConfigDataNodes();

    G6.registerEdge('flow-line', {
      draw(cfg, group) {
        const startPoint = cfg.startPoint!;
        const endPoint = cfg.endPoint!;
        const { style } = cfg;
        const shape = group.addShape('path', {
          attrs: {
            stroke: style!.stroke,
            path: [
              ['M', startPoint.x, startPoint.y], //M: Move to
              ['L', startPoint.x, (startPoint.y + endPoint.y) / 2], // L:line to
              ['L', endPoint.x, (startPoint.y + endPoint.y) / 2],
              ['L', endPoint.x, endPoint.y],
            ],
          },
        });

        return shape;
      },
    });

    // 使用传入的拓扑图数据
    if (topoData) {
      graph.current.data(_.cloneDeep(topoData));
      graph.current.render();
      // 自动适应视图
      graph.current.fitView();

      appenAutoShapeListener(graph.current);
      // 为 OBProxy 节点添加图标
      addServerIconsToOBProxy(graph.current);
      // 为 Zone 节点添加图标
      addIconsToZone(graph.current);
      // 为 Cluster 节点添加图标
      addIconsToCluster(graph.current);
    }
  };

  // 缩放功能
  const handleZoomIn = () => {
    if (graph.current) {
      const currentZoom = graph.current.getZoom();
      const newZoom = Math.min(currentZoom * 1.2, 1.6);
      graph.current.zoomTo(newZoom);
      setZoom(newZoom);
    }
  };

  const handleZoomOut = () => {
    if (graph.current) {
      const currentZoom = graph.current.getZoom();
      const newZoom = Math.max(currentZoom / 1.2, 0.2);
      graph.current.zoomTo(newZoom);
      setZoom(newZoom);
    }
  };

  const handleFitView = () => {
    if (graph.current) {
      graph.current.fitView();
      const currentZoom = graph.current.getZoom();
      setZoom(currentZoom);
    }
  };

  // 全屏功能
  const handleFullscreen = async () => {
    if (!containerRef.current) return;

    try {
      if (!isFullscreen) {
        // 进入全屏
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen();
        } else if ((containerRef.current as any).webkitRequestFullscreen) {
          await (containerRef.current as any).webkitRequestFullscreen();
        } else if ((containerRef.current as any).mozRequestFullScreen) {
          await (containerRef.current as any).mozRequestFullScreen();
        } else if ((containerRef.current as any).msRequestFullscreen) {
          await (containerRef.current as any).msRequestFullscreen();
        }
      } else {
        // 退出全屏
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if ((document as any).webkitExitFullscreen) {
          await (document as any).webkitExitFullscreen();
        } else if ((document as any).mozCancelFullScreen) {
          await (document as any).mozCancelFullScreen();
        } else if ((document as any).msExitFullscreen) {
          await (document as any).msExitFullscreen();
        }
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };

  // 监听全屏状态变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = !!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);

      // 全屏时设置背景色为白色
      if (isCurrentlyFullscreen) {
        document.body.style.backgroundColor = '#fff';
      } else {
        document.body.style.backgroundColor = '';
      }

      // 全屏时重新调整画布大小
      if (graph.current && isCurrentlyFullscreen) {
        setTimeout(() => {
          const container = document.getElementById('topoContainer');
          if (container) {
            graph.current.changeSize(container.scrollWidth, container.scrollHeight);
            graph.current.fitView();
          }
        }, 100);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

  // 监听缩放变化
  useEffect(() => {
    if (graph.current) {
      const handleZoom = () => {
        const currentZoom = graph.current.getZoom();
        setZoom(currentZoom);
      };
      graph.current.on('viewportchange', handleZoom);
      return () => {
        graph.current?.off('viewportchange', handleZoom);
      };
    }
  }, [graph.current]);

  // 初始化图表和更新数据
  useEffect(() => {
    if (configTopoData) {
      if (!graph.current) {
        // 首次初始化
        init(configTopoData);
        const currentZoom = graph.current?.getZoom();
        if (currentZoom) {
          setZoom(currentZoom);
        }
      } else {
        // 数据更新
        graph.current.changeData(_.cloneDeep(configTopoData));
        graph.current.fitView();

        // 为 OBProxy 节点添加图标
        addServerIconsToOBProxy(graph.current);
        // 为 Zone 节点添加图标
        addIconsToZone(graph.current);
        // 为 Cluster 节点添加图标
        addIconsToCluster(graph.current);

        const currentZoom = graph.current.getZoom();
        setZoom(currentZoom);
      }
    }
    // 清理函数：组件卸载时销毁图表
    return () => {
      if (graph.current) {
        graph.current.destroy();
        graph.current = null;
      }
    };
  }, [configTopoData]);
  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        height: '100vh',
        backgroundColor: isFullscreen ? '#fff' : 'transparent'
      }}
      className={isFullscreen ? styles.fullscreenContainer : ''}
    >
      <div style={{ height: '100%' }} id="topoContainer"></div>
      <Spin
        spinning={Boolean(loading || !configTopoData)}
        size="large"
        className={styles.topoSpin}
      />
      {/* 控制按钮 */}
      <div className={styles.topoControls}>
        <Button.Group>
          <Button
            icon={<ZoomOutOutlined />}
            onClick={handleZoomOut}
            disabled={!graph.current}
            title={intl.formatMessage({
              id: 'OBD.pages.components.TopoComponent.ZoomOut',
              defaultMessage: '缩小',
            })}
          />
          <Button
            onClick={handleFitView}
            disabled={!graph.current}
            title={intl.formatMessage({
              id: 'OBD.pages.components.TopoComponent.FitView',
              defaultMessage: '适应视图',
            })}
          >
            {Math.round(zoom * 100)}%
          </Button>
          <Button
            icon={<ZoomInOutlined />}
            onClick={handleZoomIn}
            disabled={!graph.current}
            title={intl.formatMessage({
              id: 'OBD.pages.components.TopoComponent.ZoomIn',
              defaultMessage: '放大',
            })}
          />
          <Button
            icon={isFullscreen ? <CompressOutlined /> : <FullscreenOutlined />}
            onClick={handleFullscreen}
            title={intl.formatMessage({
              id: isFullscreen
                ? 'OBD.pages.components.TopoComponent.ExitFullscreen'
                : 'OBD.pages.components.TopoComponent.Fullscreen',
              defaultMessage: isFullscreen ? '退出全屏' : '全屏',
            })}
          />
        </Button.Group>
      </div>
      <footer className={styles.pageFooterContainer}>
        <div className={styles.pageFooter}>
          <Space className={styles.foolterAction}>
            <Button
              onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
              data-aspm-click="c307504.d317275"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheckExit',
                defaultMessage: '预检查-退出',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.Exit',
                defaultMessage: '退出',
              })}
            </Button>
            <Button
              onClick={prevStep}
              data-aspm-click="c307504.d317274"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheckPreviousStep',
                defaultMessage: '预检查-上一步',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            <Button
              type="primary"
              onClick={handlePreCheck}
              loading={createConfigLoading}
              data-aspm-click="c307504.d317273"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheck',
                defaultMessage: '预检查-预检查',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheck.1',
                defaultMessage: '预检查',
              })}
            </Button>

          </Space>
        </div>
      </footer>
    </div>
  );
}
