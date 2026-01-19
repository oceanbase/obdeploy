//@ts-nocheck
import { Group, Image, Rect, Text } from '@antv/g6-react-node';
import { intl } from '@/utils/intl';

// VIP 节点组件
export const VIPNode = ({ cfg }: any) => {
    const { label, vipAddress, vipPort } = cfg;
    const nodeWidth = 250;
    const nodeHeight = 100;

    return (
        <Group>
            <Rect
                style={{
                    width: nodeWidth,
                    height: nodeHeight,
                    fill: '#fff',
                    stroke: 'transparent',
                    radius: 6,
                }}
                name="container"
            >
                {/* VIP 标题 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 14,
                        fontWeight: 'bold',
                        x: nodeWidth / 2,
                        y: 25,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="vipTitle"
                >
                    {label}
                </Text>
                {/* IP 地址 - 左对齐，位置靠右以 VIP 为中心 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 12,
                        x: nodeWidth / 2 - 50,
                        y: 55,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'left',
                    }}
                    name="vipAddress"
                >
                    {`${intl.formatMessage({
                        id: 'OBD.pages.components.TopoComponent.IPAddress',
                        defaultMessage: 'IP 地址',
                    })}      ${vipAddress}`}
                </Text>
                {/* 访问端口 - 左对齐，位置靠右以 VIP 为中心 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 12,
                        x: nodeWidth / 2 - 50,
                        y: 75,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'left',
                    }}
                    name="vipPort"
                >
                    {`${intl.formatMessage({
                        id: 'OBD.pages.components.TopoComponent.AccessPort',
                        defaultMessage: '访问端口',
                    })}      ${vipPort || 2883}`}
                </Text>
            </Rect>
        </Group>
    );
};

// DNS 节点组件
export const DNSNode = ({ cfg }: any) => {
    const { label, domain } = cfg;
    const nodeWidth = 250; // 增加宽度以确保文本不换行
    const nodeHeight = 80;

    // 清理域名值，确保没有换行符和特殊字符
    const domainValue = String(domain).trim().replace(/[\r\n\t]/g, '').replace(/\s+/g, ' ')

    // 组合域名文本
    const domainText = `域名  ${domainValue}`;

    return (
        <Group>
            <Rect
                style={{
                    width: nodeWidth,
                    height: nodeHeight,
                    fill: '#fff',
                    stroke: 'transparent',
                    radius: 6,
                }}
                name="container"
            >
                {/* DNS 标题 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 14,
                        fontWeight: 'bold',
                        x: nodeWidth / 2,
                        y: 25,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="dnsTitle"
                >
                    {label}
                </Text>
                {/* 域名和值在同一行 - 使用单个 Text 组件，无空格连接 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 12,
                        x: nodeWidth / 2,
                        y: 55,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="domainValue"
                >
                    {`${intl.formatMessage({
                        id: 'OBD.pages.components.TopoComponent.Domain',
                        defaultMessage: '域名',
                    })}  ${domainValue}`}
                </Text>
            </Rect>
        </Group>
    );
};

// OBProxy 节点组件
export const OBProxyNode = ({ cfg }: any) => {
    const { label, servers = [] } = cfg;
    const nodeWidth = Math.max(400, servers.length * 120 + 40);
    const nodeHeight = 140;
    const serverSpacing = 100;

    return (
        <Group>
            <Rect
                style={{
                    width: nodeWidth,
                    height: nodeHeight,
                    fill: '#fff',
                    stroke: 'transparent',
                    radius: 6,
                }}
                name="container"
            >
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 14,
                        fontWeight: 'bold',
                        x: nodeWidth / 2,
                        y: 25,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="obproxyTitle"
                >
                    {label}
                </Text>
                {/* 服务器图标和IP */}
                {servers.map((server: string, index: number) => {
                    const startX = (nodeWidth - (servers.length - 1) * serverSpacing) / 2;
                    const x = startX + index * serverSpacing;
                    const iconSize = 50; // 图标大小
                    return (
                        <Group key={`server-${index}`}>
                            {/* 服务器图标 - 使用 zone_running.svg，使用完整的 URL */}
                            <Image
                                style={{
                                    x: x - iconSize / 2,
                                    y: 45,
                                    width: iconSize,
                                    height: iconSize,
                                }}
                                img={`${typeof window !== 'undefined' ? window.location.origin : ''}/assets/zone_running.svg`}
                                name={`server-icon-${index}`}
                            />
                            {/* IP 地址 */}
                            <Text
                                style={{
                                    position: 'absolute',
                                    fontSize: 11,
                                    x: x,
                                    y: 120,
                                    fill: 'rgb(0,0,0,.85)',
                                    textAlign: 'center',
                                }}
                                name={`server-ip-${index}`}
                            >
                                {server}
                            </Text>
                        </Group>
                    );
                })}
            </Rect>
        </Group>
    );
};


