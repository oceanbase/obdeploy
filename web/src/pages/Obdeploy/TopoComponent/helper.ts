//@ts-nocheck
import { Graph, INode } from '@antv/g6';

const propsToEventMap = {
  click: 'onClick',
  dbclick: 'onDBClick',
  mouseenter: 'onMouseEnter',
  mousemove: 'onMouseMove',
  mouseout: 'onMouseOut',
  mouseover: 'onMouseOver',
  mouseleave: 'onMouseLeave',
  mousedown: 'onMouseDown',
  mouseup: 'onMouseUp',
  dragstart: 'onDragStart',
  drag: 'onDrag',
  dragend: 'onDragEnd',
  dragenter: 'onDragEnter',
  dragleave: 'onDragLeave',
  dragover: 'onDragOver',
  drop: 'onDrop',
  contextmenu: 'onContextMenu',
};

/**
 * When listening to mouseenter and mouseleave events, evt.shape is null (g6 itself)
 */
export function appenAutoShapeListener(graph: Graph) {
  Object.entries(propsToEventMap).forEach(([eventName, propName]) => {
    graph.on(`node:${eventName}`, (evt) => {
      const shape = evt.shape;
      const item = evt.item as INode;
      const graph = evt.currentTarget as Graph;
      const func =
        (shape?.get(propName) as any) ||
        evt.target.cfg[propName];
      if (func) {
        func(evt, item, shape, graph);
      }
    });
  });
}

/**
 * 为画布添加边框
 */
export function addCanvasBorder(graph: Graph) {
  const group = graph.get('group');
  
  // 移除已存在的边框（如果存在）
  const existingBorder = group.find((item: any) => {
    return item.get('name') === 'canvas-border';
  });
  if (existingBorder) {
    existingBorder.remove();
  }
  
  // 获取所有节点和边的边界框
  const nodes = graph.getNodes();
  const edges = graph.getEdges();
  
  if (nodes.length === 0) {
    return;
  }
  
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  
  // 计算所有节点的边界框
  nodes.forEach((node: any) => {
    const bbox = node.getBBox();
    minX = Math.min(minX, bbox.minX);
    minY = Math.min(minY, bbox.minY);
    maxX = Math.max(maxX, bbox.maxX);
    maxY = Math.max(maxY, bbox.maxY);
  });
  
  // 计算所有边的边界框（包括连接线）
  edges.forEach((edge: any) => {
    const bbox = edge.getBBox();
    if (bbox && bbox.width > 0 && bbox.height > 0) {
      minX = Math.min(minX, bbox.minX);
      minY = Math.min(minY, bbox.minY);
      maxX = Math.max(maxX, bbox.maxX);
      maxY = Math.max(maxY, bbox.maxY);
    }
  });
  
  // 添加 padding，与 fitViewPadding 保持一致
  const padding = 50;
  const x = minX - padding;
  const y = minY - padding;
  const width = maxX - minX + padding * 2;
  const height = maxY - minY + padding * 2;
  
  // 添加边框矩形到 group 的最底层
  const borderShape = group.addShape('rect', {
    attrs: {
      x: x,
      y: y,
      width: width,
      height: height,
      fill: 'transparent',
      stroke: '#d9d9d9',
      lineWidth: 1,
      radius: 4,
    },
    name: 'canvas-border',
  });
  
  // 将边框移到最底层
  borderShape.toBack();
}

/**
 * 为 OBProxy 节点添加 SVG 图标
 */
export function addServerIconsToOBProxy(graph: Graph) {
  graph.getNodes().forEach((node) => {
    const model = node.getModel();
    if (model.type === 'obproxy' && model.servers) {
      const group = node.getContainer();
      const bbox = node.getBBox();
      
      // 移除已存在的图标（如果存在）
      const existingIcons = group.findAll((item: any) => {
        return item.get('name') && item.get('name').startsWith('server-icon-');
      });
      existingIcons.forEach((icon: any) => icon.remove());
      
      // 为每个服务器添加图标
      const servers = model.servers || [];
      const serverSpacing = 100;
      const iconSize = 50;
      const startX = (bbox.width - (servers.length - 1) * serverSpacing) / 2;
      
      servers.forEach((server: string, index: number) => {
        const x = startX + index * serverSpacing;
        const iconX = x - iconSize / 2;
        // IP 地址在 y: 120（文字基线位置），fontSize: 11
        // 在 G6 中，Text 的 y 是基线，文字底部在基线位置
        // 图标底部距离文字基线 4px，所以图标底部应该在 y: 120 - 4 = 116
        // 图标高度 50px，所以图标顶部在 y: 116 - 50 = 66
        // 往上移 10px，所以图标顶部在 y: 66 - 10 = 56
        const iconY = 56;
        
        // 使用 G6 原生的 image shape
        group.addShape('image', {
          attrs: {
            x: iconX,
            y: iconY,
            width: iconSize,
            height: iconSize,
            img: `${window.location.origin}/assets/zone_running.svg`,
          },
          name: `server-icon-${index}`,
        });
      });
    }
  });
}

/**
 * 为 Zone 节点添加 SVG 图标
 */
export function addIconsToZone(graph: Graph) {
  graph.getNodes().forEach((node) => {
    const model = node.getModel();
    if (model.type === 'zone') {
      const group = node.getContainer();
      const bbox = node.getBBox();
      
      // 移除已存在的图标（如果存在）
      const existingIcon = group.find((item: any) => {
        return item.get('name') === 'zone-icon';
      });
      if (existingIcon) {
        existingIcon.remove();
      }
      
      // 添加图标
      // 标题在 y: 35，图标顶部在 y: 45，与标题间距 10px，更协调
      // 图标高度 50px，所以图标底部在 y: 95
      const iconSize = 50;
      const iconX = bbox.width / 2 - iconSize / 2;
      const iconY = 45; // 图标顶部位置，往上移了 11px
      
      // 使用 G6 原生的 image shape
      group.addShape('image', {
        attrs: {
          x: iconX,
          y: iconY,
          width: iconSize,
          height: iconSize,
          img: `${window.location.origin}/assets/zone_running.svg`,
        },
        name: 'zone-icon',
      });
    }
  });
}

/**
 * 为 Cluster 节点添加 SVG 图标
 */
export function addIconsToCluster(graph: Graph) {
  graph.getNodes().forEach((node) => {
    const model = node.getModel();
    if (model.type === 'cluster') {
      const group = node.getContainer();
      const bbox = node.getBBox();
      
      // 移除已存在的图标（如果存在）
      const existingIcon = group.find((item: any) => {
        return item.get('name') === 'cluster-icon';
      });
      if (existingIcon) {
        existingIcon.remove();
      }
      
      // 添加图标
      // 集群名称在 y: 130（文字基线位置），fontSize: 12
      // 在 G6 中，Text 的 y 是基线，文字底部在基线位置
      // 图标底部距离文字基线 4px，所以图标底部应该在 y: 130 - 4 = 126
      // 图标高度 50px，所以图标顶部在 y: 126 - 50 = 76
      // 往上移 20px（两次各 10px），所以图标顶部在 y: 76 - 20 = 56
      const iconSize = 50;
      const iconX = bbox.width / 2 - iconSize / 2;
      const iconY = 56; // 图标顶部位置
      
      // 使用 G6 原生的 image shape
      group.addShape('image', {
        attrs: {
          x: iconX,
          y: iconY,
          width: iconSize,
          height: iconSize,
          img: `${window.location.origin}/assets/cluster_running.svg`,
        },
        name: 'cluster-icon',
      });
    }
  });
}
