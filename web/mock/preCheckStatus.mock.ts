// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/precheck': (req: Request, res: Response) => {
    res.status(200).send({
      code: 90,
      data: {
        total: 75,
        finished: 66,
        all_passed: true,
        status: null,
        message: '第质结流制去干标划那张且十。',
        info: [
          {
            name: '侯丽',
            server: '入工今集要外书级活保年给难界被。',
            status: null,
            result: null,
            recoverable: false,
            code: '声育况主其质因则导林命见住设何题书家。',
            description: '议矿时统集示点话江据具由基。',
            advisement: null,
          },
          {
            name: '姚秀英',
            server: '状儿当进面物十产白下与划况老三市持。',
            status: null,
            result: null,
            recoverable: true,
            code: '题色所式话积原快广王流而正证单。',
            description: '持习量基最些都连着后济铁处亲其能律。',
            advisement: null,
          },
        ],
      },
      msg: '说命程铁说实合到流引世明或一。',
      success: true,
    });
  },
};
