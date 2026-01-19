//@ts-nocheck
import G6 from '@antv/g6';
import { createNodeFromReact } from '@antv/g6-react-node';
import { DNSNode, VIPNode, OBProxyNode, ClusterNode, ZoneNode } from './CustomNodes';

const tooltip = new G6.Tooltip({
  offsetX: 10,
  offsetY: 20,
  shouldBegin: (e) => {
    return Boolean(e.item.getModel().tooltipInfo);
  },
  getContent(e) {
    const outDiv = document.createElement('div');
    const { tooltipInfo } = e.item.getModel();
    outDiv.style.width = '180px';
    outDiv.innerHTML = `
      <ul>
        ${tooltipInfo &&
      Object.keys(tooltipInfo)
        .map((key) => `<li>${key}:${tooltipInfo[key]}</li>`)
        .join('')
      }
      </ul>`;
    return outDiv;
  },
  itemTypes: ['node'],
});

function config(width: number, height: number) {
  return {
    container: 'topoContainer',
    width,
    height,
    linkCenter: true,
    fitViewPadding: [50, 50, 50, 50],
    fitView: true,
    maxZoom: 1.6,
    minZoom: 0.2,
    // 设置背景色为浅灰色
    backgroundColor: '#f5f5f5',
    layout: {
      type: 'compactBox',
      direction: 'TB',
      getId: function getId(d: any) {
        return d.id;
      },
      getHeight: function getHeight(d: any) {
        // 根据节点类型返回不同的高度
        if (d.type === 'dns') return 80;
        if (d.type === 'vip') return 100;
        if (d.type === 'obproxy') return 140;
        if (d.type === 'cluster') return 140;
        if (d.type === 'zone') return 140;
        return 48;
      },
      getWidth: function getWidth(d: any) {
        // 根据节点类型返回不同的宽度
        if (d.type === 'dns') return 250; // 增加 DNS 节点宽度以确保文本不换行
        if (d.type === 'vip') return 250;
        if (d.type === 'obproxy') {
          const serverCount = d.servers?.length || 0;
          return Math.max(400, serverCount * 120 + 40);
        }
        if (d.type === 'cluster') return 250;
        if (d.type === 'zone') return 180;
        return 100;
      },
      getVGap: function getVGap() {
        return 80; // 增加垂直间距，使层次更清晰
      },
      getHGap: function getHGap() {
        return 150; // 增加水平间距，使 Zone 节点分布更均匀
      },
    },
    defaultEdge: {
      type: 'flow-line',
      sourceAnchor: 0,
      targetAnchor: 1,
      style: {
        radius: 0, // 直线连接，不使用圆角
        stroke: '#c5cbd4',
        lineWidth: 1.5,
      },
    },
    defaultNode: {
      style: {
        width: 100,
        height: 48,
        fill: 'rgb(19,33,92)',
        radius: 5,
      },
      anchorPoints: [
        [0.9, 0.5],
        [0, 0.5],
      ],
    },
    plugins: [tooltip],
    nodeStateStyles: {
      hover: {
        fill: '#fff',
        shadowBlur: 30,
        shadowColor: '#ddd',
      },
      operatorhover: {
        'operator-box': {
          opacity: 1,
        },
      },
    },
    modes: {
      default: [
        'zoom-canvas',
        'drag-canvas',
        // {
        //   type: 'tooltip',
        //   formatText(model: any) {
        //     return TopoTooltip(model.type, tooltipData);
        //   },
        //   offset: 10,
        // },
      ],
    },
  };
}

/**
 * 注册基于 configData 的自定义节点
 */
export const registerConfigDataNodes = () => {
  G6.registerNode('dns', createNodeFromReact(DNSNode));
  G6.registerNode('vip', createNodeFromReact(VIPNode));
  G6.registerNode('obproxy', createNodeFromReact(OBProxyNode));
  G6.registerNode('cluster', createNodeFromReact(ClusterNode));
  G6.registerNode('zone', createNodeFromReact(ZoneNode));
};

export { config };