// OceanBase 集群节点组件
export const ClusterNode = ({ cfg }: any) => {
    const { label, clusterName } = cfg;
    const nodeWidth = 250;
    const nodeHeight = 140;

    return (
        <Group>
            <Rect
                style={{
                    width: nodeWidth,
                    height: nodeHeight,
                    fill: '#fff',
                    stroke: 'transparent',
                    radius: 6,
                }}
                name="container"
            >
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 14,
                        fontWeight: 'bold',
                        x: nodeWidth / 2,
                        y: 35,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="clusterTitle"
                >
                    {label}
                </Text>
                {/* 集群名称 */}
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 12,
                        x: nodeWidth / 2,
                        y: 130,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="clusterName"
                >
                    {clusterName || 'myoceanbase'}
                </Text>
            </Rect>
        </Group>
    );
};

// Zone 节点组件
export const ZoneNode = ({ cfg }: any) => {
    const { label, zoneName, zoneIp } = cfg;
    const nodeWidth = 180;
    const nodeHeight = 140;
    const fontSize = 11;
    const maxWidth = 160; // 文本最大宽度
    const lineHeight = 16; // 行高

    // 将IP地址字符串分割成多行
    const splitIpIntoLines = (ipString: string): string[] => {
        if (!ipString) return [];

        // 按逗号分割IP地址
        const ips = ipString.split(',').map(ip => ip.trim()).filter(ip => ip);
        if (ips.length === 0) return [];

        const lines: string[] = [];
        let currentLine = '';

        ips.forEach((ip, index) => {
            const testLine = currentLine ? `${currentLine},${ip}` : ip;
            // 估算文本宽度（每个字符大约占字体大小的0.6倍）
            const estimatedWidth = testLine.length * fontSize * 0.6;

            if (estimatedWidth > maxWidth && currentLine) {
                // 当前行已满，开始新行
                lines.push(currentLine);
                currentLine = ip;
            } else {
                currentLine = testLine;
            }

            // 如果是最后一个IP，添加到当前行
            if (index === ips.length - 1) {
                lines.push(currentLine);
            }
        });

        return lines;
    };

    const ipLines = splitIpIntoLines(zoneIp || '');
    // 图标位置：顶部 y:45，高度 50px，底部 y:95
    // IP 地址应该在图标下方，留出间距
    const iconBottom = 45 + 50; // 图标底部位置 (y: 95)
    const spacing = 8; // 图标和IP地址之间的间距
    const startY = iconBottom + spacing; // IP地址第一行的起始位置 (y: 103)
    // 节点高度140px，确保IP地址在节点内
    // Text的y是基线位置，文字高度约11px
    // 如果2行，最后一行基线在 y: 103 + 16 = 119，文字底部在 y: 119 + 11 = 130，在节点内
    // 如果3行，最后一行基线在 y: 103 + 2*16 = 135，文字底部在 y: 135 + 11 = 146，超出节点
    // 为了确保在节点内，限制最多2行，如果IP地址很多可以缩小字体或调整布局
    const maxLines = 2;
    const displayLines = ipLines.slice(0, maxLines);

    return (
        <Group>
            <Rect
                style={{
                    width: nodeWidth,
                    height: nodeHeight,
                    fill: '#fff',
                    stroke: 'transparent',
                    radius: 6,
                }}
                name="container"
            >
                <Text
                    style={{
                        position: 'absolute',
                        fontSize: 14,
                        fontWeight: 'bold',
                        x: nodeWidth / 2,
                        y: 35,
                        fill: 'rgb(0,0,0,.85)',
                        textAlign: 'center',
                    }}
                    name="zoneTitle"
                >
                    {label}
                </Text>
                {/* IP 地址 - 多行显示 */}
                {displayLines.map((line, index) => (
                    <Text
                        key={`zoneIp-${index}`}
                        style={{
                            position: 'absolute',
                            fontSize: fontSize,
                            x: nodeWidth / 2,
                            y: startY + index * lineHeight,
                            fill: 'rgb(0,0,0,.85)',
                            textAlign: 'center',
                        }}
                        name={`zoneIp-${index}`}
                    >
                        {line}
                    </Text>
                ))}
            </Rect>
        </Group>
    );
};

