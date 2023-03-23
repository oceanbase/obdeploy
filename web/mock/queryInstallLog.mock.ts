// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/install/log': (
    req: Request,
    res: Response,
  ) => {
    res.status(200).send({
      code: 66,
      data: { log: '响严管号同都战养志各再很己除具。', offset: 100 },
      msg: '我理回是科定积王育构引知例面非长老。',
      success: true,
    });
  },
};
