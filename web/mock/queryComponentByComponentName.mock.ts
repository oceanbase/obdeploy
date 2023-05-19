// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/components/:component': (req: Request, res: Response) => {
    res.status(200).send({
      code: 69,
      data: {
        name: '杨明',
        info: [
          {
            estimated_size: 73,
            version: '圆社千始回自易亲点如装期影识治难几。',
            type: 115,
            release: '主与百广周三看到细矿手规题素。',
            arch: '严们住直道代方个布形海员在分务。',
            md5: '通值千合除果手信导克路响。',
            version_type: 116,
          },
          {
            estimated_size: 68,
            version: '高速非现都七治何点强三交济形。',
            type: 117,
            release: '发进做京列号起习参复府战论亲它十界通。',
            arch: '么具生象与只好厂接速价已了。',
            md5: '调划并况也较除片影克布众才来。',
            version_type: 118,
          },
          {
            estimated_size: 79,
            version: '作该资种解省于属一工文比建那工始。',
            type: 119,
            release: '何改且江开根周件周整动性。',
            arch: '美文放式向还如认门音那设向证。',
            md5: '转些将低调办较整件装压这的。',
            version_type: 120,
          },
          {
            estimated_size: 89,
            version: '情音置至快量族值已增学象候等别空青基。',
            type: 121,
            release: '看般改报断边委求型图色收叫天成高利。',
            arch: '识些料离利本系声几市成管等老做就变今。',
            md5: '数力设化根性事七和科小完压达毛先进。',
            version_type: 122,
          },
        ],
      },
      msg: '济生多级原联每化运支将证路委器。',
      success: true,
    });
  },
};
